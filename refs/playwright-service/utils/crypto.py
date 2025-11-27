import os
import json
import base64
from cryptography.fernet import Fernet
from typing import Tuple, Optional

class CredentialManager:
    """
    Manages encryption and decryption of credentials.
    Uses Fernet symmetric encryption.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize with a secret key.
        If not provided, reads from SECRET_KEY env var.
        """
        self.key = secret_key or os.getenv("SECRET_KEY")
        if not self.key:
            raise ValueError("SECRET_KEY environment variable is not set")
        
        try:
            self.fernet = Fernet(self.key)
        except Exception as e:
            raise ValueError(f"Invalid SECRET_KEY: {str(e)}")

    def encrypt_credentials(self, username: str, password: str) -> str:
        """
        Encrypts username and password into a single string.
        Format: JSON {"u": username, "p": password} -> Encrypted
        """
        data = json.dumps({"u": username, "p": password}).encode('utf-8')
        encrypted = self.fernet.encrypt(data)
        return encrypted.decode('utf-8')

    def decrypt_credentials(self, encrypted_data: str) -> Tuple[str, str]:
        """
        Decrypts data and returns (username, password).
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode('utf-8'))
            data = json.loads(decrypted.decode('utf-8'))
            return data.get("u"), data.get("p")
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")
