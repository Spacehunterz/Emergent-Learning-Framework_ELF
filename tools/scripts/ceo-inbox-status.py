#!/usr/bin/env python3
"""
Query and manage CEO inbox items by frontmatter status.

Usage:
    # List pending decisions
    python ceo-inbox-status.py --status pending

    # List all by priority
    python ceo-inbox-status.py --priority high

    # Mark as decided
    python ceo-inbox-status.py --decide <filename> --decision "approved"

    # Summary
    python ceo-inbox-status.py --summary
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add query module to path
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BASE_DIR / 'query'))

from frontmatter import (
    read_file_with_frontmatter,
    update_file_frontmatter,
    find_files_by_frontmatter
)

CEO_INBOX_PATH = BASE_DIR / 'ceo-inbox'


def get_all_decisions() -> List[Dict[str, Any]]:
    """Get all CEO inbox items with their frontmatter."""
    decisions = []

    if not CEO_INBOX_PATH.exists():
        return decisions

    for path in CEO_INBOX_PATH.glob('*.md'):
        if path.name == 'TEMPLATE.md':
            continue

        frontmatter, content = read_file_with_frontmatter(path)

        # Extract title from content
        title = path.stem
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break

        decisions.append({
            'path': path,
            'filename': path.name,
            'title': title,
            'frontmatter': frontmatter,
            'status': frontmatter.get('status', 'unknown'),
            'priority': frontmatter.get('priority', 'medium'),
            'created': frontmatter.get('created'),
            'domain': frontmatter.get('domain'),
        })

    return decisions


def filter_decisions(decisions: List[Dict], **criteria) -> List[Dict]:
    """Filter decisions by criteria."""
    filtered = decisions

    for key, value in criteria.items():
        if value is not None:
            filtered = [d for d in filtered if d.get(key) == value]

    return filtered


def format_decision(decision: Dict, verbose: bool = False) -> str:
    """Format a decision for display."""
    # Use ASCII-safe markers for Windows compatibility
    priority_marker = {
        'critical': '[!!!]',
        'high': '[!!]',
        'medium': '[!]',
        'low': '[-]',
    }.get(decision['priority'], '[?]')

    status_marker = {
        'pending': '[PENDING]',
        'decided': '[DECIDED]',
        'deferred': '[DEFERRED]',
    }.get(decision['status'], '[?]')

    line = f"{status_marker} {priority_marker} {decision['title']}"

    if verbose:
        line += f"\n   File: {decision['filename']}"
        if decision['created']:
            line += f"\n   Created: {decision['created']}"
        if decision['domain']:
            line += f"\n   Domain: {decision['domain']}"

    return line


def print_summary(decisions: List[Dict]) -> None:
    """Print summary of CEO inbox status."""
    total = len(decisions)
    pending = len([d for d in decisions if d['status'] == 'pending'])
    decided = len([d for d in decisions if d['status'] == 'decided'])
    deferred = len([d for d in decisions if d['status'] == 'deferred'])

    critical = len([d for d in decisions if d['priority'] == 'critical' and d['status'] == 'pending'])
    high = len([d for d in decisions if d['priority'] == 'high' and d['status'] == 'pending'])

    print("=== CEO Inbox Summary ===\n")
    print(f"Total items:  {total}")
    print(f"  Pending:    {pending}")
    print(f"  Decided:    {decided}")
    print(f"  Deferred:   {deferred}")
    print()

    if critical > 0:
        print(f"[!!!] CRITICAL pending: {critical}")
    if high > 0:
        print(f"[!!] HIGH pending: {high}")


def mark_decided(filename: str, decision: str) -> bool:
    """Mark a decision as decided."""
    path = CEO_INBOX_PATH / filename

    if not path.exists():
        # Try with .md extension
        path = CEO_INBOX_PATH / f"{filename}.md"

    if not path.exists():
        print(f"ERROR: File not found: {filename}", file=sys.stderr)
        return False

    success = update_file_frontmatter(path, {
        'status': 'decided',
        'decided': datetime.now().strftime('%Y-%m-%d'),
        'decision': decision,
    })

    if success:
        print(f"[OK] Marked as decided: {path.name}")
        return True
    else:
        print(f"ERROR: Failed to update: {path.name}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Query and manage CEO inbox items',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--status', choices=['pending', 'decided', 'deferred'],
                       help='Filter by status')
    parser.add_argument('--priority', choices=['critical', 'high', 'medium', 'low'],
                       help='Filter by priority')
    parser.add_argument('--domain', type=str, help='Filter by domain')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--decide', type=str, metavar='FILE',
                       help='Mark a file as decided')
    parser.add_argument('--decision', type=str,
                       help='Decision text (use with --decide)')

    args = parser.parse_args()

    # Handle decide action
    if args.decide:
        if not args.decision:
            print("ERROR: --decision required with --decide", file=sys.stderr)
            return 1
        return 0 if mark_decided(args.decide, args.decision) else 1

    # Get all decisions
    decisions = get_all_decisions()

    if not decisions:
        print("No CEO inbox items found.")
        return 0

    # Summary mode
    if args.summary:
        print_summary(decisions)
        return 0

    # Filter
    if args.status:
        decisions = filter_decisions(decisions, status=args.status)
    if args.priority:
        decisions = filter_decisions(decisions, priority=args.priority)
    if args.domain:
        decisions = filter_decisions(decisions, domain=args.domain)

    # Sort by priority then date
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    decisions.sort(key=lambda d: (priority_order.get(d['priority'], 4), d.get('created', '')))

    # Display
    if not decisions:
        print("No matching items found.")
        return 0

    status_label = args.status or 'all'
    print(f"=== CEO Inbox ({status_label}) ===\n")

    for decision in decisions:
        print(format_decision(decision, args.verbose))
        if args.verbose:
            print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
