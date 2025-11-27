"""
Tests for encryption and decryption utilities.

Tests focus on critical workflows:
- Encryption produces valid Fernet tokens
- Decryption recovers original plaintext
- Decryption fails gracefully with corrupted data
"""

import pytest
import os
from cryptography.fernet import Fernet, InvalidToken

# Generate a test encryption key
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode('utf-8')


@pytest.fixture(autouse=True)
def setup_encryption_key():
    """Set up test encryption key in environment."""
    os.environ['CREDENTIAL_ENCRYPTION_KEY'] = TEST_ENCRYPTION_KEY
    # Reload the encryption module to pick up the test key
    import importlib
    import sys
    if 'src.encryption' in sys.modules:
        del sys.modules['src.encryption']
    yield
    # Cleanup
    if 'CREDENTIAL_ENCRYPTION_KEY' in os.environ:
        del os.environ['CREDENTIAL_ENCRYPTION_KEY']


def test_encryption_produces_valid_fernet_token():
    """Test that encryption produces a valid Fernet token."""
    from src.encryption import encrypt

    plaintext = 'my_secure_password_123'
    encrypted = encrypt(plaintext)

    # Verify it's a string
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    # Fernet tokens start with 'gAAAAA' base64 prefix
    assert encrypted.startswith('gAAAAA')


def test_decryption_recovers_original_plaintext():
    """Test that decryption recovers the original plaintext."""
    from src.encryption import encrypt, decrypt

    plaintext = 'test_password_with_special_chars!@#$%'
    encrypted = encrypt(plaintext)
    decrypted = decrypt(encrypted)

    assert decrypted == plaintext


def test_decryption_fails_gracefully_with_corrupted_data():
    """Test that decryption fails gracefully with corrupted encrypted data."""
    from src.encryption import decrypt

    corrupted_data = 'invalid_base64_token_data!!!'

    with pytest.raises((InvalidToken, Exception)):
        decrypt(corrupted_data)


def test_encryption_different_each_time():
    """Test that encrypting the same plaintext produces different ciphertexts (due to IV)."""
    from src.encryption import encrypt

    plaintext = 'same_password'
    encrypted1 = encrypt(plaintext)
    encrypted2 = encrypt(plaintext)

    # Different IVs mean different ciphertexts even for same plaintext
    assert isinstance(encrypted1, str)
    assert isinstance(encrypted2, str)
    assert len(encrypted1) > 0
    assert len(encrypted2) > 0
    # Fernet tokens have randomness so they should be different
    assert encrypted1 != encrypted2


def test_encryption_handles_empty_string():
    """Test that encryption handles empty strings."""
    from src.encryption import encrypt, decrypt

    plaintext = ''
    encrypted = encrypt(plaintext)
    decrypted = decrypt(encrypted)

    assert decrypted == plaintext


def test_encryption_handles_unicode_passwords():
    """Test that encryption handles unicode passwords."""
    from src.encryption import encrypt, decrypt

    plaintext = 'пароль_с_кириллицей_123'  # Cyrillic characters
    encrypted = encrypt(plaintext)
    decrypted = decrypt(encrypted)

    assert decrypted == plaintext
