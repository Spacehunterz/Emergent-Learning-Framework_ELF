"""
Input validation functions for the Query System.

All validation functions raise ValidationError on invalid input.
"""

import re
from typing import List

# Import ValidationError with fallback for script execution
try:
    from .exceptions import ValidationError
except ImportError:
    from exceptions import ValidationError


# Validation constants
MAX_DOMAIN_LENGTH = 100
MAX_QUERY_LENGTH = 10000
MAX_TAG_COUNT = 50
MAX_TAG_LENGTH = 50
MIN_LIMIT = 1
MAX_LIMIT = 1000
DEFAULT_TIMEOUT = 30
MAX_TOKENS = 50000


def validate_domain(domain: str) -> str:
    """
    Validate domain string.

    Args:
        domain: Domain to validate

    Returns:
        Validated domain string

    Raises:
        ValidationError: If domain is invalid
    """
    if not domain:
        raise ValidationError(
            "Domain cannot be empty. Provide a valid domain name. [QS001]"
        )

    if len(domain) > MAX_DOMAIN_LENGTH:
        raise ValidationError(
            f"Domain exceeds maximum length of {MAX_DOMAIN_LENGTH} characters. "
            f"Use a shorter domain name. [QS001]"
        )

    # Allow alphanumeric, hyphen, underscore, and dot
    if not re.match(r'^[a-zA-Z0-9\-_.]+$', domain):
        raise ValidationError(
            f"Domain '{domain}' contains invalid characters. "
            f"Use only alphanumeric, hyphen, underscore, and dot. [QS001]"
        )

    return domain.strip()


def validate_limit(limit: int) -> int:
    """
    Validate limit parameter.

    Args:
        limit: Limit to validate

    Returns:
        Validated limit

    Raises:
        ValidationError: If limit is invalid
    """
    if not isinstance(limit, int):
        raise ValidationError(
            f"Limit must be an integer, got {type(limit).__name__}. [QS001]"
        )

    if limit < MIN_LIMIT:
        raise ValidationError(
            f"Limit must be at least {MIN_LIMIT}. Got: {limit}. [QS001]"
        )

    if limit > MAX_LIMIT:
        raise ValidationError(
            f"Limit exceeds maximum of {MAX_LIMIT}. "
            f"Use a smaller limit or process results in batches. [QS001]"
        )

    return limit


def validate_tags(tags: List[str]) -> List[str]:
    """
    Validate tags list.

    Args:
        tags: List of tags to validate

    Returns:
        Validated tags list

    Raises:
        ValidationError: If tags are invalid
    """
    if not isinstance(tags, list):
        raise ValidationError(
            f"Tags must be a list, got {type(tags).__name__}. [QS001]"
        )

    if len(tags) > MAX_TAG_COUNT:
        raise ValidationError(
            f"Too many tags (max {MAX_TAG_COUNT}). "
            f"Reduce number of tags or query in batches. [QS001]"
        )

    validated_tags = []
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue

        if len(tag) > MAX_TAG_LENGTH:
            raise ValidationError(
                f"Tag '{tag[:20]}...' exceeds maximum length of {MAX_TAG_LENGTH}. [QS001]"
            )

        if not re.match(r'^[a-zA-Z0-9\-_.]+$', tag):
            raise ValidationError(
                f"Tag '{tag}' contains invalid characters. "
                f"Use only alphanumeric, hyphen, underscore, and dot. [QS001]"
            )

        validated_tags.append(tag)

    if not validated_tags:
        raise ValidationError(
            "No valid tags provided after filtering. [QS001]"
        )

    return validated_tags


def validate_query(query: str) -> str:
    """
    Validate query string.

    Args:
        query: Query string to validate

    Returns:
        Validated query string

    Raises:
        ValidationError: If query is invalid
    """
    if not query:
        raise ValidationError(
            "Query string cannot be empty. [QS001]"
        )

    if len(query) > MAX_QUERY_LENGTH:
        raise ValidationError(
            f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters. "
            f"Reduce query size. [QS001]"
        )

    return query.strip()
