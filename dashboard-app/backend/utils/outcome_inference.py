"""
Outcome inference module for the Emergent Learning Framework.

This module provides functions to infer workflow outcomes (success/failure)
from text content, enabling re-analysis of workflow runs that were
initially marked as "unknown".
"""

import json
import re
from typing import Tuple


def infer_outcome_from_content(content: str) -> Tuple[str, str]:
    """
    Infer outcome (success/failure) from text content.

    Args:
        content: Text content to analyze

    Returns:
        Tuple of (outcome, reason) where outcome is 'success', 'failure', or 'unknown'
    """
    if not content or not content.strip():
        return "unknown", "No content to analyze"

    failure_patterns = [
        (r'(?i)\berror\b[:\s]', "Error detected"),
        (r'(?i)\bexception\b[:\s]', "Exception raised"),
        (r'(?i)\bfailed\b[:\s]', "Operation failed"),
        (r'(?i)\bcould not\b', "Could not complete"),
        (r'(?i)\bunable to\b', "Unable to complete"),
        (r'\[BLOCKER\]', "Blocker encountered"),
        (r'(?i)\btraceback\b', "Exception traceback"),
        (r'(?i)\bpermission denied\b', "Permission denied"),
        (r'(?i)\btimed?\s+out\b', "Timeout occurred"),
    ]

    false_positive_patterns = [
        r'(?i)was not found to be',
        r'(?i)\berror handling\b',
        r'(?i)\bno errors?\b',
        r'(?i)\bwithout errors?\b',
        r'(?i)\b(fixed|resolved|corrected)\b.*\b(error|failure)',
        r'(?i)\b(error|failure)\b.*(fixed|resolved|corrected)',
    ]

    for pattern, reason in failure_patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            ctx_start = max(0, match.start() - 30)
            ctx_end = min(len(content), match.end() + 30)
            ctx = content[ctx_start:ctx_end]
            is_false_positive = any(re.search(fp, ctx) for fp in false_positive_patterns)
            if not is_false_positive:
                return "failure", reason

    success_patterns = [
        (r'\bsuccessfully\s+\w+', "Successfully completed action"),
        (r'\btask\s+complete', "Task completed"),
        (r'\ball tests pass', "Tests passed"),
        (r'\[success\]', "Success marker found"),
        (r'\bcompleted\s+successfully', "Completed successfully"),
        (r'\b(created|generated|built|made)\b\s+\w+', "Created something"),
        (r'\b(fixed|resolved|corrected)\b\s+\w+', "Fixed something"),
        (r'\b(updated|modified|changed)\b\s+\w+', "Updated something"),
        (r'\b(implemented|added)\b\s+\w+', "Implemented something"),
        (r'\b(analyzed|examined|reviewed)\b\s+\w+', "Analyzed something"),
    ]

    content_lower = content.lower()
    for pattern, reason in success_patterns:
        if re.search(pattern, content_lower):
            return "success", reason

    if len(content) > 50:
        return "success", "Substantial output without errors"

    return "unknown", "Could not determine outcome"


def extract_content_from_result(result_json: str) -> str:
    """
    Extract analyzable content from a result_json field.

    Args:
        result_json: JSON string or dict containing result data

    Returns:
        Extracted text content
    """
    if not result_json:
        return ""

    try:
        rj = json.loads(result_json) if isinstance(result_json, str) else result_json
        if isinstance(rj, dict):
            parts = []
            for key in ['result', 'output', 'message', 'content', 'text']:
                if key in rj and rj[key]:
                    parts.append(str(rj[key]))
            return "\n".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass

    return ""
