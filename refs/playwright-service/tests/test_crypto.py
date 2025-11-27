import os
import pytest
import json
from cryptography.fernet import Fernet
from utils.crypto import CredentialManager
from utils.logger import configure_logger, get_logger
import structlog
from io import StringIO
import sys

# Set dummy secret key for testing
os.environ["SECRET_KEY"] = Fernet.generate_key().decode()

def test_credential_manager_encrypt_decrypt():
    cm = CredentialManager()
    username = "testuser"
    password = "supersecretpassword"
    
    encrypted = cm.encrypt_credentials(username, password)
    assert encrypted != password
    assert "supersecretpassword" not in encrypted
    
    decrypted_user, decrypted_pass = cm.decrypt_credentials(encrypted)
    assert decrypted_user == username
    assert decrypted_pass == password

def test_credential_manager_missing_key():
    del os.environ["SECRET_KEY"]
    with pytest.raises(ValueError, match="SECRET_KEY environment variable is not set"):
        CredentialManager()
    # Restore key for other tests
    os.environ["SECRET_KEY"] = Fernet.generate_key().decode()

def test_logger_redaction(capsys):
    configure_logger()
    logger = get_logger("test_logger")
    
    # We need to capture stdout/stderr
    # structlog.PrintLoggerFactory prints to stdout/stderr
    
    logger.info("Test log", password="supersecretpassword", username="testuser")
    
    captured = capsys.readouterr()
    output = captured.out
    
    assert "supersecretpassword" not in output
    assert "***REDACTED***" in output
    assert "testuser" in output

if __name__ == "__main__":
    # Manually run tests if executed as script
    try:
        test_credential_manager_encrypt_decrypt()
        print("test_credential_manager_encrypt_decrypt passed")
        
        # test_credential_manager_missing_key() # Skip this one in manual run as it messes with env
        print("test_credential_manager_missing_key skipped in manual run")

        # Mock capsys for manual run
        class MockCapsys:
            def readouterr(self):
                from collections import namedtuple
                Output = namedtuple('Output', ['out', 'err'])
                return Output(sys.stdout.getvalue(), "")
        
        # Redirect stdout to capture
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        test_logger_redaction(MockCapsys())
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        print("test_logger_redaction passed")
        
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()
