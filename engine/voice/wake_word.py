import numpy as np
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
        
        if HAS_OWW:
            try:
                print(f"Loading openwakeword model: {wake_word}...")
                self.oww_model = Model(
                    wakeword_models=[wake_word],
                    inference_framework="onnx"
                )
                self.engine = "openwakeword"
            except Exception as e:
                print(f"[Error] Failed to initialize openwakeword: {e}")
                self.engine = "manual"
        else:
            self.engine = "manual"
            print("[WakeWord] openwakeword not installed. Defaulting to manual mode.")
            
    def process_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Process an audio chunk to detect the wake word.
        Args:
            audio_chunk: A numpy array of int16 audio data.
        """
        if self.engine != "openwakeword":
            return False
            
        # IMPORTANT: We removed the 3.0x gain multiplier because it caused severe integer clipping
        # and prevented the wake word from triggering when shouting.
        prediction = self.oww_model.predict(audio_chunk)
        
        for ww, score in prediction.items():
            if score >= self.threshold:
                return True
                
        return False

    def reset(self):
        """Reset the internal buffer."""
        if self.engine == "openwakeword":
            self.oww_model.reset()
