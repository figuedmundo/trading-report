"""IP address and CIDR range utilities.

Provides functions for IP address validation and CIDR range matching.
"""

import ipaddress
from typing import Union


def is_ip_in_cidr(ip_address: str, cidr_range: str) -> bool:
    """Check if an IP address is within a CIDR range.

    Args:
        ip_address: IP address as string (e.g., "192.168.1.5")
        cidr_range: CIDR range as string (e.g., "192.168.1.0/24")

    Returns:
        True if IP is within the CIDR range, False otherwise

    Raises:
        ValueError: If IP address or CIDR range format is invalid
    """
    try:
        # Parse the IP address
        ip_obj = ipaddress.ip_address(ip_address)

        # Parse the CIDR range
        network_obj = ipaddress.ip_network(cidr_range, strict=False)

        # Check if IP is in the network
        return ip_obj in network_obj

    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as e:
        raise ValueError(
            f"Invalid IP address or CIDR range format: ip={ip_address}, cidr={cidr_range}"
        ) from e


def validate_ip_address(ip_address: str) -> bool:
    """Validate if a string is a valid IP address.

    Args:
        ip_address: IP address as string

    Returns:
        True if valid IP address, False otherwise
    """
    try:
        ipaddress.ip_address(ip_address)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def validate_cidr_range(cidr_range: str) -> bool:
    """Validate if a string is a valid CIDR range.

    Args:
        cidr_range: CIDR range as string

    Returns:
        True if valid CIDR range, False otherwise
    """
    try:
        ipaddress.ip_network(cidr_range, strict=False)
        return True
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError):
        return False
