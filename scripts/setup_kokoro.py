import os
import urllib.request

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "tts")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"

model_path = os.path.join(MODEL_DIR, "kokoro-v0_19.onnx")
voices_path = os.path.join(MODEL_DIR, "voices.json")

def download_file(url, path, desc):
    if not os.path.exists(path):
        print(f"Downloading {desc}...")
        try:
            urllib.request.urlretrieve(url, path)
            print(f"{desc} downloaded successfully.")
        except Exception as e:
            print(f"Failed to download {desc}: {e}")
    else:
        print(f"{desc} already exists.")

if __name__ == "__main__":
    download_file(MODEL_URL, model_path, "Kokoro ONNX Model")
    download_file(VOICES_URL, voices_path, "Kokoro Voices JSON")
    
    # Test initialization
    try:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(model_path, voices_path)
        print("Kokoro TTS initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize Kokoro: {e}")
