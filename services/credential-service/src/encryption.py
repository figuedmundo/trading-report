"""
Encryption and decryption utilities for credential management.

Provides symmetric encryption using Fernet (AES-128 CBC with HMAC SHA256 authentication)
from the cryptography library. The master encryption key is loaded from the environment
variable CREDENTIAL_ENCRYPTION_KEY at module initialization.

Credentials are encrypted before storage in the database and decrypted on retrieval
from the credential service API.
"""

import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Global cipher instance
_cipher = None


def _load_encryption_key():
    """
    Load and validate the encryption key from environment variable.

    The key must be a 32-byte base64-encoded Fernet key.
    This is called at module import time.

    Raises:
        ValueError: If key is missing or invalid format
    """
    key = os.environ.get('CREDENTIAL_ENCRYPTION_KEY')

    if not key:
        error_msg = 'CREDENTIAL_ENCRYPTION_KEY environment variable not set'
        logger.critical(error_msg)
        raise ValueError(error_msg)

    try:
        # Validate by attempting to create a Fernet cipher
        Fernet(key)
        return key
    except Exception as e:
        error_msg = 'CREDENTIAL_ENCRYPTION_KEY must be 32-byte base64-encoded Fernet key'
        logger.critical(f'{error_msg}: {str(e)}')
        raise ValueError(error_msg)


def _get_cipher():
    """
    Get or initialize the Fernet cipher instance.

    Returns:
        Fernet: Cipher instance for encryption/decryption
    """
    global _cipher
    if _cipher is None:
        key = _load_encryption_key()
        _cipher = Fernet(key)
    return _cipher


def encrypt(plaintext: str) -> str:
    """
    Encrypt a plaintext string to a base64-encoded Fernet token.

    Args:
        plaintext: The password or sensitive data to encrypt

    Returns:
        str: Base64-encoded Fernet token suitable for storage in TEXT column

    Raises:
        Exception: If encryption fails (should not occur in normal operation)
    """
    try:
        cipher = _get_cipher()
        plaintext_bytes = plaintext.encode('utf-8')
        encrypted_bytes = cipher.encrypt(plaintext_bytes)
        # Fernet token is already base64-encoded
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f'Encryption failed: {str(e)}')
        raise


def decrypt(encrypted_data: str) -> str:
    """
    Decrypt a base64-encoded Fernet token to plaintext.

    Args:
        encrypted_data: Base64-encoded Fernet token from database

    Returns:
        str: Decrypted plaintext

    Raises:
        InvalidToken: If token is corrupted or decryption key is wrong
        Exception: For other decryption failures
    """
    try:
        cipher = _get_cipher()
        encrypted_bytes = encrypted_data.encode('utf-8')
        plaintext_bytes = cipher.decrypt(encrypted_bytes)
        return plaintext_bytes.decode('utf-8')
    except InvalidToken as e:
        logger.error(f'Decryption failed - invalid token or wrong key: {str(e)}')
        raise
    except Exception as e:
        logger.error(f'Decryption failed: {str(e)}')
        raise


# Initialize cipher on module import
try:
    _get_cipher()
except ValueError as e:
    # Log critical error but don't raise - let application handle startup failure
    logger.critical(f'Failed to initialize encryption: {str(e)}')
