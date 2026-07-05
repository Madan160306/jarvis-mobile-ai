import numpy as np
import os
import json

try:
    from openwakeword.model import Model
    import openwakeword
    openwakeword.utils.download_models()
    HAS_OWW = True
except ImportError:
    HAS_OWW = False

class WakeWordEngine:
    def __init__(self, access_key=None, wake_word="hey_jarvis"):
        self.wake_word = wake_word
        # 0.45 based on Madan's voice profile
        self.threshold = 0.45 
        
        # Check if we are in Termux
        in_termux = os.path.exists('/data/data/com.termux')
        
        if HAS_OWW and not in_termux:
            try:
                print(f"Loading openwakeword model: {wake_word}...")
                self.oww_model = Model(
                    wakeword_models=[wake_word],
                    inference_framework="onnx"
                )
                self.engine = "openwakeword"
            except Exception as e:
                print(f"[Error] Failed to initialize openwakeword: {e}")
                self.engine = "vosk"
        else:
            self.engine = "vosk"
            
        if self.engine == "vosk":
            try:
                from vosk import Model as VoskModel, KaldiRecognizer
                print("[WakeWord] Using Vosk Wake Word fallback for Mobile/Termux...")
                vosk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "vosk-model-small-en-us-0.15")
                if os.path.exists(vosk_path):
                    self.vosk_model = VoskModel(vosk_path)
                    self.rec = KaldiRecognizer(self.vosk_model, 16000)
                    self.engine = "vosk"
                else:
                    self.engine = "manual"
                    print(f"[WakeWord] Vosk model not found at {vosk_path}. Defaulting to manual mode.")
            except Exception as e:
                print(f"[WakeWord] Failed to initialize Vosk: {e}")
                self.engine = "manual"
            
    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Process an audio chunk to detect the wake word.
        Args:
            audio_chunk: A numpy array of int16 audio data.
        """
        if self.engine == "openwakeword":
            prediction = self.oww_model.predict(audio_chunk)
            for ww, score in prediction.items():
                if score >= self.threshold:
                    return True
            return False
            
        elif self.engine == "vosk":
            # Convert numpy array to bytes for Vosk
            audio_bytes = audio_chunk.tobytes()
            if self.rec.AcceptWaveform(audio_bytes):
                result = json.loads(self.rec.Result())
                text = result.get("text", "").lower()
                if "jarvis" in text or "hey jarvis" in text:
                    print(f"[WakeWord] Vosk triggered on: '{text}'")
                    # Reset recognizer to clear buffer
                    self.rec.Reset()
                    return True
            else:
                # Check partial result to trigger instantly without waiting for silence
                partial = json.loads(self.rec.PartialResult())
                text = partial.get("partial", "").lower()
                if "jarvis" in text or "hey jarvis" in text:
                    print(f"[WakeWord] Vosk partial triggered on: '{text}'")
                    self.rec.Reset()
                    return True
            return False
            
        return False

    def reset(self):
        """Reset the internal buffer."""
        if self.engine == "openwakeword":
            self.oww_model.reset()
        elif self.engine == "vosk" and hasattr(self, "rec"):
            self.rec.Reset()
