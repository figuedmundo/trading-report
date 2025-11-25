"""
Pytest configuration and fixtures.

Sets up mocks for psycopg2 and other dependencies that may not be available
in test environment.
"""

import sys
from unittest.mock import MagicMock

# Mock psycopg2 before any module imports
sys.modules["psycopg2"] = MagicMock()
sys.modules["psycopg2.pool"] = MagicMock()
