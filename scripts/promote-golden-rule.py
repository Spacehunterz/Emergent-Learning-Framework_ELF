#!/usr/bin/env python3
"""
Promote a heuristic or create a new golden rule with emergent categorization.

This script:
1. Parses existing golden rules to discover categories
2. Accepts a new rule (from heuristic ID or direct input)
3. Uses emergent categorization (agent suggests, user confirms)
4. Appends to golden-rules.md with proper formatting

Usage:
    # From heuristic ID
    python promote-golden-rule.py --from-heuristic 42

    # Direct input
    python promote-golden-rule.py --rule "Never X without Y" --why "Because Z" --category git

    # Interactive mode
    python promote-golden-rule.py

When run by Claude Code, Claude acts as the categorizing agent by analyzing
the rule content and existing categories to suggest the best fit.
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
MEMORY_DIR = BASE_DIR / "memory"
DB_PATH = MEMORY_DIR / "index.db"
GOLDEN_RULES_PATH = MEMORY_DIR / "golden-rules.md"


def parse_existing_rules() -> Tuple[List[Dict], Dict[str, int], int]:
    """
    Parse existing golden rules from the markdown file.

    Returns:
        - List of rule dicts with id, title, rule, why, category
        - Dict of category -> count
        - Next rule number
    """
    if not GOLDEN_RULES_PATH.exists():
        return [], {}, 1

    content = GOLDEN_RULES_PATH.read_text(encoding='utf-8')

    rules = []
    categories = {}
    max_num = 0

    # Pattern to match rule sections
    # ## 15. Never Commit Without Asking
    rule_pattern = re.compile(
        r'## (\d+)\. (.+?)\n'
        r'> (.+?)\n\n'
        r'(?:\*\*Category:\*\* (.+?)\n)?'
        r'\*\*Why:\*\* (.+?)\n',
        re.DOTALL
    )

    for match in rule_pattern.finditer(content):
        num = int(match.group(1))
        title = match.group(2).strip()
        rule_text = match.group(3).strip()
        category = match.group(4).strip() if match.group(4) else 'uncategorized'
        why = match.group(5).strip()

        max_num = max(max_num, num)

        rules.append({
            'num': num,
            'title': title,
            'rule': rule_text,
            'category': category,
            'why': why
        })

        categories[category] = categories.get(category, 0) + 1

    return rules, categories, max_num + 1


def get_heuristic_by_id(heuristic_id: int) -> Optional[Dict]:
    """Fetch a heuristic from the database by ID."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        return None

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM heuristics WHERE id = ?",
            (heuristic_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"ERROR: Database error: {e}", file=sys.stderr)
        return None


def suggest_category(rule: str, why: str, existing_categories: Dict[str, int]) -> str:
    """
    Suggest a category based on rule content and existing categories.

    This uses keyword matching as a baseline. When run by Claude,
    Claude should override this with better analysis.
    """
    rule_lower = rule.lower() + ' ' + why.lower()

    # Keyword hints for common patterns
    keyword_hints = {
        'git': ['git', 'commit', 'push', 'pull', 'branch', 'repo', 'repository'],
        'user-interaction': ['user', 'trust', 'command', 'ask', 'confirm', 'approval'],
        'process': ['before', 'after', 'first', 'then', 'workflow', 'session', 'record', 'document'],
        'verification': ['verify', 'check', 'test', 'validate', 'confirm', 'never guess'],
        'technical': ['api', 'code', 'function', 'import', 'async', 'await', 'error'],
        'react': ['react', 'useeffect', 'usestate', 'hook', 'component', 'render'],
        'agents': ['agent', 'subagent', 'spawn', 'task tool'],
    }

    # Check existing categories first (prefer reuse)
    for category in existing_categories:
        cat_lower = category.lower().replace('-', ' ')
        if cat_lower in rule_lower:
            return category

    # Check keyword hints
    for category, keywords in keyword_hints.items():
        for keyword in keywords:
            if keyword in rule_lower:
                # If this category exists, use it; otherwise suggest it
                for existing in existing_categories:
                    if existing.lower() == category.lower():
                        return existing
                return category

    return 'general'


def format_golden_rule(
    num: int,
    title: str,
    rule: str,
    why: str,
    category: str,
    source: str = "promoted"
) -> str:
    """Format a golden rule for the markdown file."""
    today = datetime.now().strftime('%Y-%m-%d')

    return f"""---

## {num}. {title}
> {rule}

**Category:** {category}
**Why:** {why}
**Promoted:** {today} ({source})
**Validations:** 1

"""


def append_golden_rule(rule_text: str) -> bool:
    """Append a formatted rule to the golden rules file."""
    try:
        with open(GOLDEN_RULES_PATH, 'a', encoding='utf-8') as f:
            f.write(rule_text)
        return True
    except Exception as e:
        print(f"ERROR: Failed to write rule: {e}", file=sys.stderr)
        return False


def display_categories(categories: Dict[str, int]) -> None:
    """Display existing categories with counts."""
    if not categories:
        print("\nNo existing categories found. This will be the first!")
        return

    print("\n=== Existing Categories ===")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} rule(s)")
    print()


def interactive_mode() -> Optional[Dict]:
    """Collect rule data interactively."""
    print("=== Promote to Golden Rule (Interactive) ===\n")

    # Parse existing
    rules, categories, next_num = parse_existing_rules()
    display_categories(categories)

    print(f"This will be Golden Rule #{next_num}\n")

    title = input("Title (short name): ").strip()
    if not title:
        print("ERROR: Title required", file=sys.stderr)
        return None

    rule = input("Rule (the principle, imperative form): ").strip()
    if not rule:
        print("ERROR: Rule required", file=sys.stderr)
        return None

    why = input("Why (explanation): ").strip()
    if not why:
        print("ERROR: Explanation required", file=sys.stderr)
        return None

    # Suggest category
    suggested = suggest_category(rule, why, categories)
    print(f"\nSuggested category: {suggested}")

    category = input(f"Category [{suggested}]: ").strip()
    if not category:
        category = suggested

    source = input("Source [observation]: ").strip() or "observation"

    return {
        'num': next_num,
        'title': title,
        'rule': rule,
        'why': why,
        'category': category,
        'source': source
    }


def main():
    parser = argparse.ArgumentParser(
        description='Promote a heuristic to golden rule with emergent categorization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # From existing heuristic
    python promote-golden-rule.py --from-heuristic 42

    # Direct input with all fields
    python promote-golden-rule.py \\
        --title "Never Commit Without Asking" \\
        --rule "NEVER run git commit without explicit user approval" \\
        --why "Commits are permanent public record" \\
        --category git

    # Interactive mode
    python promote-golden-rule.py

    # Show existing categories
    python promote-golden-rule.py --list-categories
"""
    )

    parser.add_argument('--from-heuristic', type=int, metavar='ID',
                       help='Promote an existing heuristic by ID')
    parser.add_argument('--title', type=str, help='Short title for the rule')
    parser.add_argument('--rule', type=str, help='The rule statement (imperative)')
    parser.add_argument('--why', type=str, help='Explanation of why this rule matters')
    parser.add_argument('--category', type=str, help='Category (or let it be suggested)')
    parser.add_argument('--source', type=str, default='promoted',
                       help='Source of the rule (default: promoted)')
    parser.add_argument('--list-categories', action='store_true',
                       help='List existing categories and exit')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be added without writing')
    parser.add_argument('--auto', action='store_true',
                       help='Fully automated - no prompts, use suggested category')

    args = parser.parse_args()

    # Parse existing rules
    rules, categories, next_num = parse_existing_rules()

    # List categories mode
    if args.list_categories:
        display_categories(categories)
        print(f"Next rule number: {next_num}")
        return 0

    # Collect rule data
    data = None

    if args.from_heuristic:
        # Promote from heuristic
        heuristic = get_heuristic_by_id(args.from_heuristic)
        if not heuristic:
            print(f"ERROR: Heuristic {args.from_heuristic} not found", file=sys.stderr)
            return 1

        print(f"\n=== Promoting Heuristic #{args.from_heuristic} ===")
        print(f"Rule: {heuristic['rule']}")
        print(f"Domain: {heuristic['domain']}")
        print(f"Confidence: {heuristic['confidence']}")

        # Use domain as category hint
        suggested = args.category or suggest_category(
            heuristic['rule'],
            heuristic.get('explanation', ''),
            categories
        )

        # If domain exists and matches a category pattern, prefer it
        if heuristic['domain'] and not args.category:
            domain_lower = heuristic['domain'].lower()
            for cat in categories:
                if cat.lower() == domain_lower:
                    suggested = cat
                    break
            else:
                # Domain might be a good new category
                if heuristic['domain'] not in ['general', 'uncategorized']:
                    suggested = heuristic['domain']

        display_categories(categories)
        print(f"Suggested category: {suggested}")

        if sys.stdin.isatty() and not args.dry_run and not args.auto:
            category = input(f"Category [{suggested}]: ").strip() or suggested
            title = input(f"Title [{heuristic['rule'][:40]}...]: ").strip()
            if not title:
                # Generate title from rule
                title = heuristic['rule'][:50].rstrip('.')
        else:
            category = args.category or suggested
            title = heuristic['rule'][:50].rstrip('.')

        data = {
            'num': next_num,
            'title': title,
            'rule': heuristic['rule'],
            'why': heuristic.get('explanation', 'Promoted from validated heuristic'),
            'category': category,
            'source': f"promoted from heuristic #{args.from_heuristic}"
        }

    elif args.rule:
        # Direct input mode
        if not args.title:
            print("ERROR: --title required with --rule", file=sys.stderr)
            return 1
        if not args.why:
            print("ERROR: --why required with --rule", file=sys.stderr)
            return 1

        suggested = args.category or suggest_category(args.rule, args.why, categories)

        data = {
            'num': next_num,
            'title': args.title,
            'rule': args.rule,
            'why': args.why,
            'category': args.category or suggested,
            'source': args.source
        }

    elif sys.stdin.isatty():
        # Interactive mode
        data = interactive_mode()
        if not data:
            return 1
    else:
        parser.print_help()
        return 0

    # Format the rule
    formatted = format_golden_rule(
        num=data['num'],
        title=data['title'],
        rule=data['rule'],
        why=data['why'],
        category=data['category'],
        source=data['source']
    )

    # Show preview
    print("\n=== Preview ===")
    print(formatted)

    if args.dry_run:
        print("[DRY RUN] Would append to:", GOLDEN_RULES_PATH)
        return 0

    # Confirm (skip if --auto)
    if sys.stdin.isatty() and not args.auto:
        confirm = input("Add this golden rule? [Y/n]: ").strip().lower()
        if confirm and confirm != 'y':
            print("Cancelled.")
            return 0

    # Write
    if append_golden_rule(formatted):
        print(f"\nGolden Rule #{data['num']} added successfully!")
        print(f"Category: {data['category']}")
        print(f"File: {GOLDEN_RULES_PATH}")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
