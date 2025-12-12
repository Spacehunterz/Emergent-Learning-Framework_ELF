"""
Proposal Query Functions for the Emergent Learning Framework

Add this function to QuerySystem class in query.py to enable
pending proposal retrieval during check-ins.

Usage:
    # In query.py QuerySystem class
    from .proposal_queries import get_pending_proposals

    # Or copy the function directly into the QuerySystem class
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def get_pending_proposals(self, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get pending proposals for check-in display.

    Reads proposal markdown files from proposals/pending/ directory,
    parses their frontmatter, and returns summaries for display.

    Args:
        limit: Maximum number of proposals to return (default: 10)

    Returns:
        List of dictionaries containing proposal metadata:
        [
            {
                'filename': 'YYYY-MM-DD_type_slug.md',
                'path': '/full/path/to/file.md',
                'type': 'heuristic|failure|pattern|contradiction',
                'domain': 'domain-name',
                'title': 'Proposal Title',
                'summary': 'Brief summary...',
                'confidence': 0.7,  # for heuristics
                'severity': 3,       # for failures
                'tags': ['tag1', 'tag2'],
                'submitted_at': 'YYYY-MM-DD HH:MM:SS',
                'submitted_by': 'agent-id'
            },
            ...
        ]

    Example:
        >>> qs = QuerySystem()
        >>> proposals = qs.get_pending_proposals(limit=5)
        >>> for p in proposals:
        ...     print(f"[{p['type']}] {p['title']} (domain: {p['domain']})")
    """
    proposals = []
    pending_dir = self.base_path / "proposals" / "pending"

    self._log_debug(f"Looking for pending proposals in: {pending_dir}")

    if not pending_dir.exists():
        self._log_debug("Pending proposals directory does not exist")
        return proposals

    # Get all markdown files, sorted by modification time (newest first)
    try:
        md_files = sorted(
            pending_dir.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:limit]
    except Exception as e:
        self._log_debug(f"Error listing pending proposals: {e}")
        return proposals

    for filepath in md_files:
        try:
            proposal = _parse_proposal_file(filepath)
            if proposal:
                proposals.append(proposal)
        except Exception as e:
            self._log_debug(f"Error parsing proposal {filepath}: {e}")
            continue

    self._log_debug(f"Found {len(proposals)} pending proposals")
    return proposals


def _parse_proposal_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Parse a proposal markdown file and extract metadata.

    Args:
        filepath: Path to the proposal file

    Returns:
        Dictionary with proposal metadata, or None if parsing fails
    """
    content = filepath.read_text(encoding='utf-8')

    proposal = {
        'filename': filepath.name,
        'path': str(filepath),
        'type': 'unknown',
        'domain': 'general',
        'title': 'Untitled',
        'summary': '',
        'confidence': None,
        'severity': None,
        'tags': [],
        'submitted_at': None,
        'submitted_by': None
    }

    # Parse frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()

            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if key == 'type':
                        proposal['type'] = value.lower()
                    elif key == 'domain':
                        proposal['domain'] = value
                    elif key == 'confidence':
                        try:
                            proposal['confidence'] = float(value)
                        except ValueError:
                            pass
                    elif key == 'severity':
                        try:
                            proposal['severity'] = int(value)
                        except ValueError:
                            pass
                    elif key == 'tags':
                        proposal['tags'] = [t.strip() for t in value.split(',')]
                    elif key == 'submitted_at':
                        proposal['submitted_at'] = value
                    elif key == 'submitted_by':
                        proposal['submitted_by'] = value
        else:
            body = content
    else:
        body = content

    # Extract title (first # heading)
    for line in body.split('\n'):
        if line.startswith('# '):
            proposal['title'] = line[2:].strip()
            break

    # Extract summary section
    summary_match = re.search(
        r'^##\s+[Ss]ummary\s*\n(.*?)(?=\n##|\Z)',
        body,
        re.MULTILINE | re.DOTALL
    )
    if summary_match:
        summary = summary_match.group(1).strip()
        # Truncate to first 200 chars
        proposal['summary'] = summary[:200] + ('...' if len(summary) > 200 else '')

    return proposal


def format_proposals_for_context(proposals: List[Dict[str, Any]]) -> str:
    """
    Format proposals list for inclusion in agent context.

    Args:
        proposals: List of proposal dictionaries from get_pending_proposals()

    Returns:
        Formatted markdown string for context display
    """
    if not proposals:
        return ""

    lines = [
        "\n# Pending Proposals\n",
        f"*{len(proposals)} proposals awaiting review*\n"
    ]

    for i, p in enumerate(proposals, 1):
        type_emoji = {
            'heuristic': 'H',
            'failure': 'F',
            'pattern': 'P',
            'contradiction': '!'
        }.get(p['type'], '?')

        lines.append(f"\n## [{type_emoji}] {p['title']}")
        lines.append(f"**Type:** {p['type']} | **Domain:** {p['domain']}")

        if p['type'] == 'heuristic' and p['confidence'] is not None:
            lines.append(f"**Confidence:** {p['confidence']}")
        elif p['type'] == 'failure' and p['severity'] is not None:
            lines.append(f"**Severity:** {p['severity']}")

        if p['tags']:
            lines.append(f"**Tags:** {', '.join(p['tags'])}")

        if p['summary']:
            lines.append(f"\n{p['summary']}")

        lines.append(f"\n*File: {p['filename']}*\n")

    lines.append("\n---\n")
    lines.append("*Review proposals with: `./scripts/review-proposal.sh pending/<file> approve|reject`*\n")

    return '\n'.join(lines)


# ============================================================================
# INTEGRATION CODE FOR query.py
# ============================================================================
#
# To add pending proposals to the QuerySystem class, add these methods
# to the QuerySystem class in query.py:
#
# 1. Copy the get_pending_proposals() function above into the class
# 2. Copy _parse_proposal_file() as a module-level function
# 3. Update build_context() to include proposals:
#
#     # In build_context(), after checking CEO reviews, add:
#     proposals = self.get_pending_proposals(limit=5)
#     if proposals:
#         context_parts.append("\n# Pending Proposals\n\n")
#         for p in proposals:
#             entry = f"- **[{p['type'].upper()}] {p['title']}** (domain: {p['domain']})\n"
#             if p['summary']:
#                 entry += f"  {p['summary']}\n\n"
#             context_parts.append(entry)
#
# 4. Add CLI argument in main():
#     parser.add_argument('--pending-proposals', action='store_true',
#                        help='List pending proposals')
#
# 5. Add handler in main():
#     elif args.pending_proposals:
#         result = query_system.get_pending_proposals(args.limit)
# ============================================================================
