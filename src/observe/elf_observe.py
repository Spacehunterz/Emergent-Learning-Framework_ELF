"""
ELF Pattern Observation - Extract patterns from session logs.

This module extracts actionable patterns from Claude session logs:
- Retry patterns: When the same tool is called again after failure
- Error patterns: Recurring error signatures
- Search patterns: Grep/Glob followed by Read sequences
- Success sequences: Tool chains that lead to commits
- Tool sequences: Common tool ordering patterns

Usage:
    from src.observe.elf_observe import extract_patterns_from_session
    patterns = await extract_patterns_from_session('/path/to/session.log')
"""

import json
import hashlib
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.query.models import (
        Pattern, Heuristic, manager, initialize_database, get_manager
    )
except ImportError:
    # Fallback for direct execution
    Pattern = None
    Heuristic = None
    manager = None


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Error signature patterns (regex -> normalized label)
ERROR_PATTERNS = [
    (r'(?i)permission denied', 'permission_denied'),
    (r'(?i)module.?not.?found|cannot.?find.?module', 'module_not_found'),
    (r'(?i)timeout|timed?.?out', 'timeout'),
    (r'(?i)connection.?refused', 'connection_refused'),
    (r'(?i)syntax.?error', 'syntax_error'),
    (r'(?i)type.?error', 'type_error'),
    (r'(?i)not.?found|404', 'not_found'),
    (r'(?i)ENOENT', 'file_not_found'),
    (r'(?i)EACCES', 'access_denied'),
    (r'(?i)npm ERR!', 'npm_error'),
    (r'(?i)pip.*(error|failed)', 'pip_error'),
    (r'(?i)git.*(error|fatal)', 'git_error'),
    (r'(?i)docker.*(error|failed)', 'docker_error'),
]

# Tool to domain mapping
TOOL_DOMAIN_MAP = {
    'Bash': 'shell',
    'Read': 'files',
    'Write': 'files',
    'Edit': 'files',
    'Glob': 'search',
    'Grep': 'search',
    'Task': 'agents',
    'WebFetch': 'web',
    'WebSearch': 'web',
}

# Keyword to domain mapping (checked in input_summary)
KEYWORD_DOMAIN_MAP = {
    'npm': 'nodejs',
    'node': 'nodejs',
    'pip': 'python',
    'python': 'python',
    'pytest': 'python',
    'git': 'git',
    'docker': 'docker',
    'test': 'testing',
    'react': 'react',
    'api': 'api',
    'database': 'database',
    'sql': 'database',
}

# Retry detection window (seconds between failure and retry)
RETRY_WINDOW_SECONDS = 120

# Minimum entries for a pattern to be significant
MIN_PATTERN_OCCURRENCES = 2


# -----------------------------------------------------------------------------
# Pattern Extraction Classes
# -----------------------------------------------------------------------------

class PatternExtractor:
    """
    Extract patterns from session log entries.

    Analyzes tool_use entries to find:
    - Retry attempts after failures
    - Recurring error signatures
    - Search → Read sequences
    - Tool chains leading to success
    """

    def __init__(
        self,
        entries: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        project_path: Optional[str] = None
    ):
        """
        Initialize the pattern extractor.

        Args:
            entries: List of log entries (parsed from JSONL)
            session_id: Optional session identifier
            project_path: Optional project path for location-specific patterns
        """
        # Filter to tool_use entries and sort by timestamp
        self.entries = sorted(
            [e for e in entries if e.get('type') == 'tool_use'],
            key=lambda x: x.get('ts', '')
        )
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.project_path = project_path
        self.patterns: List[Dict[str, Any]] = []

    def extract_all(self) -> List[Dict[str, Any]]:
        """Extract all pattern types from the entries."""
        self.patterns = []
        self.patterns.extend(self._extract_retry_patterns())
        self.patterns.extend(self._extract_error_patterns())
        self.patterns.extend(self._extract_search_patterns())
        self.patterns.extend(self._extract_success_sequences())
        self.patterns.extend(self._extract_tool_sequences())
        return self.patterns

    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        try:
            # Handle various ISO formats
            if 'T' in ts:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return None

    def _normalize_input(self, input_summary: str) -> str:
        """Normalize input for comparison (remove paths, numbers, etc.)."""
        if not input_summary:
            return ''
        # Remove specific file paths but keep command structure
        normalized = re.sub(r'/[\w/.-]+', '/PATH', input_summary)
        # Remove line numbers
        normalized = re.sub(r':\d+', ':N', normalized)
        # Remove quotes content but keep structure
        normalized = re.sub(r'"[^"]*"', '"..."', normalized)
        return normalized[:100]  # Limit length

    def _infer_domain(self, entry: Dict[str, Any]) -> str:
        """Infer domain from tool and input content."""
        tool = entry.get('tool', '')
        tool_domain = TOOL_DOMAIN_MAP.get(tool, 'general')

        input_text = (entry.get('input_summary', '') or '').lower()
        for keyword, domain in KEYWORD_DOMAIN_MAP.items():
            if keyword in input_text:
                return domain

        return tool_domain

    def _extract_error_signature(self, output: str) -> Optional[str]:
        """Extract normalized error signature from output."""
        if not output:
            return None

        for pattern, label in ERROR_PATTERNS:
            if re.search(pattern, output):
                return label

        # Fallback: first meaningful line of error
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        if lines:
            # Return first non-empty line, truncated
            return lines[0][:80]
        return None

    def _extract_retry_patterns(self) -> List[Dict[str, Any]]:
        """Find failure → retry patterns."""
        patterns = []

        for i, entry in enumerate(self.entries):
            if entry.get('outcome') != 'failure':
                continue

            failure_ts = self._parse_timestamp(entry.get('ts', ''))
            if not failure_ts:
                continue

            failure_tool = entry.get('tool', '')
            failure_input = self._normalize_input(entry.get('input_summary', ''))

            # Look for retry within window
            for j in range(i + 1, min(i + 10, len(self.entries))):
                retry_entry = self.entries[j]
                retry_ts = self._parse_timestamp(retry_entry.get('ts', ''))

                if not retry_ts:
                    continue

                # Check if within retry window
                delta = (retry_ts - failure_ts).total_seconds()
                if delta > RETRY_WINDOW_SECONDS:
                    break

                # Check if same tool
                if retry_entry.get('tool') != failure_tool:
                    continue

                retry_input = self._normalize_input(retry_entry.get('input_summary', ''))

                # Check if similar input (same normalized form or starts similarly)
                if failure_input[:30] == retry_input[:30] or \
                   failure_tool in ('Bash',) and failure_input.split()[0:1] == retry_input.split()[0:1]:

                    # Found a retry - what changed?
                    difference = retry_entry.get('input_summary', '')[:100]

                    patterns.append({
                        'pattern_type': 'retry',
                        'pattern_text': f"When {failure_tool} fails, retry with: {difference}",
                        'signature': f"{failure_tool}:{failure_input[:50]}",
                        'domain': self._infer_domain(entry),
                        'session_ids': [self.session_id],
                        'project_path': self.project_path,
                    })
                    break  # Only capture first retry

        return patterns

    def _extract_error_patterns(self) -> List[Dict[str, Any]]:
        """Extract recurring error signatures."""
        error_counts: Dict[str, List[Dict]] = defaultdict(list)

        for entry in self.entries:
            if entry.get('outcome') != 'failure':
                continue

            output = entry.get('output_summary', '')
            sig = self._extract_error_signature(output)
            if sig:
                error_counts[sig].append(entry)

        patterns = []
        for sig, entries in error_counts.items():
            if len(entries) >= MIN_PATTERN_OCCURRENCES:
                tool = entries[0].get('tool', 'unknown')
                patterns.append({
                    'pattern_type': 'error',
                    'pattern_text': f"Common error with {tool}: {sig}",
                    'signature': f"error:{sig}:{tool}",
                    'domain': self._infer_domain(entries[0]),
                    'occurrence_count': len(entries),
                    'session_ids': [self.session_id],
                    'project_path': self.project_path,
                })

        return patterns

    def _extract_search_patterns(self) -> List[Dict[str, Any]]:
        """Extract search → read sequences."""
        patterns = []
        search_tools = {'Grep', 'Glob'}

        for i, entry in enumerate(self.entries):
            if entry.get('tool') not in search_tools:
                continue

            search_input = entry.get('input_summary', '')

            # Count subsequent Read operations
            read_count = 0
            read_files = []
            for j in range(i + 1, min(i + 20, len(self.entries))):
                next_entry = self.entries[j]
                if next_entry.get('tool') == 'Read':
                    read_count += 1
                    read_files.append(next_entry.get('input_summary', '')[:50])
                elif next_entry.get('tool') in search_tools:
                    break  # New search, stop counting

            if read_count >= 2:
                patterns.append({
                    'pattern_type': 'search',
                    'pattern_text': f"Search '{search_input[:50]}' leads to reading {read_count} files",
                    'signature': f"search:{self._normalize_input(search_input)}:{read_count}",
                    'domain': 'search',
                    'occurrence_count': read_count,
                    'session_ids': [self.session_id],
                    'project_path': self.project_path,
                })

        return patterns

    def _extract_success_sequences(self) -> List[Dict[str, Any]]:
        """Extract tool chains that lead to successful commits."""
        patterns = []

        for i, entry in enumerate(self.entries):
            # Look for git commit success
            if entry.get('tool') != 'Bash':
                continue
            input_summary = entry.get('input_summary', '')
            if 'git commit' not in input_summary.lower():
                continue
            if entry.get('outcome') != 'success':
                continue

            # Found a successful commit - what preceded it?
            preceding_tools = []
            for j in range(max(0, i - 10), i):
                prev_entry = self.entries[j]
                if prev_entry.get('outcome') == 'success':
                    preceding_tools.append(prev_entry.get('tool', 'unknown'))

            if len(preceding_tools) >= 3:
                sequence = ' → '.join(preceding_tools[-5:])
                patterns.append({
                    'pattern_type': 'success_sequence',
                    'pattern_text': f"Successful commit after: {sequence}",
                    'signature': f"success_seq:{':'.join(preceding_tools[-5:])}",
                    'domain': 'git',
                    'session_ids': [self.session_id],
                    'project_path': self.project_path,
                })

        return patterns

    def _extract_tool_sequences(self) -> List[Dict[str, Any]]:
        """Extract common tool ordering patterns."""
        # Count tool pair transitions
        transitions: Dict[str, int] = defaultdict(int)

        for i in range(len(self.entries) - 1):
            curr_tool = self.entries[i].get('tool', '')
            next_tool = self.entries[i + 1].get('tool', '')
            if curr_tool and next_tool:
                transitions[f"{curr_tool}→{next_tool}"] += 1

        patterns = []
        for transition, count in transitions.items():
            if count >= 5:  # Threshold for significance
                patterns.append({
                    'pattern_type': 'tool_sequence',
                    'pattern_text': f"Common sequence: {transition} ({count} times)",
                    'signature': f"tool_seq:{transition}",
                    'domain': 'workflow',
                    'occurrence_count': count,
                    'session_ids': [self.session_id],
                    'project_path': self.project_path,
                })

        return patterns


# -----------------------------------------------------------------------------
# Pattern Storage Functions
# -----------------------------------------------------------------------------

def hash_pattern(pattern: Dict[str, Any]) -> str:
    """Generate dedup hash for a pattern."""
    key_parts = [
        pattern.get('pattern_type', ''),
        pattern.get('signature', pattern.get('pattern_text', ''))
    ]
    return hashlib.sha256(':'.join(key_parts).encode()).hexdigest()[:16]


def calculate_initial_strength(pattern: Dict[str, Any]) -> float:
    """Calculate initial pattern strength based on extraction signals."""
    base_strength = 0.3

    # Occurrence bonus
    occurrence_count = pattern.get('occurrence_count', 1)
    occurrence_bonus = min(0.3, occurrence_count * 0.05)

    # Pattern type multipliers
    TYPE_MULTIPLIERS = {
        'retry': 1.2,           # Retry patterns are actionable
        'error': 1.0,           # Errors are common
        'success_sequence': 1.3, # Success sequences are valuable
        'search': 0.8,          # Search patterns are contextual
        'tool_sequence': 0.9,
    }
    type_mult = TYPE_MULTIPLIERS.get(pattern.get('pattern_type', ''), 1.0)

    strength = (base_strength + occurrence_bonus) * type_mult
    return min(1.0, max(0.0, strength))


async def upsert_pattern(pattern: Dict[str, Any]) -> int:
    """
    Insert or update a pattern in the database.

    If pattern exists (by hash), increment occurrence count and update last_seen.
    Otherwise, create new pattern.

    Returns: Pattern ID
    """
    if Pattern is None:
        raise ImportError("Pattern model not available - run from project root")

    pattern_hash = hash_pattern(pattern)
    now = datetime.utcnow()

    m = get_manager()
    async with m:
        async with m.connection():
            # Try to find existing pattern
            existing = None
            async for p in Pattern.select().where(Pattern.pattern_hash == pattern_hash):
                existing = p
                break

            if existing:
                # Update existing pattern
                existing.occurrence_count += pattern.get('occurrence_count', 1)
                existing.last_seen = now
                existing.strength = min(1.0, existing.strength + 0.05)

                # Merge session IDs
                session_ids = json.loads(existing.session_ids or '[]')
                new_sessions = pattern.get('session_ids', [])
                session_ids = list(set(session_ids + new_sessions))[-10:]
                existing.session_ids = json.dumps(session_ids)

                existing.updated_at = now
                await existing.save()
                return existing.id

            else:
                # Create new pattern
                new_pattern = await Pattern.create(
                    pattern_type=pattern['pattern_type'],
                    pattern_hash=pattern_hash,
                    pattern_text=pattern['pattern_text'],
                    signature=pattern.get('signature'),
                    occurrence_count=pattern.get('occurrence_count', 1),
                    first_seen=now,
                    last_seen=now,
                    session_ids=json.dumps(pattern.get('session_ids', [])),
                    project_path=pattern.get('project_path'),
                    domain=pattern.get('domain', 'general'),
                    strength=calculate_initial_strength(pattern),
                    created_at=now,
                    updated_at=now,
                )
                return new_pattern.id


# -----------------------------------------------------------------------------
# Main API Functions
# -----------------------------------------------------------------------------

def parse_session_log(log_path: Path) -> List[Dict[str, Any]]:
    """
    Parse a session log file (JSONL format).

    Args:
        log_path: Path to the session log file

    Returns:
        List of parsed log entries
    """
    entries = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # Skip malformed lines
    except FileNotFoundError:
        pass
    return entries


async def extract_patterns_from_session(
    log_path: str,
    session_id: Optional[str] = None,
    project_path: Optional[str] = None,
    save_to_db: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract patterns from a session log and optionally save to database.

    Args:
        log_path: Path to session log file (JSONL)
        session_id: Optional session identifier
        project_path: Optional project path for location-specific patterns
        save_to_db: Whether to save patterns to database (default: True)

    Returns:
        List of extracted patterns
    """
    log_file = Path(log_path)

    # Generate session ID from filename if not provided
    if not session_id:
        session_id = log_file.stem

    # Parse log entries
    entries = parse_session_log(log_file)
    if not entries:
        return []

    # Extract patterns
    extractor = PatternExtractor(entries, session_id, project_path)
    patterns = extractor.extract_all()

    # Save to database if requested
    if save_to_db and patterns:
        for pattern in patterns:
            try:
                await upsert_pattern(pattern)
            except Exception as e:
                print(f"[elf_observe] Failed to save pattern: {e}", file=sys.stderr)

    return patterns


async def extract_patterns_from_text(
    log_content: str,
    session_id: Optional[str] = None,
    project_path: Optional[str] = None,
    save_to_db: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract patterns from raw log content (for Ralph loop stdout capture).

    This handles raw Claude output that may not be in JSONL format.
    Attempts to parse as JSONL first, then falls back to text parsing.

    Args:
        log_content: Raw log content (may be JSONL or plain text)
        session_id: Optional session identifier
        project_path: Optional project path
        save_to_db: Whether to save to database

    Returns:
        List of extracted patterns
    """
    entries = []

    # Try JSONL parsing first
    for line in log_content.split('\n'):
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # Not JSON - try to extract tool calls from text
                # Look for patterns like "Tool: Bash" or "[Bash]"
                tool_match = re.search(r'\[?(?:Tool:?\s*)?(\w+)\]?\s*[:>]?\s*(.+)', line)
                if tool_match:
                    tool, summary = tool_match.groups()
                    if tool in TOOL_DOMAIN_MAP:
                        entries.append({
                            'ts': datetime.now().isoformat(),
                            'type': 'tool_use',
                            'tool': tool,
                            'input_summary': summary[:200],
                            'outcome': 'unknown'
                        })

    if not entries:
        return []

    # Extract patterns
    extractor = PatternExtractor(entries, session_id, project_path)
    patterns = extractor.extract_all()

    # Save to database if requested
    if save_to_db and patterns:
        for pattern in patterns:
            try:
                await upsert_pattern(pattern)
            except Exception as e:
                print(f"[elf_observe] Failed to save pattern: {e}", file=sys.stderr)

    return patterns


# -----------------------------------------------------------------------------
# CLI Support
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description='Extract patterns from session logs')
    parser.add_argument('--session', type=str, help='Path to session log file')
    parser.add_argument('--project', type=str, help='Project path for location-specific patterns')
    parser.add_argument('--dry-run', action='store_true', help='Extract without saving to DB')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    async def main():
        if args.session:
            # Initialize database
            from src.query.models import initialize_database
            await initialize_database()

            patterns = await extract_patterns_from_session(
                args.session,
                project_path=args.project,
                save_to_db=not args.dry_run
            )

            print(f"Extracted {len(patterns)} patterns")
            if args.verbose:
                for p in patterns:
                    print(f"  [{p['pattern_type']}] {p['pattern_text'][:60]}")
        else:
            parser.print_help()

    asyncio.run(main())
