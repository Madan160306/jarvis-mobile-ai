import os
import time
import pygame
import soundfile as sf
import traceback

# Initialize pygame mixer for audio playback
pygame.mixer.init()

class TTSEngine:
    _kokoro = None
    _voice = "af_heart"
    
    @classmethod
    def _get_kokoro(cls):
        if cls._kokoro is None:
            try:
                from kokoro_onnx import Kokoro
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                model_path = os.path.join(base_dir, "models", "tts", "kokoro-v1.0.onnx")
                voices_path = os.path.join(base_dir, "models", "tts", "voices-v1.0.bin")
                if os.path.exists(model_path) and os.path.exists(voices_path):
                    cls._kokoro = Kokoro(model_path, voices_path)
                    print("[TTS] Kokoro ONNX initialized successfully.")
                else:
                    print(f"[TTS] ERROR: Kokoro models not found in {os.path.join(base_dir, 'models', 'tts')}")
            except ImportError:
                print("[TTS] kokoro_onnx not installed. Falling back to native Termux TTS.")
                cls._kokoro = "TERMUX_LITE"
            except Exception as e:
                print(f"[TTS] Kokoro init failed: {e}")
        return cls._kokoro

    @staticmethod
    def speak(text: str, lang: str = 'en'):
        print(f"JK: {text}")
        
        kokoro = TTSEngine._get_kokoro()
        if not kokoro:
            print("[TTS] Cannot speak, Kokoro engine is not loaded.")
            return

        if kokoro == "TERMUX_LITE":
            # Termux Lite Mode: Use native Android TTS engine with zero CPU overhead!
            import subprocess
            try:
                subprocess.run(["termux-tts-speak", text], check=True)
            except Exception as e:
                print(f"[TTS] Termux native TTS failed: {e}")
            return

        try:
            # We split by newlines or long punctuation if needed, but Kokoro handles short paragraphs well
            samples, sample_rate = kokoro.create(
                text, voice=TTSEngine._voice, speed=1.1, lang="en-us"
            )
            
            # Save and play immediately
            audio_file = f"temp_jk_{int(time.time()*1000)}.wav"
            sf.write(audio_file, samples, sample_rate)
            
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(30)
                
            pygame.mixer.music.unload()
            
            # Cleanup
            time.sleep(0.05)
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
        except Exception as e:
            print(f"[ERROR] Kokoro TTS failed: {e}")
            traceback.print_exc()

def speak(text: str, lang: str = 'en'):
    TTSEngine.speak(text, lang)