#!/usr/bin/env python3
"""
Generate a Fernet encryption key for credential storage.

Fernet provides symmetric encryption using AES-128 CBC with HMAC SHA256.
The key generated is a base64-encoded 32-byte value.

Usage:
    python scripts/generate_encryption_key.py

Output:
    Prints a base64-encoded key suitable for the CREDENTIAL_ENCRYPTION_KEY environment variable.

Security Notes:
    - Store the key in a secure location (.env file with chmod 600)
    - Keep development and production keys separate
    - Rotate keys periodically (requires re-encryption of all credentials)
    - Do NOT commit the key to version control
"""

from cryptography.fernet import Fernet


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        str: Base64-encoded key suitable for environment variable
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


def main():
    """Generate and print a new encryption key."""
    key = generate_encryption_key()

    print('\n' + '=' * 70)
    print('Generated Fernet Encryption Key')
    print('=' * 70)
    print('\nKey:')
    print(key)
    print('\nAdd to .env file:')
    print(f'CREDENTIAL_ENCRYPTION_KEY={key}')
    print('\nOr set as environment variable:')
    print(f'export CREDENTIAL_ENCRYPTION_KEY="{key}"')
    print('\nSecurity Notes:')
    print('- Store in secure location (restricted file permissions)')
    print('- Keep development and production keys separate')
    print('- Rotate periodically (requires re-encryption of all credentials)')
    print('- Do NOT commit to version control')
    print('=' * 70 + '\n')


if __name__ == '__main__':
    main()
