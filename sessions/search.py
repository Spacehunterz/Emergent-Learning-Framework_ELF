#!/usr/bin/env python3
"""
Emergent Learning Framework - Session Log Search

Natural language search system for session logs.

Usage:
    python search.py "what did we try for auth"
    python search.py "auth bug we fixed"
    python search.py "what failed yesterday" --days 1
    python search.py "database migrations" --limit 5

Each session log entry is JSON:
    {"ts": ISO timestamp, "type": "tool_use", "tool": tool_name,
     "input_summary": text, "output_summary": text, "outcome": "success"|"failure"|"unknown"}
"""

import argparse
import json
import os
import re
import sys
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Common stop words to filter out from queries
# Note: Keep outcome-related words (failure, success, error, failed) for search accuracy
STOP_WORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
    'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
    'from', 'up', 'about', 'into', 'over', 'after', 'beneath', 'under',
    'above', 'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
    'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
    'just', 'also', 'now', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'each', 'every', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'any', 'what', 'which', 'who', 'whom',
    'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
    'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
    'his', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours',
    'theirs', 'try', 'tried', 'yesterday', 'today'
}

# Keywords that map to specific outcome searches
OUTCOME_KEYWORDS = {
    'failed': 'failure',
    'failing': 'failure',
    'broke': 'failure',
    'broken': 'failure',
    'crashed': 'failure',
    'succeeded': 'success',
    'worked': 'success',
    'passed': 'success',
}


def extract_keywords(query: str) -> List[str]:
    """
    Extract meaningful keywords from a natural language query.

    Args:
        query: Natural language query string

    Returns:
        List of extracted keywords (lowercase, filtered)
    """
    # Normalize: lowercase and split on non-word characters
    words = re.split(r'\W+', query.lower())

    # Filter: remove stop words and short words
    keywords = []
    for word in words:
        if not word or len(word) < 3:
            continue

        # Map outcome-related words to their canonical form
        if word in OUTCOME_KEYWORDS:
            keywords.append(OUTCOME_KEYWORDS[word])
        elif word not in STOP_WORDS:
            keywords.append(word)

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords


def parse_timestamp(ts: str) -> Optional[datetime]:
    """
    Parse ISO timestamp string to datetime.

    Args:
        ts: ISO format timestamp string

    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Handle various ISO formats
        ts = ts.replace('Z', '+00:00')
        if '.' in ts and '+' in ts:
            # Handle microseconds with timezone
            ts = ts.split('+')[0].split('.')[0]
        elif '.' in ts:
            ts = ts.split('.')[0]
        elif '+' in ts:
            ts = ts.split('+')[0]

        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        try:
            # Fallback: try common formats
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
    return None


def calculate_relevance(entry: Dict[str, Any], keywords: List[str],
                        now: datetime) -> Tuple[float, List[str]]:
    """
    Calculate relevance score for an entry based on keyword matches and recency.

    Args:
        entry: Session log entry dict
        keywords: List of search keywords
        now: Current datetime for recency calculation

    Returns:
        Tuple of (score, matched_keywords)
    """
    score = 0.0
    matched = []

    # Build searchable text from entry
    searchable_parts = [
        entry.get('tool', ''),
        entry.get('input_summary', ''),
        entry.get('output_summary', ''),
        entry.get('type', ''),
        entry.get('outcome', '')
    ]
    searchable_text = ' '.join(str(p) for p in searchable_parts).lower()

    # Keyword matching (main factor)
    for keyword in keywords:
        if keyword in searchable_text:
            score += 1.0
            matched.append(keyword)

            # Bonus for tool name match
            if keyword in entry.get('tool', '').lower():
                score += 0.5
            # Bonus for outcome match
            if keyword in entry.get('outcome', '').lower():
                score += 0.3

    # Recency boost (half-life: 3 days)
    ts = parse_timestamp(entry.get('ts', ''))
    if ts:
        age_days = (now - ts).total_seconds() / 86400
        recency_factor = 0.5 ** (age_days / 3)  # Half-life of 3 days
        score *= (0.3 + 0.7 * recency_factor)  # Range: 0.3x to 1.0x

    return score, matched


def get_log_files(logs_dir: Path, days: int) -> List[Path]:
    """
    Get log files within the specified day range.

    Args:
        logs_dir: Path to logs directory
        days: Number of days to look back

    Returns:
        List of log file paths, sorted by modification time (newest first)
    """
    if not logs_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    files = []

    for f in logs_dir.glob('*.jsonl'):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                files.append((mtime, f))
        except (OSError, ValueError):
            # Include file if we can't determine its age
            files.append((datetime.now(), f))

    # Sort by modification time, newest first
    files.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in files]


def search_logs(query: str, days: int = 7, limit: int = 10,
                base_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Search session logs for entries matching the query.

    Args:
        query: Natural language search query
        days: Number of days to search back
        limit: Maximum number of results
        base_path: Base path to emergent-learning directory

    Returns:
        List of matching entries with relevance scores
    """
    if base_path is None:
        base_path = Path.home() / ".claude" / "emergent-learning"

    logs_dir = base_path / "sessions" / "logs"

    # Extract keywords
    keywords = extract_keywords(query)
    if not keywords:
        return []

    # Get relevant log files
    log_files = get_log_files(logs_dir, days)
    if not log_files:
        return []

    now = datetime.now()
    results = []

    # Search through log files
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        score, matched = calculate_relevance(entry, keywords, now)

                        if score > 0:
                            results.append({
                                'entry': entry,
                                'score': score,
                                'matched_keywords': matched,
                                'source_file': str(log_file.name),
                                'line_num': line_num
                            })
                    except json.JSONDecodeError:
                        continue

        except (OSError, IOError) as e:
            # Skip files we can't read
            continue

    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)

    # Return top results
    return results[:limit]


def format_timestamp(ts: str) -> str:
    """Format timestamp for display."""
    dt = parse_timestamp(ts)
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M')
    return ts[:16] if len(ts) >= 16 else ts


def truncate_text(text: str, max_len: int = 80) -> str:
    """Truncate text to maximum length."""
    if not text:
        return ""
    text = text.replace('\n', ' ').strip()
    if len(text) > max_len:
        return text[:max_len-3] + '...'
    return text


def format_results(results: List[Dict], query: str, days: int,
                   max_chars: int = 2000) -> str:
    """
    Format search results for display.

    Args:
        results: List of search results
        query: Original query string
        days: Number of days searched
        max_chars: Maximum total characters in output

    Returns:
        Formatted string for display
    """
    lines = []

    # Header
    lines.append(f"\n{'='*3} SESSION SEARCH: \"{query}\" {'='*3}\n")

    if not results:
        lines.append("No matching entries found.\n")
        lines.append(f"{'='*40}\n")
        return '\n'.join(lines)

    current_chars = sum(len(line) for line in lines)

    for result in results:
        entry = result['entry']

        # Format entry
        ts = format_timestamp(entry.get('ts', 'Unknown'))
        tool = entry.get('tool', 'Unknown')
        entry_type = entry.get('type', 'unknown')
        outcome = entry.get('outcome', 'unknown')

        # Build entry text
        entry_lines = []
        entry_lines.append(f"[{ts}] {entry_type}: {tool}")

        input_summary = entry.get('input_summary', '')
        if input_summary:
            entry_lines.append(f"  Input: {truncate_text(input_summary, 60)}")

        output_summary = entry.get('output_summary', '')
        if output_summary:
            entry_lines.append(f"  Output: {truncate_text(output_summary, 50)}")

        entry_lines.append(f"  Outcome: {outcome}")
        entry_lines.append("")  # Blank line

        entry_text = '\n'.join(entry_lines)

        # Check if adding this entry would exceed max chars
        if current_chars + len(entry_text) > max_chars:
            lines.append("... (truncated for token efficiency)")
            break

        lines.append(entry_text)
        current_chars += len(entry_text)

    # Footer
    lines.append(f"Found {len(results)} match{'es' if len(results) != 1 else ''} in last {days} days")
    lines.append(f"{'='*40}\n")

    return '\n'.join(lines)


def main():
    """CLI entry point for session log search."""
    parser = argparse.ArgumentParser(
        description="Natural language search for session logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python search.py "auth bug we fixed"
    python search.py "what failed yesterday" --days 1
    python search.py "database migrations" --limit 5
    python search.py "grep searches" --json
        """
    )

    parser.add_argument('query', type=str, help='Natural language search query')
    parser.add_argument('--days', type=int, default=7,
                        help='Number of days to search back (default: 7)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Maximum number of results (default: 10)')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    parser.add_argument('--base-path', type=str,
                        help='Base path to emergent-learning directory')
    parser.add_argument('--debug', action='store_true',
                        help='Show debug information')

    args = parser.parse_args()

    # Parse base path if provided
    base_path = Path(args.base_path) if args.base_path else None

    # Extract keywords for debug
    if args.debug:
        keywords = extract_keywords(args.query)
        print(f"[DEBUG] Keywords: {keywords}", file=sys.stderr)

    # Search
    results = search_logs(
        query=args.query,
        days=args.days,
        limit=args.limit,
        base_path=base_path
    )

    if args.debug:
        print(f"[DEBUG] Found {len(results)} results", file=sys.stderr)

    # Output
    if args.json:
        # JSON output mode
        output = []
        for r in results:
            output.append({
                'timestamp': r['entry'].get('ts'),
                'type': r['entry'].get('type'),
                'tool': r['entry'].get('tool'),
                'input_summary': r['entry'].get('input_summary'),
                'output_summary': r['entry'].get('output_summary'),
                'outcome': r['entry'].get('outcome'),
                'relevance_score': round(r['score'], 3),
                'matched_keywords': r['matched_keywords']
            })
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(format_results(results, args.query, args.days))

    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
