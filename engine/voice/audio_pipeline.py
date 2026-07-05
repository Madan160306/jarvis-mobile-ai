import time
import collections
import numpy as np
import sys
import os

try:
    import pyaudio
    HAS_PYAUDIO = True
except Exception:
    HAS_PYAUDIO = False
    
try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

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
        
        if HAS_PYAUDIO:
            self.pa = pyaudio.PyAudio()
        self.FORMAT = pyaudio.paInt16 if HAS_PYAUDIO else 'int16'
        self.CHANNELS = 1
        self.RATE = 16000
        # Openwakeword prefers 1280 samples per chunk (80ms at 16kHz)
        self.CHUNK_SIZE = 1280 
        
        # Neural VAD for detecting end of command
        try:
            from silero_vad import load_silero_vad
            self.vad_model = load_silero_vad(onnx=True)
            self.has_vad = True
        except ImportError:
            self.vad_model = None
            self.has_vad = False
        
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
        if HAS_PYAUDIO:
            stream = self.pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                start=False,
                frames_per_buffer=self.CHUNK_SIZE
            )
            stream.start_stream()
        elif HAS_SD:
            stream = sd.InputStream(samplerate=self.RATE, channels=self.CHANNELS, dtype=self.FORMAT, blocksize=self.CHUNK_SIZE)
            stream.start()
        else:
            print("[PIPELINE] No streaming audio library found. Using Termux Speech-to-Text Fallback.")
            import subprocess
            while True:
                input("\n[Termux Mode] Press ENTER to speak to JARVIS...")
                print("Listening...")
                try:
                    # Uses Android's native speech recognition dialog!
                    result = subprocess.check_output(["termux-speech-to-text"]).decode("utf-8").strip()
                    if result:
                        yield result, "en"
                except Exception as e:
                    print(f"[Termux ASR Error] {e}")
            return

        self.wake_engine.reset()
        print("[PIPELINE] 💤 Listening for wake word...")
        
        state = "DORMANT"
        command_buffer = bytearray()
        
        if self.has_vad:
            from silero_vad import VADIterator
            import torch
            # Reset iterator
            vad_iterator = VADIterator(self.vad_model, sampling_rate=16000, min_silence_duration_ms=600, threshold=0.5)
            vad_position = 0
        else:
            vad_iterator = None
            vad_position = 0
        
        try:
            while True:
                if HAS_PYAUDIO:
                    chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                else:
                    chunk, overflow = stream.read(self.CHUNK_SIZE)
                    chunk = chunk.flatten().tobytes()
                
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
                        if self.has_vad:
                            vad_iterator = VADIterator(self.vad_model, sampling_rate=16000, min_silence_duration_ms=600, threshold=0.5)
                            vad_position = 0
                        
                elif state == "AWAKE":
                    command_buffer.extend(chunk)
                    
                    if self.has_vad:
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
                    else:
                        # No VAD: hardcode 4 second record limit
                        if len(command_buffer) > self.RATE * 2 * 4.0:
                            state = "TRANSCRIBING"
                            
                    # Hard limit 10 seconds max to prevent infinite recording
                    if len(command_buffer) > self.RATE * 2 * 10:
                        state = "TRANSCRIBING"
                        
                if state == "TRANSCRIBING":
                    print("[PIPELINE] 🎙️ Processing command...")
                    # Stop recording during processing and TTS playback to avoid hearing itself
                    try:
                        if HAS_PYAUDIO:
                            stream.stop_stream()
                        elif HAS_SD:
                            stream.stop()
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
                        if HAS_PYAUDIO:
                            stream.start_stream()
                            for _ in range(2):
                                stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                        elif HAS_SD:
                            stream.start()
                            for _ in range(2):
                                stream.read(self.CHUNK_SIZE)
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
            try:
                if HAS_PYAUDIO:
                    stream.stop_stream()
                    stream.close()
                elif HAS_SD:
                    stream.stop()
                    stream.close()
            except:
                pass

    def _transcribe_buffer(self, audio_buffer: bytearray):
        """Extract the transcription logic from hybrid_asr to process a direct buffer."""
        try:
            import noisereduce
            HAS_NOISEREDUCE = True
        except Exception:
            HAS_NOISEREDUCE = False
        
        if len(audio_buffer) < int(self.RATE * 2 * 0.15):
            return ("", "en")
            
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        audio_duration = len(audio_buffer) / (self.RATE * 2)
        
        # Apply noise reduction based on config setting
        noise_red = self.config.get("noise_reduction", "stationary")
        if HAS_NOISEREDUCE and noise_red == "stationary":
            try:
                audio_np = noisereduce.reduce_noise(y=audio_np, sr=self.RATE, stationary=True, prop_decrease=0.2)
            except:
                pass
        elif HAS_NOISEREDUCE and noise_red == "non-stationary":
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
                        wf.setsampwidth(2) # 16-bit PCM
                        wf.setframerate(self.RATE)
                        wf.writeframes(audio_buffer)
                    wav_io.seek(0)
                    
                    import requests
                    
                    api_key = HybridLLM.get_api_key("groq")
                    if not api_key:
                        raise ValueError("Groq API key missing")
                        
                    files = {
                        "file": ("audio.wav", wav_io.read(), "audio/wav"),
                    }
                    data = {
                        "model": "whisper-large-v3-turbo",
                        "language": "en",
                        "prompt": "Hey JARVIS. JARVIS is an AI assistant."
                    }
                    
                    response = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        transcription_text = response.json().get("text", "")
                    else:
                        raise Exception(f"Groq API error: {response.text}")
                        
                    text = transcription_text.strip()
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
