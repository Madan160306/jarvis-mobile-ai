import time
import collections
import pyaudio
import numpy as np
import audioop
import sys
import os

import collections
from engine.voice.wake_word import WakeWordEngine
from engine.voice.hybrid_asr import HybridVoiceEngine
from engine.voice.voice_auth import VoiceAuthenticator
from engine.voice.tts_engine import TTSEngine

# Optional beep sound
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

class AudioPipeline:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "jk_config.yaml")
        try:
            import yaml
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except Exception:
            self.config = {}

        access_key = self.config.get("porcupine_access_key", "")
        wake_word_cfg = self.config.get("wake_word", "jarvis")
        self.wake_engine = WakeWordEngine(access_key=access_key, wake_word=wake_word_cfg)
        
        asr_model = self.config.get("asr_model", "base.en")
        self.asr_engine = HybridVoiceEngine(model_size=asr_model)
        
        self.pa = pyaudio.PyAudio()
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        # Openwakeword prefers 1280 samples per chunk (80ms at 16kHz)
        self.CHUNK_SIZE = 1280 
        
        # Neural VAD for detecting end of command
        from silero_vad import load_silero_vad
        self.vad_model = load_silero_vad(onnx=True)
        
        # Load voice biometrics profile
        owner_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "owner_voice.npy")
        self.voice_auth = VoiceAuthenticator(owner_path)
        
    def _play_beep(self):
        if HAS_WINSOUND:
            winsound.Beep(1000, 200) # 1000 Hz, 200ms
            
    def listen_continuously(self):
        """
        State Machine:
        1. DORMANT: Feed chunks to openwakeword.
        2. AWAKE: Beep, then collect chunks until VAD detects silence.
        3. TRANSCRIBING: Send collected buffer to ASR.
        """
        stream = self.pa.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            start=False,
            frames_per_buffer=self.CHUNK_SIZE
        )
        
        self.wake_engine.reset()
        stream.start_stream()
        print("[PIPELINE] 💤 Listening for wake word...")
        
        state = "DORMANT"
        command_buffer = bytearray()
        
        from silero_vad import VADIterator
        import torch
        # Reset iterator
        vad_iterator = VADIterator(self.vad_model, sampling_rate=16000, min_silence_duration_ms=600, threshold=0.5)
        vad_position = 0
        
        try:
            while True:
                # Read audio chunk
                chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                
                if state == "DORMANT":
                    # Convert to numpy array for porcupine wrapper
                    audio_np = np.frombuffer(chunk, dtype=np.int16)
                    is_awake = self.wake_engine.process_chunk(audio_np)
                    
                    if is_awake:
                        print("[PIPELINE] ✅ Wake word detected!")
                        self._play_beep()
                        self.wake_engine.reset()
                        state = "AWAKE"
                        command_buffer.clear()
                        vad_iterator = VADIterator(self.vad_model, sampling_rate=16000, min_silence_duration_ms=600, threshold=0.5)
                        vad_position = 0
                        
                elif state == "AWAKE":
                    command_buffer.extend(chunk)
                    
                    # Feed exactly 512 samples (1024 bytes) into Silero VAD
                    while len(command_buffer) - vad_position >= 1024:
                        vad_chunk = command_buffer[vad_position:vad_position+1024]
                        vad_position += 1024
                        
                        audio_int16 = np.frombuffer(vad_chunk, np.int16)
                        audio_float32 = torch.from_numpy(audio_int16.astype(np.float32) / 32768.0)
                        
                        speech_dict = vad_iterator(audio_float32)
                        if speech_dict is not None and "end" in speech_dict:
                            state = "TRANSCRIBING"
                            break
                            
                    # Hard limit 10 seconds max to prevent infinite recording
                    if len(command_buffer) > self.RATE * 2 * 10:
                        state = "TRANSCRIBING"
                        
                if state == "TRANSCRIBING":
                    print("[PIPELINE] 🎙️ Processing command...")
                    # Stop recording during processing and TTS playback to avoid hearing itself
                    try:
                        stream.stop_stream()
                    except Exception as e:
                        print(f"[PIPELINE] Warning: failed to stop stream: {e}")

                    # We bypass listen() and just pass the buffer to its transcription logic.
                    audio_float32_buffer = np.frombuffer(command_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # Security: Continuous Voice Biometrics Check
                    # Verify this is actually the registered owner speaking the command
                    if not self.voice_auth.authenticate_buffer(audio_float32_buffer):
                        print("[SECURITY] Unauthorized voice signature detected! Dropping command.")
                        TTSEngine.speak("I am sorry, but I only take orders from Sir.")
                        text = ""
                    else:
                        text, lang = self._transcribe_buffer(command_buffer)
                        
                    if text:
                        yield text, lang
                    
                    # Restart the stream to resume listening (flushes any stale buffer data)
                    try:
                        stream.start_stream()
                        # Discard first few chunks to skip initialization pops/clicks
                        for _ in range(2):
                            stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                    except Exception as e:
                        print(f"[PIPELINE] Warning: failed to start stream: {e}")

                    # Reset back to dormant
                    print("[PIPELINE] 💤 Returning to sleep...")
                    self.wake_engine.reset()
                    state = "DORMANT"
                    command_buffer.clear()
                    
        except KeyboardInterrupt:
            print("[PIPELINE] Stopped.")
        finally:
            stream.stop_stream()
            stream.close()

    def _transcribe_buffer(self, audio_buffer: bytearray):
        """Extract the transcription logic from hybrid_asr to process a direct buffer."""
        import noisereduce
        
        if len(audio_buffer) < int(self.RATE * 2 * 0.15):
            return ("", "en")
            
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        audio_duration = len(audio_buffer) / (self.RATE * 2)
        
        # Apply noise reduction based on config setting
        noise_red = self.config.get("noise_reduction", "stationary")
        if noise_red == "stationary":
            try:
                audio_np = noisereduce.reduce_noise(y=audio_np, sr=self.RATE, stationary=True, prop_decrease=0.2)
            except:
                pass
        elif noise_red == "non-stationary":
            try:
                audio_np = noisereduce.reduce_noise(y=audio_np, sr=self.RATE, stationary=False, prop_decrease=0.2)
            except:
                pass

        # Hybrid Routing
        if audio_duration >= 4.0:
            try:
                from engine.network.network_utils import NetworkUtils
                from engine.ai.hybrid_llm import HybridLLM
                if NetworkUtils.is_online():
                    import io
                    import wave
                    wav_io = io.BytesIO()
                    with wave.open(wav_io, 'wb') as wf:
                        wf.setnchannels(self.CHANNELS)
                        wf.setsampwidth(self.pa.get_sample_size(self.FORMAT))
                        wf.setframerate(self.RATE)
                        wf.writeframes(audio_buffer)
                    wav_io.seek(0)
                    
                    client = HybridLLM.get_groq_client()
                    transcription = client.audio.transcriptions.create(
                        file=("audio.wav", wav_io.read()),
                        model="whisper-large-v3-turbo",
                        language="en",
                        prompt="Hey JARVIS. JARVIS is an AI assistant."
                    )
                    text = transcription.text.strip()
                    clean_check = text.lower().strip()
                    
                    hallucinations = ["thank you.", "thanks.", "hello.", "bye.", "goodbye."]
                    if not any(clean_check == h for h in hallucinations) and "jarvis is an ai assistant" not in clean_check and "thanks for watching" not in clean_check:
                        return (text, "en")
            except Exception as e:
                print(f"[Hybrid ASR] Groq Cloud failed: {e}")

        # Local Edge Fallback
        if not self.asr_engine.model:
            return ("", "en")
            
        try:
            segments, info = self.asr_engine.model.transcribe(
                audio_np,
                language="en",
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                initial_prompt="Hey JK. Hey Jake. JK is an AI assistant."
            )
            text = "".join([segment.text for segment in segments]).strip()
            clean_check = text.lower().strip()
            
            hallucinations = ["thank you.", "thanks.", "hello.", "bye.", "goodbye."]
            if not any(clean_check == h for h in hallucinations) and "jk is an ai assistant" not in clean_check and "thanks for watching" not in clean_check:
                return (text, info.language)
        except Exception as e:
            print(f"[ERROR] Whisper ASR failed: {e}")
            
        return ("", "en")
