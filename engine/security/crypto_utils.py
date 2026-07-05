from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os, base64, json, time, uuid

class SecurityError(Exception):
    pass

class CommandCrypto:
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits for GCM
    
    def __init__(self, master_key: bytes):
        # Derive command-specific key using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=None,
            info=b"jk-command-key",
        )
        self.key = hkdf.derive(master_key)
        self.aesgcm = AESGCM(self.key)
    
    def encrypt_command(self, command: str) -> str:
        # Include timestamp and UUID to prevent replay attacks
        payload = json.dumps({
            "cmd": command,
            "ts": time.time(),
            "nonce": str(uuid.uuid4()),
        })
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self.aesgcm.encrypt(nonce, payload.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()
    
    def decrypt_command(self, encrypted: str) -> dict:
        data = base64.b64decode(encrypted.encode())
        nonce, ciphertext = data[:self.NONCE_SIZE], data[self.NONCE_SIZE:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        payload = json.loads(plaintext.decode())
        
        # Replay attack check: reject commands older than 30 seconds
        if time.time() - payload["ts"] > 30:
            raise SecurityError("Command timestamp expired — possible replay attack")
        return payload

def encrypt_command(command: str) -> str:
    # Example wrapper for CLI
    # In a real scenario, this key should be loaded from a secure vault
    dummy_key = b"0" * 32 
    crypto = CommandCrypto(dummy_key)
    return crypto.encrypt_command(command)

def decrypt_response(encrypted: str) -> str:
    # Example wrapper
    dummy_key = b"0" * 32 
    crypto = CommandCrypto(dummy_key)
    return crypto.decrypt_command(encrypted)["cmd"]
