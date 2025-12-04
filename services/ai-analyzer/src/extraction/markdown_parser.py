"""
Markdown parsing utilities for LLM response extraction.

Provides functions to parse markdown sections from LLM responses and extract
structured data like trading operations from marked sections.
"""

import re
import json
from typing import Dict, Tuple, List, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_markdown_sections(response_text: str) -> Dict[str, str]:
    """
    Extract markdown sections from LLM response.

    Finds all ## Section Name patterns and extracts content until next ## or EOF.
    Section names are normalized to lowercase.

    Sections marked with ##, e.g.:
    ## Summary
    text...
    ## Trading Operations
    [...JSON...]

    Args:
        response_text: Raw LLM response with markdown sections

    Returns:
        Dict mapping section names (lowercase) to content
    """
    if not response_text or not isinstance(response_text, str):
        logger.debug("parse_markdown_sections: empty or non-string response")
        return {}

    sections = {}

    # Find all ## Section Name patterns with content until next ## or EOF
    # Pattern matches: ##\s*SectionName\n content until next ## or end
    pattern = r'##\s*(?P<section_name>[\w\s]+?)\s*\n(?P<content>.*?)(?=##|$)'

    try:
        for match in re.finditer(pattern, response_text, re.DOTALL | re.IGNORECASE):
            section_name = match.group('section_name').strip().lower()
            content = match.group('content').strip()
            sections[section_name] = content

            logger.debug(
                f"Extracted markdown section",
                extra={"section_name": section_name, "content_length": len(content)}
            )
    except Exception as e:
        logger.warning(
            f"Error parsing markdown sections: {str(e)}",
            extra={"error": str(e)}
        )
        return {}

    return sections


def extract_section(
    sections_dict: Dict[str, str],
    *section_names: str
) -> str:
    """
    Extract section content from parsed sections dict.

    Looks for section using provided names in order (case-insensitive).
    Returns content of first matching section.

    Args:
        sections_dict: Dict from parse_markdown_sections()
        *section_names: Variable args for section names to try

    Returns:
        Section content as string, or empty string if not found
    """
    for section_name in section_names:
        normalized_name = section_name.lower().strip()
        if normalized_name in sections_dict:
            return sections_dict[normalized_name]

    logger.debug(
        f"Section not found in parsed markdown",
        extra={"requested_sections": section_names}
    )
    return ""


def extract_trading_operations(
    section_content: str,
    context_text: str = ""
) -> Tuple[List[Dict], bool]:
    """
    Extract trading operations from markdown section.

    Looks for JSON array in section content. Sets operations_found=True
    only if valid operations array is found with at least one operation
    that has required fields (action, symbol).

    Args:
        section_content: Content from Trading Operations/Trading Signals section
        context_text: Full raw text (for future confidence scoring if needed)

    Returns:
        Tuple of (operations_list, operations_found_boolean)
        - operations_list: List of operation dicts, empty if none found
        - operations_found: Boolean indicating if valid operations were found
    """
    operations = []
    operations_found = False

    if not section_content or not isinstance(section_content, str):
        logger.debug("extract_trading_operations: empty or non-string section")
        return operations, operations_found

    section_content = section_content.strip()
    if not section_content:
        return operations, operations_found

    try:
        # Find JSON array in content: search for [ followed by ] with content between
        json_match = re.search(r'\[.*?\]', section_content, re.DOTALL)

        if not json_match:
            logger.debug("extract_trading_operations: no JSON array found in section")
            return operations, operations_found

        json_str = json_match.group(0)
        operations = json.loads(json_str)

        # Validate operations is a list
        if not isinstance(operations, list):
            logger.warning(
                "extract_trading_operations: JSON is not an array",
                extra={"type": type(operations).__name__}
            )
            return [], False

        # Mark as found only if list has elements with required fields
        for op in operations:
            if isinstance(op, dict) and 'action' in op and 'symbol' in op:
                operations_found = True
                break

        if operations_found:
            logger.info(
                f"Found trading operations",
                extra={"count": len(operations), "operations_found": True}
            )
        else:
            logger.debug(
                "extract_trading_operations: no valid operations with required fields",
                extra={"array_length": len(operations)}
            )

        return operations, operations_found

    except json.JSONDecodeError as e:
        logger.warning(
            f"extract_trading_operations: JSON parsing failed",
            extra={"error": str(e), "content_preview": section_content[:200]}
        )
        return [], False

    except Exception as e:
        logger.warning(
            f"extract_trading_operations: unexpected error",
            extra={"error": str(e), "error_type": type(e).__name__}
        )
        return [], False
