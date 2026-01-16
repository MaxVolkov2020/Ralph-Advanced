"""
Encryption utilities for sensitive data (git tokens, credentials)
Uses Fernet symmetric encryption with key from environment variable
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken


def get_encryption_key() -> bytes:
    """
    Get encryption key from environment variable.
    Key must be 32 bytes, base64 encoded (44 characters).

    Generate a new key with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # For development, use a default key (CHANGE IN PRODUCTION!)
        # This allows the system to work without configuration
        key = "ralph-advanced-default-encryption-key-32b="
        # Ensure it's valid base64 and 32 bytes
        key = base64.urlsafe_b64encode(key[:32].encode()).decode()
    return key.encode()


def get_fernet() -> Fernet:
    """Get Fernet instance with encryption key"""
    return Fernet(get_encryption_key())


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext string.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    if not plaintext:
        return ""

    f = get_fernet()
    encrypted = f.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_value(ciphertext: str) -> Optional[str]:
    """
    Decrypt an encrypted string.

    Args:
        ciphertext: The encrypted string to decrypt

    Returns:
        Decrypted plaintext string, or None if decryption fails
    """
    if not ciphertext:
        return None

    try:
        f = get_fernet()
        decrypted = f.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        # Invalid token - either corrupted or wrong key
        return None
    except Exception:
        return None


def generate_encryption_key() -> str:
    """
    Generate a new encryption key.
    Use this to create a key for the ENCRYPTION_KEY environment variable.

    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    return Fernet.generate_key().decode()


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted (Fernet format).
    Fernet tokens start with 'gAAAAA' when base64 encoded.

    Args:
        value: String to check

    Returns:
        True if value appears to be Fernet-encrypted
    """
    if not value or len(value) < 10:
        return False
    return value.startswith('gAAAAA')
