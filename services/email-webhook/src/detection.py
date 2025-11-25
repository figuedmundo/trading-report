"""
Keyword-based report detection logic.

Detects trading reports using configurable keywords matched against email
subject and body content (case-insensitive).
"""

import re
import logging
from typing import List, Tuple
from config import get_config

logger = logging.getLogger(__name__)


def detect_trading_report(subject: str, body: str) -> Tuple[bool, List[str]]:
    """
    Detect if email contains a trading report based on keyword matching.

    Args:
        subject: Email subject line
        body: Email body text

    Returns:
        Tuple of (is_report_detected, matched_keywords)
    """
    config = get_config()
    keywords = config.report_keywords

    matched = []

    # Combine subject and body for searching
    content = f"{subject} {body}".lower()

    # Match keywords (case-insensitive)
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            continue

        # Use word boundaries for more precise matching
        pattern = r"\b" + re.escape(keyword_lower) + r"\b"
        if re.search(pattern, content):
            matched.append(keyword)

    is_detected = len(matched) > 0

    if is_detected:
        logger.info(f"Trading report detected with keywords: {matched}")
    else:
        logger.debug("No trading report keywords found")

    return is_detected, matched
