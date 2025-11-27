"""
Utility functions for masking sensitive data in logs and responses.

Masks email addresses, phone numbers, and API tokens to protect privacy.
"""

from typing import Optional


def mask_email(email: str) -> str:
    """
    Mask email address for logging.

    Example: user@example.com -> u***@example.com

    Args:
        email: Email address to mask

    Returns:
        Masked email address
    """
    if not email or "@" not in email:
        return "***"

    parts = email.split("@")
    if len(parts) != 2:
        return "***"

    local_part, domain = parts
    if len(local_part) <= 1:
        masked_local = "*" * len(local_part)
    else:
        masked_local = local_part[0] + "*" * (len(local_part) - 1)

    return f"{masked_local}@{domain}"


def mask_chat_id(chat_id: str) -> str:
    """
    Mask Telegram chat ID for logging.

    Example: 123456789 -> 123456****

    Args:
        chat_id: Chat ID to mask

    Returns:
        Masked chat ID
    """
    if not chat_id:
        return "***"

    if len(chat_id) <= 6:
        return "*" * len(chat_id)

    return chat_id[:6] + "*" * (len(chat_id) - 6)


def mask_phone(phone: str) -> str:
    """
    Mask phone number for logging.

    Example: +1234567890 -> +123****

    Args:
        phone: Phone number to mask

    Returns:
        Masked phone number
    """
    if not phone:
        return "***"

    # Find where the actual number starts (after country code)
    if phone.startswith("+"):
        prefix = phone[:4]  # +123
        if len(phone) > 4:
            return prefix + "*" * (len(phone) - 4)
        return prefix

    # No country code, just mask most of it
    if len(phone) <= 3:
        return "*" * len(phone)
    return phone[:3] + "*" * (len(phone) - 3)


def mask_api_token(token: str) -> str:
    """
    Mask API token for logging.

    Example: abc123def456 -> abc123***

    Args:
        token: Token to mask

    Returns:
        Masked token
    """
    if not token:
        return "***"

    if len(token) <= 4:
        return "*" * len(token)

    return token[:len(token) - 4] + "****"


def mask_recipient(recipient: str, channel: str) -> str:
    """
    Mask recipient based on channel type.

    Args:
        recipient: Recipient address/ID
        channel: Channel type (email, telegram, sms, etc.)

    Returns:
        Masked recipient
    """
    channel_lower = channel.lower().strip()

    if channel_lower == "email":
        return mask_email(recipient)
    elif channel_lower == "telegram":
        return mask_chat_id(recipient)
    elif channel_lower == "sms":
        return mask_phone(recipient)
    else:
        # Default: mask most of the string
        return mask_api_token(recipient)


def should_mask_in_logs(field_name: str) -> bool:
    """
    Determine if a field should be masked in logs.

    Args:
        field_name: Name of the field

    Returns:
        True if field should be masked
    """
    masking_keywords = {
        "password",
        "token",
        "secret",
        "key",
        "api_key",
        "credentials",
        "credential",
        "auth",
        "bearer",
        "email",
        "phone",
        "chat_id",
        "recipient",
    }

    return field_name.lower() in masking_keywords
