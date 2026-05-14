import base64

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    # Ensure the key is 32 url-safe base64 bytes as Fernet requires
    key = settings.encryption_key.encode()
    padded = base64.urlsafe_b64encode(key[:32].ljust(32, b"\x00"))
    return Fernet(padded)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
