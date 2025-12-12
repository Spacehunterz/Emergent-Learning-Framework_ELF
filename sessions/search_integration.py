#!/usr/bin/env python3
"""
Emergent Learning Framework - Session Search Integration

Provides a function interface for integrating session log search
into the main query system (query.py).

Usage:
    from search_integration import search_sessions

    result = search_sessions("auth bug", days=7, limit=10)
    print(result)  # Formatted string ready for check-in output
"""

import sys
import io
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# Lazy-loaded module references
_search_module = None


def _get_search_module():
    """
    Lazily load the search module to avoid import-time issues.
    Returns the search module with all needed functions.
    """
    global _search_module
    if _search_module is not None:
        return _search_module

    # Try relative import first (when used as package)
    try:
        from . import search as _search_module
        return _search_module
    except ImportError:
        pass

    # Try direct import (when running from sessions directory)
    try:
        import search as _search_module
        return _search_module
    except ImportError:
        pass

    # Fallback: dynamic import from file path
    import importlib.util
    search_path = Path(__file__).parent / "search.py"
    if not search_path.exists():
        raise ImportError(f"Cannot find search.py at {search_path}")

    spec = importlib.util.spec_from_file_location("search", search_path)
    _search_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_search_module)
    return _search_module


def search_sessions(query: str, days: int = 7, limit: int = 10,
                    max_chars: int = 2000,
                    base_path: Optional[Path] = None) -> str:
    """
    Search session logs and return formatted string for check-in output.

    This function is designed to be called from query.py to include
    relevant session history in the building context.

    Args:
        query: Natural language search query
        days: Number of days to search back (default: 7)
        limit: Maximum number of results to return (default: 10)
        max_chars: Maximum total characters in output for token efficiency (default: 2000)
        base_path: Base path to emergent-learning directory (default: ~/.claude/emergent-learning)

    Returns:
        Formatted string ready to include in check-in output.
        Returns empty string if no matches or if logs directory doesn't exist.

    Example:
        >>> result = search_sessions("auth bug we fixed", days=7, limit=5)
        >>> print(result)

        === SESSION HISTORY: "auth bug we fixed" ===

        [2024-12-11 14:32] tool_use: Edit
          Input: Fixed auth token refresh...
          Outcome: success

        Found 1 match in last 7 days
        ========================================
    """
    if base_path is None:
        base_path = Path.home() / ".claude" / "emergent-learning"

    # Check if logs directory exists
    logs_dir = base_path / "sessions" / "logs"
    if not logs_dir.exists():
        return ""

    # Get search module
    try:
        search_mod = _get_search_module()
    except ImportError:
        return ""

    # Extract keywords to validate query has meaningful terms
    keywords = search_mod.extract_keywords(query)
    if not keywords:
        return ""

    # Search logs
    try:
        results = search_mod.search_logs(
            query=query,
            days=days,
            limit=limit,
            base_path=base_path
        )
    except Exception:
        # Silent fail - session search is supplementary
        return ""

    if not results:
        return ""

    # Format output for check-in context
    lines = []
    lines.append(f"\n### Session History: \"{query}\"\n")

    current_chars = sum(len(line) for line in lines)

    for result in results:
        entry = result['entry']

        # Format entry
        ts = search_mod.format_timestamp(entry.get('ts', 'Unknown'))
        tool = entry.get('tool', 'Unknown')
        outcome = entry.get('outcome', 'unknown')

        # Build compact entry text
        entry_lines = []
        entry_lines.append(f"- **[{ts}] {tool}** ({outcome})")

        input_summary = entry.get('input_summary', '')
        if input_summary:
            entry_lines.append(f"  {search_mod.truncate_text(input_summary, 70)}")

        entry_text = '\n'.join(entry_lines) + '\n'

        # Check if adding this entry would exceed max chars
        if current_chars + len(entry_text) > max_chars:
            remaining = len(results) - len([l for l in lines if l.startswith('-')])
            if remaining > 0:
                lines.append(f"\n*...{remaining} more matches truncated*\n")
            break

        lines.append(entry_text)
        current_chars += len(entry_text)

    # Footer
    match_count = len(results)
    lines.append(f"\n*{match_count} match{'es' if match_count != 1 else ''} in last {days} days*\n")

    return '\n'.join(lines)


def get_recent_failures(days: int = 3, limit: int = 5,
                        base_path: Optional[Path] = None) -> str:
    """
    Get recent failures from session logs.

    Convenience function to search specifically for failures.

    Args:
        days: Number of days to search back (default: 3)
        limit: Maximum number of results (default: 5)
        base_path: Base path to emergent-learning directory

    Returns:
        Formatted string of recent failures, or empty string if none found.
    """
    return search_sessions(
        query="failure failed error",
        days=days,
        limit=limit,
        base_path=base_path
    )


def get_recent_tool_usage(tool_name: str, days: int = 7, limit: int = 10,
                          base_path: Optional[Path] = None) -> str:
    """
    Get recent usage of a specific tool.

    Args:
        tool_name: Name of the tool to search for (e.g., "Edit", "Grep")
        days: Number of days to search back (default: 7)
        limit: Maximum number of results (default: 10)
        base_path: Base path to emergent-learning directory

    Returns:
        Formatted string of tool usage, or empty string if none found.
    """
    return search_sessions(
        query=tool_name,
        days=days,
        limit=limit,
        base_path=base_path
    )


# Module self-test
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Test session search integration")
    parser.add_argument('query', nargs='?', default='test query',
                        help='Search query to test')
    parser.add_argument('--days', type=int, default=7, help='Days to search')
    parser.add_argument('--limit', type=int, default=5, help='Max results')

    args = parser.parse_args()

    print("Testing search_sessions()...")
    result = search_sessions(args.query, days=args.days, limit=args.limit)

    if result:
        print(result)
    else:
        print("No results found (this is normal if no session logs exist yet)")
        print("\nSession logs should be at: ~/.claude/emergent-learning/sessions/logs/*.jsonl")

    print("\nIntegration test complete.")
