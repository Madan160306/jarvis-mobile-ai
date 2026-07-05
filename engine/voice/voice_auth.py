import numpy as np
try:
    from sklearn.metrics.pairwise import cosine_similarity
    import librosa
    HAS_BIOMETRICS = True
except Exception:
    HAS_BIOMETRICS = False

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False
import os

class VoiceAuthenticator:
    THRESHOLD = 0.65  # Minimum similarity score
    SAMPLE_RATE = 16000
    DURATION = 3  # Seconds to record for auth
    
    def __init__(self, owner_embedding_path: str):
        self.owner_embedding_path = owner_embedding_path
        if os.path.exists(owner_embedding_path):
            self.owner_embedding = np.load(owner_embedding_path)
        else:
            self.owner_embedding = None
    
    def record_sample(self) -> np.ndarray:
        print("[*] Recording voice sample for authentication...")
        if not HAS_SD:
            print("[!] sounddevice not available for recording.")
            return np.zeros(int(self.DURATION * self.SAMPLE_RATE))
            
        audio = sd.rec(
            int(self.DURATION * self.SAMPLE_RATE),
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        audio = audio.flatten()
        
        # Simple energy check to prevent authenticating on absolute silence
        rms = np.sqrt(np.mean(audio**2))
        if rms < 0.0005: # Ultra-low threshold for quiet microphones
            print("[!] Audio too quiet. Please speak louder.")
            return np.zeros_like(audio)
            
        return audio
    
    def extract_embedding(self, audio: np.ndarray) -> np.ndarray:
        if np.all(audio == 0) or not HAS_BIOMETRICS:
            return np.zeros((1, 40))
            
        # Normalize and extract MFCC features
        audio = librosa.util.normalize(audio)
        mfcc = librosa.feature.mfcc(y=audio, sr=self.SAMPLE_RATE, n_mfcc=40)
        return np.mean(mfcc, axis=1).reshape(1, -1)
    
    def enroll_owner(self):
        print("[*] Enrolling owner voice... Please speak for 3 seconds.")
        audio = self.record_sample()
        embedding = self.extract_embedding(audio)
        dirname = os.path.dirname(self.owner_embedding_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        np.save(self.owner_embedding_path, embedding)
        self.owner_embedding = embedding
        print("[+] Owner voice enrolled successfully.")

    def authenticate(self) -> bool:
        if self.owner_embedding is None or not HAS_BIOMETRICS:
            print("[-] No owner voice enrolled or biometrics disabled.")
            return False
            
        audio = self.record_sample()
        if np.all(audio == 0):
            return False # Already printed error in record_sample
            
        embedding = self.extract_embedding(audio)
        similarity = cosine_similarity(embedding, self.owner_embedding)[0][0]
        print(f"Voice similarity score: {similarity:.2f}")
        return similarity >= self.THRESHOLD

    def authenticate_buffer(self, audio: np.ndarray) -> bool:
        """Authenticates a pre-recorded audio buffer (float32 array)."""
        if self.owner_embedding is None or not HAS_BIOMETRICS:
            return True  # Open access if no owner enrolled or if biometrics disabled (Termux Lite)
            
        if np.all(audio == 0):
            return False
            
        embedding = self.extract_embedding(audio)
        similarity = cosine_similarity(embedding, self.owner_embedding)[0][0]
        print(f"[Voice Biometrics] Command similarity score: {similarity:.2f}")
        return similarity >= self.THRESHOLD

if __name__ == "__main__":
    import sys
    auth = VoiceAuthenticator("owner_voice.npy")
    if len(sys.argv) > 1 and sys.argv[1] == "enroll":
        auth.enroll_owner()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        if auth.authenticate():
            print("Access Granted!")
        else:
            print("Access Denied!")
    else:
        print("Usage: python engine/voice/voice_auth.py [enroll|test]")
