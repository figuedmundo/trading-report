"""Spanish date parsing for trading reports."""

import re
import logging
from datetime import datetime
from typing import Optional
import pytz

logger = logging.getLogger(__name__)

# Spanish month name to number mapping
SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# Date format pattern: "26 de noviembre de 2025 a las 15:44"
DATE_PATTERN = r'(\d+)\s+de\s+(\w+)\s+de\s+(\d+)\s+a\s+las\s+(\d+):(\d+)'


def parse_spanish_date(date_string: str) -> Optional[datetime]:
    """
    Parse Spanish date format to UTC datetime.

    Parses format: "26 de noviembre de 2025 a las 15:44"
    Assumes local timezone is Europe/Madrid and converts to UTC.

    Args:
        date_string: Date string in Spanish format

    Returns:
        datetime in UTC timezone, or None if parsing fails
    """
    if not date_string or not isinstance(date_string, str):
        logger.warning(f"Invalid date string provided: {date_string}")
        return None

    try:
        # Extract components using regex
        match = re.search(DATE_PATTERN, date_string)
        if not match:
            logger.warning(f"Date string does not match expected pattern: {date_string}")
            return None

        day_str, month_name, year_str, hour_str, minute_str = match.groups()

        # Convert to integers
        day = int(day_str)
        year = int(year_str)
        hour = int(hour_str)
        minute = int(minute_str)

        # Map Spanish month name to number
        month_lower = month_name.lower()
        if month_lower not in SPANISH_MONTHS:
            logger.warning(f"Unknown Spanish month name: {month_name}")
            return None

        month = SPANISH_MONTHS[month_lower]

        # Create datetime in Europe/Madrid timezone
        madrid_tz = pytz.timezone("Europe/Madrid")
        local_dt = madrid_tz.localize(datetime(year, month, day, hour, minute))

        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.utc)

        return utc_dt

    except ValueError as e:
        logger.warning(f"Date value error for '{date_string}': {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error parsing date '{date_string}': {e}")
        return None
