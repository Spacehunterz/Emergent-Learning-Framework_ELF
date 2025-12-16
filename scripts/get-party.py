#!/usr/bin/env python3
"""
Get party (agent team) definitions for multi-agent tasks.

A "party" is a pre-configured team of agents optimized for specific task types.
This script retrieves party definitions and can suggest parties based on task description.

Usage:
    # List all parties
    python get-party.py --list

    # Get specific party
    python get-party.py --party code-review

    # Suggest party based on task
    python get-party.py --suggest "review this PR for security issues"

    # Output as JSON
    python get-party.py --party new-feature --format json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Try to import yaml, fall back to basic parsing
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
AGENTS_DIR = BASE_DIR / "agents"
PARTIES_PATH = AGENTS_DIR / "parties.yaml"


def load_parties() -> Dict[str, Any]:
    """Load party definitions from YAML file (with custom merge)."""
    # Try to use config_loader for merged parties
    try:
        sys.path.insert(0, str(BASE_DIR / 'query'))
        from config_loader import load_all_parties
        return load_all_parties()
    except ImportError:
        pass

    # Fallback to direct loading
    if not PARTIES_PATH.exists():
        print(f"ERROR: Parties file not found: {PARTIES_PATH}", file=sys.stderr)
        return {}

    content = PARTIES_PATH.read_text(encoding='utf-8')

    if YAML_AVAILABLE:
        data = yaml.safe_load(content)
        return data.get('parties', {})
    else:
        # Basic fallback parser for simple cases
        print("WARNING: PyYAML not installed. Using basic parser.", file=sys.stderr)
        return _basic_yaml_parse(content)


def _basic_yaml_parse(content: str) -> Dict[str, Any]:
    """Very basic YAML-like parser for party definitions."""
    parties = {}
    current_party = None
    current_field = None

    for line in content.split('\n'):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Top level party name (no indent, ends with :)
        if not line.startswith(' ') and stripped.endswith(':') and stripped != 'parties:' and stripped != 'custom:':
            current_party = stripped[:-1]
            parties[current_party] = {'agents': [], 'triggers': []}
            current_field = None

        # Field within a party
        elif current_party and ':' in stripped and not stripped.startswith('-'):
            key, value = stripped.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"\'')

            if value:
                parties[current_party][key] = value
            current_field = key

        # List item
        elif current_party and stripped.startswith('-'):
            value = stripped[1:].strip().strip('"\'')
            # Remove inline comments
            if '#' in value:
                value = value.split('#')[0].strip()

            if current_field in parties[current_party]:
                if isinstance(parties[current_party][current_field], list):
                    parties[current_party][current_field].append(value)
            elif current_field == 'agents':
                parties[current_party]['agents'].append(value)
            elif current_field == 'triggers':
                parties[current_party]['triggers'].append(value)

    return parties


def get_party(name: str, parties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get a specific party by name."""
    return parties.get(name)


def suggest_party(task: str, parties: Dict[str, Any]) -> List[tuple]:
    """
    Suggest parties based on task description.

    Returns list of (party_name, score, reason) tuples sorted by score.
    """
    task_lower = task.lower()
    suggestions = []

    for name, party in parties.items():
        score = 0
        reasons = []

        # Check triggers
        triggers = party.get('triggers', [])
        for trigger in triggers:
            if trigger.lower() in task_lower:
                score += 10
                reasons.append(f"matches trigger '{trigger}'")

        # Check description keywords
        description = party.get('description', '').lower()
        desc_words = set(description.split())
        task_words = set(task_lower.split())
        overlap = desc_words & task_words
        if overlap:
            score += len(overlap) * 2
            reasons.append(f"keyword overlap: {', '.join(list(overlap)[:3])}")

        # Check party name in task
        if name.replace('-', ' ') in task_lower or name.replace('-', '') in task_lower:
            score += 5
            reasons.append(f"party name in task")

        if score > 0:
            suggestions.append((name, score, '; '.join(reasons)))

    return sorted(suggestions, key=lambda x: x[1], reverse=True)


def format_party(name: str, party: Dict[str, Any], format_type: str = 'text') -> str:
    """Format party information for output."""
    if format_type == 'json':
        return json.dumps({name: party}, indent=2)

    # Text format
    lines = [
        f"=== Party: {name} ===",
        f"",
        f"Description: {party.get('description', 'N/A')}",
        f"Lead Agent:  {party.get('lead', 'N/A')}",
        f"Workflow:    {party.get('workflow', 'sequential')}",
        f"",
        f"Agents:",
    ]

    for agent in party.get('agents', []):
        lines.append(f"  - {agent}")

    triggers = party.get('triggers', [])
    if triggers:
        lines.append(f"")
        lines.append(f"Triggers:")
        for trigger in triggers:
            lines.append(f"  - \"{trigger}\"")

    return '\n'.join(lines)


def list_parties(parties: Dict[str, Any], format_type: str = 'text') -> str:
    """List all available parties."""
    if format_type == 'json':
        return json.dumps(parties, indent=2)

    lines = ["=== Available Parties ===", ""]

    for name, party in parties.items():
        lead = party.get('lead', '?')
        agents = party.get('agents', [])
        desc = party.get('description', '')[:50]
        if len(party.get('description', '')) > 50:
            desc += '...'

        lines.append(f"{name}")
        lines.append(f"  Lead: {lead} | Team: {', '.join(agents)}")
        lines.append(f"  {desc}")
        lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Get party (agent team) definitions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List all parties
    python get-party.py --list

    # Get specific party
    python get-party.py --party code-review

    # Suggest party for a task
    python get-party.py --suggest "review this PR"

    # JSON output
    python get-party.py --party new-feature --format json
"""
    )

    parser.add_argument('--list', action='store_true', help='List all parties')
    parser.add_argument('--party', type=str, help='Get specific party by name')
    parser.add_argument('--suggest', type=str, metavar='TASK',
                       help='Suggest parties for a task description')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')

    args = parser.parse_args()

    # Load parties
    parties = load_parties()
    if not parties:
        print("No parties found.", file=sys.stderr)
        return 1

    # Handle commands
    if args.list:
        print(list_parties(parties, args.format))
        return 0

    if args.party:
        party = get_party(args.party, parties)
        if party:
            print(format_party(args.party, party, args.format))
            return 0
        else:
            print(f"ERROR: Party '{args.party}' not found.", file=sys.stderr)
            print(f"Available: {', '.join(parties.keys())}", file=sys.stderr)
            return 1

    if args.suggest:
        suggestions = suggest_party(args.suggest, parties)
        if suggestions:
            if args.format == 'json':
                print(json.dumps([{'party': s[0], 'score': s[1], 'reason': s[2]} for s in suggestions], indent=2))
            else:
                print(f"=== Suggested Parties for: \"{args.suggest}\" ===\n")
                for name, score, reason in suggestions[:3]:
                    print(f"  {name} (score: {score})")
                    print(f"    {reason}")
                    print()
        else:
            print("No matching parties found. Try --list to see all options.")
        return 0

    # No command - show help
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
