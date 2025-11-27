"""
Tests for log sanitization utility.

Tests focus on critical workflows:
- Password field redaction in plain text logs
- Credential field redaction in JSON logs
- Multiple sensitive fields redacted in single message
"""

import pytest
import json
from src.logging_utils import sanitize_log_message, sanitize_dict


def test_password_redaction_in_plain_text():
    """Test password field redaction in plain text logs."""
    message = 'User login failed: password=mySecurePassword123'
    sanitized = sanitize_log_message(message)

    assert '[REDACTED]' in sanitized
    assert 'mySecurePassword123' not in sanitized
    assert 'password=' in sanitized  # Field name preserved


def test_credential_redaction_in_json():
    """Test credential field redaction in JSON logs."""
    data = {
        'event': 'login_attempt',
        'credential': 'super_secret_cred',
        'username': 'john_doe',
    }
    message = json.dumps(data)
    sanitized = sanitize_log_message(message)

    # Parse back to verify structure
    parsed = json.loads(sanitized)
    assert parsed['credential'] == '[REDACTED]'
    assert parsed['username'] == 'john_doe'  # Non-sensitive field preserved


def test_multiple_sensitive_fields_redacted():
    """Test multiple sensitive fields redacted in single message."""
    message = 'API call with password=secret1 and api_key=key123 and token=abc123xyz'
    sanitized = sanitize_log_message(message)

    assert sanitized.count('[REDACTED]') == 3
    assert 'secret1' not in sanitized
    assert 'key123' not in sanitized
    assert 'abc123xyz' not in sanitized
    assert 'password=' in sanitized
    assert 'api_key=' in sanitized
    assert 'token=' in sanitized


def test_encrypted_data_redaction():
    """Test encrypted_data field redaction."""
    message = 'Storing encrypted_data=gAAAAABh7kPY8V9_encrypted_token_value'
    sanitized = sanitize_log_message(message)

    assert '[REDACTED]' in sanitized
    assert 'gAAAAABh7kPY8V9_encrypted_token_value' not in sanitized


def test_auth_field_redaction():
    """Test auth field redaction (case-insensitive)."""
    message = 'Authorization header: Auth=Bearer123 or SECRET=value456'
    sanitized = sanitize_log_message(message)

    assert sanitized.count('[REDACTED]') >= 2
    assert 'Bearer123' not in sanitized
    assert 'value456' not in sanitized


def test_non_sensitive_fields_preserved():
    """Test that non-sensitive fields are preserved."""
    message = 'User email=user@example.com and domain=broker.com status=active'
    sanitized = sanitize_log_message(message)

    assert 'user@example.com' in sanitized
    assert 'broker.com' in sanitized
    assert 'status=active' in sanitized
    assert '[REDACTED]' not in sanitized


def test_sanitize_dict_function():
    """Test sanitize_dict function for structured data."""
    data = {
        'domain': 'broker.com',
        'username': 'john',
        'password': 'secret123',
        'api_key': 'key123',
        'metadata': {
            'token': 'xyz789',
            'login_url': 'https://broker.com/login',
        }
    }

    sanitized = sanitize_dict(data)

    assert sanitized['domain'] == 'broker.com'
    assert sanitized['username'] == 'john'
    assert sanitized['password'] == '[REDACTED]'
    assert sanitized['api_key'] == '[REDACTED]'
    assert sanitized['metadata']['token'] == '[REDACTED]'
    assert sanitized['metadata']['login_url'] == 'https://broker.com/login'


def test_empty_message_handling():
    """Test handling of empty messages."""
    assert sanitize_log_message('') == ''
    assert sanitize_log_message(None) is None


def test_json_with_null_and_arrays():
    """Test JSON logs with null values and arrays."""
    data = {
        'passwords': ['pass1', 'pass2'],
        'secret': None,
        'metadata': {
            'key': None,
            'items': ['item1', 'item2']
        }
    }

    message = json.dumps(data)
    sanitized = sanitize_log_message(message)
    parsed = json.loads(sanitized)

    assert parsed['passwords'] == '[REDACTED]'
    assert parsed['secret'] == '[REDACTED]'
    assert parsed['metadata']['key'] == '[REDACTED]'
