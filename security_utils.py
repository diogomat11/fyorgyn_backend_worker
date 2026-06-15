# security_utils.py — Utilitários de criptografia Fernet para senhas
import os
from cryptography.fernet import Fernet

FERNET_SECRET = os.getenv("FERNET_SECRET", "")


def encrypt_password(password: str) -> str:
    """Criptografa uma senha usando Fernet."""
    f = Fernet(FERNET_SECRET.encode())
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Descriptografa uma senha criptografada com Fernet."""
    f = Fernet(FERNET_SECRET.encode())
    return f.decrypt(encrypted.encode()).decode()
