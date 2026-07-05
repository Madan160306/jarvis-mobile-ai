import os
import time
import numpy as np
import collections

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
try:
    from faster_whisper import WhisperModel
    HAS_LOCAL_WHISPER = True
except ImportError:
    HAS_LOCAL_WHISPER = False
    print("[ASR] faster_whisper not installed. Defaulting to Cloud ASR (Termux Lite Mode).")

try:
    import noisereduce
    HAS_NOISEREDUCE = True
except Exception:
    HAS_NOISEREDUCE = False

class HybridVoiceEngine:
    def __init__(self, model_size=None):
        # Load config to get model_size and noise_reduction settings
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "jk_config.yaml")
        try:
            import yaml
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except:
            self.config = {}

        if model_size is None:
            model_size = self.config.get("asr_model", "base.en")
            
        print(f"Loading Whisper '{model_size}' model (Perfect Balance of Speed & Accuracy)...")
        if HAS_LOCAL_WHISPER:
            try:
                # use cpu with int8 quantization for ultra-fast, lightweight on-device inference
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            except Exception as e:
                print(f"[ERROR] Could not load Whisper model. Error: {e}")
                self.model = None
        else:
            self.model = None
            try:
                from vosk import Model as VoskModel, KaldiRecognizer
                import json
                vosk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "vosk-model-small-en-us-0.15")
                if os.path.exists(vosk_path):
                    self.vosk_model = VoskModel(vosk_path)
                    print("[ASR] Vosk model loaded successfully for Termux offline fallback.")
                else:
                    self.vosk_model = None
                    print(f"[ASR] Vosk model not found at {vosk_path}")
            except Exception as e:
                print(f"[ERROR] Could not load Vosk model: {e}")
                self.vosk_model = None

        try:
            from silero_vad import load_silero_vad
            self.vad_model = load_silero_vad(onnx=True)
            self.has_vad = True
        except ImportError:
            self.vad_model = None
            self.has_vad = False
            print("[ASR] silero_vad not installed. VAD disabled (Termux Lite Mode).")
        if HAS_PYAUDIO:
            self.pa = pyaudio.PyAudio()
            self.FORMAT = pyaudio.paInt16
        else:
            self.pa = None
            self.FORMAT = 8 # paInt16 is typically 8
        self.CHANNELS = 1
        self.RATE = 16000
        # Silero requires exactly 512 for 16kHz
        self.CHUNK_SIZE = 512

    def listen(self) -> tuple[str, str]:
        """Returns a tuple of (transcribed_text, detected_language_code)"""
        if not self.model and getattr(self, "vosk_model", None) is None and not HAS_LOCAL_WHISPER:
            # We still allow Groq cloud ASR even if local is missing
            pass
            
        ring_buffer = collections.deque(maxlen=int(0.5 * self.RATE / self.CHUNK_SIZE)) # 0.5s pre-speech buffer
        audio_buffer = bytearray()
        triggered = False
        
        if self.has_vad:
            from silero_vad import VADIterator
            import torch
            vad_iterator = VADIterator(self.vad_model, sampling_rate=16000, min_silence_duration_ms=600, threshold=0.5)
        else:
            vad_iterator = None
            
        try:
            if HAS_PYAUDIO:
                pa = pyaudio.PyAudio()
                stream = pa.open(format=pyaudio.paInt16, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK_SIZE)
                stream.start_stream()
            elif HAS_SD:
                stream = sd.InputStream(samplerate=self.RATE, channels=self.CHANNELS, dtype='int16', blocksize=self.CHUNK_SIZE)
                stream.start()
            else:
                print("[ERROR] Neither pyaudio nor sounddevice is installed. Cannot record.")
                return ("", "en")
                
            while True:
                if HAS_PYAUDIO:
                    chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                    audio_int16 = np.frombuffer(chunk, np.int16)
                else:
                    chunk, overflowed = stream.read(self.CHUNK_SIZE)
                    audio_int16 = chunk.flatten()
                    chunk = audio_int16.tobytes()
                    
                if self.has_vad:
                    audio_float32 = torch.from_numpy(audio_int16.astype(np.float32) / 32768.0)
                    speech_dict = vad_iterator(audio_float32)
                    
                    if not triggered:
                        ring_buffer.append(chunk)
                        if speech_dict is not None and "start" in speech_dict:
                            triggered = True
                            audio_buffer.extend(b''.join(ring_buffer))
                            ring_buffer.clear()
                    else:
                        audio_buffer.extend(chunk)
                        if speech_dict is not None and "end" in speech_dict:
                            break # End of phrase
                else:
                    # Fallback if no VAD (Termux Lite): just record fixed 4.0 seconds
                    audio_buffer.extend(chunk)
                    if len(audio_buffer) >= self.RATE * 2 * 4.0:
                        break
                        
                if len(audio_buffer) > self.RATE * 2 * 10:
                    break
        except Exception as e:
            print(f"[ASR] Error during streaming: {e}")
        finally:
            if HAS_PYAUDIO:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            elif HAS_SD:
                stream.stop()
                stream.close()
            
        # If audio is too short (less than 0.15 seconds), it's just a click or noise.
        # Skip Whisper inference entirely to prevent 2-3 seconds of lag!
        if len(audio_buffer) < int(self.RATE * 2 * 0.15):
            return ("", "en")
            
        # Process the captured buffer
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        
        audio_duration = len(audio_buffer) / (self.RATE * 2) # 16-bit PCM = 2 bytes per sample
        
        # Apply noise reduction based on config setting
        noise_red = self.config.get("noise_reduction", "stationary")
        if HAS_NOISEREDUCE and noise_red == "stationary":
            try:
                audio_np = noisereduce.reduce_noise(y=audio_np, sr=16000, stationary=True, prop_decrease=0.2)
            except:
                pass
        elif HAS_NOISEREDUCE and noise_red == "non-stationary":
            try:
                audio_np = noisereduce.reduce_noise(y=audio_np, sr=16000, stationary=False, prop_decrease=0.2)
            except:
                pass

        # HYBRID ROUTING: Use Cloud (Groq whisper-large-v3) for heavy tasks >= 4.0s or if Lite Mode
        if not HAS_LOCAL_WHISPER or audio_duration >= 4.0:
            try:
                from engine.network.network_utils import NetworkUtils
                from engine.ai.hybrid_llm import HybridLLM
                if NetworkUtils.is_online():
                    import io
                    import wave
                    print(f"[Hybrid ASR] Routing to Groq Cloud (whisper-large-v3) for maximum accuracy...")
                    
                    # Convert raw buffer to WAV in memory
                    wav_io = io.BytesIO()
                    with wave.open(wav_io, 'wb') as wf:
                        wf.setnchannels(self.CHANNELS)
                        wf.setsampwidth(2) # 16-bit PCM is 2 bytes
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
                    
                    if "jarvis is an ai assistant" in clean_check or "thanks for watching" in clean_check or "thank you for watching" in clean_check:
                        return ("", "en")
                        
                    hallucinations = [
                        "thank you.", "thank you very much.", "thanks.", "thanks!",
                        "you", "hello.", "yeah?", "i'm here.", "go ahead.", "bye.", "goodbye."
                    ]
                    if any(clean_check == h for h in hallucinations):
                        return ("", "en")
                        
                    if text:
                        return (text, "en")
            except Exception as e:
                print(f"[Hybrid ASR] Groq Cloud failed, falling back to local small.en model: {e}")
            
        # LOCAL EDGE FALLBACK: For short commands (<3.0s) or if Cloud fails
        if HAS_LOCAL_WHISPER and self.model:
            try:
                segments, info = self.model.transcribe(
                    audio_np,
                    language="en",
                    beam_size=1, # Fast greedy decoding
                    temperature=0.0,
                    condition_on_previous_text=False,
                    vad_filter=True, # Enable Silero VAD to prevent hallucinations on silence
                    initial_prompt="Hey JARVIS. JARVIS is an AI assistant. Commands include: send WhatsApp, call to Sandeep, send message to Sandeep, check battery, lock phone, open app, play YT Music, YouTube Music, play Dudue OST."
                )
                text = "".join([segment.text for segment in segments]).strip()
                
                clean_check = text.lower().strip()
                # Aggressive fix for repeating prompt hallucinations
                if "jarvis is an ai assistant" in clean_check or "thanks for watching" in clean_check or "thank you for watching" in clean_check:
                    return ("", "en")
                    
                hallucinations = [
                    "thank you.", "thank you very much.", "thanks.", "thanks!",
                    "you", "hello.", "yeah?", "i'm here.", "go ahead.", "bye.", "goodbye."
                ]
                if any(clean_check == h for h in hallucinations):
                    return ("", "en")
                
                if text:
                    return (text, info.language)
            except Exception as e:
                print(f"[ERROR] Whisper ASR failed: {e}")
        elif not HAS_LOCAL_WHISPER and getattr(self, "vosk_model", None):
            try:
                import json
                from vosk import KaldiRecognizer
                rec = KaldiRecognizer(self.vosk_model, 16000)
                # Convert the float32 array back to int16 for Vosk
                audio_int16 = (audio_np * 32768.0).astype(np.int16).tobytes()
                
                rec.AcceptWaveform(audio_int16)
                result = json.loads(rec.FinalResult())
                text = result.get("text", "").strip()
                
                if text:
                    print(f"[ASR] Vosk Offline Fallback heard: '{text}'")
                    return (text, "en")
            except Exception as e:
                print(f"[ERROR] Vosk ASR failed: {e}")
            
        return ("", "en")
        
        return ("", "en")

import threading
from engine.voice.tts_engine import TTSEngine

class InterruptibleSpeaker:
    _speaking = False
    _interrupt_flag = False
    
    @classmethod
    def speak_interruptible(cls, text: str) -> bool:
        cls._speaking = True
        cls._interrupt_flag = False
        
        interrupt_thread = threading.Thread(
            target=cls._listen_for_interrupt,
            daemon=True
        )
        interrupt_thread.start()
        
        # We split the text by sentences so that we can periodically check the flag if needed, 
        # or we just rely on pygame.mixer.music.stop() from the background thread.
        # Since Kokoro in tts_engine creates audio files and blocks via pygame.time.Clock(), 
        # stopping pygame mixer will break the get_busy() loop.
        
        try:
            import pygame
            HAS_PYGAME = True
        except ImportError:
            HAS_PYGAME = False
            
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            sentences = [text]
            
        for sentence in sentences:
            if cls._interrupt_flag:
                if HAS_PYGAME:
                    pygame.mixer.music.stop()
                cls._speaking = False
                return True
                
            TTSEngine.speak(sentence + ".")
            
            # Re-check flag after the sentence finishes
            if cls._interrupt_flag:
                if HAS_PYGAME:
                    pygame.mixer.music.stop()
                cls._speaking = False
                return True
                
        cls._speaking = False
        return False
        
    @classmethod
    def _listen_for_interrupt(cls):
        # Neural Voice Activity Detection (Silero VAD) replaces WebRTC VAD
        # This completely solves Acoustic Echo (falsely interrupting self) and fan noise.
        import torch
        import numpy as np
        try:
            from silero_vad import load_silero_vad
            vad_model = load_silero_vad(onnx=True)
            has_vad = True
        except ImportError:
            vad_model = None
            has_vad = False
        
        try:
            if HAS_PYAUDIO:
                pa = pyaudio.PyAudio()
                stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=CHUNK)
            elif HAS_SD:
                stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16', blocksize=CHUNK)
                stream.start()
            else:
                return # Can't interrupt if no microphone access
                
            # Give a 0.5s grace period so we don't instantly interrupt from the speaker pop
            import time
            time.sleep(0.5)
            
            consecutive_speech = 0
            while cls._speaking:
                if HAS_PYAUDIO:
                    chunk = stream.read(CHUNK, exception_on_overflow=False)
                    audio_int16 = np.frombuffer(chunk, np.int16)
                else:
                    chunk, overflow = stream.read(CHUNK)
                    audio_int16 = chunk.flatten()
                
                if has_vad:
                    audio_float32 = torch.from_numpy(audio_int16.astype(np.float32) / 32768.0)
                    prob = vad_model(audio_float32, 16000).item()
                    
                    if prob > 0.8:
                        consecutive_speech += 1
                    else:
                        consecutive_speech = 0
                else:
                    consecutive_speech = 0
                    
                if consecutive_speech >= 4:
                    cls._interrupt_flag = True
                    try:
                        import pygame
                        pygame.mixer.music.stop()
                    except ImportError:
                        pass
                    break
        except Exception as e:
            print(f"[VAD Interrupt] Error: {e}")
        finally:
            if HAS_PYAUDIO:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            elif HAS_SD:
                stream.stop()
                stream.close()
