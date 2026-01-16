#!/usr/bin/env python3
"""
ELF Observation & Distillation CLI.

Usage:
    python -m src.observe observe --session /path/to/log
    python -m src.observe distill --run --auto-append
    python -m src.observe distill --dry-run

Commands:
    observe     Extract patterns from session logs
    distill     Promote patterns to heuristics

Examples:
    # Extract patterns from today's session
    python -m src.observe observe --session ~/.claude/emergent-learning/sessions/logs/2024-01-15_session.jsonl

    # Run distillation with auto-append to golden rules
    python -m src.observe distill --run --auto-append

    # Preview what distillation would do
    python -m src.observe distill --dry-run --verbose
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def cmd_observe(args):
    """Handle the observe command."""
    from src.query.models import initialize_database
    from src.observe.elf_observe import extract_patterns_from_session

    await initialize_database()

    if args.session == 'today':
        # Find today's session log
        logs_dir = Path.home() / ".claude" / "emergent-learning" / "sessions" / "logs"
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = logs_dir / f"{today}_session.jsonl"
        if not session_file.exists():
            print(f"No session log found for today: {session_file}")
            return 1
        session_path = str(session_file)
    else:
        session_path = args.session

    patterns = await extract_patterns_from_session(
        session_path,
        project_path=args.project,
        save_to_db=not args.dry_run
    )

    print(f"Extracted {len(patterns)} patterns from {Path(session_path).name}")

    if args.verbose:
        for p in patterns:
            print(f"  [{p['pattern_type']:15}] {p['pattern_text'][:60]}")

    if args.dry_run:
        print("(dry run - patterns not saved)")

    return 0


async def cmd_distill(args):
    """Handle the distill command."""
    from src.query.models import initialize_database
    from src.observe.elf_distill import run_distillation, apply_decay_only

    await initialize_database()

    if args.decay_only:
        decayed = await apply_decay_only(args.project)
        print(f"Applied decay to {decayed} patterns")
        return 0

    result = await run_distillation(
        project_path=args.project,
        auto_append=args.auto_append,
        dry_run=args.dry_run,
    )

    mode = "(dry run)" if args.dry_run else "complete"
    print(f"Distillation {mode}:")
    print(f"  Patterns decayed: {result['patterns_decayed']}")
    print(f"  Candidates found: {result['candidates_found']}")
    print(f"  Patterns promoted: {result['patterns_promoted']}")

    if args.auto_append:
        print(f"  Golden rules appended: {result.get('golden_rules_appended', 0)}")

    if args.verbose:
        if result.get('heuristics_created'):
            print("\nPromoted patterns:")
            for h in result['heuristics_created']:
                print(f"  - {h['pattern_text']}")
        if result.get('would_promote'):
            print("\nWould promote:")
            for p in result['would_promote']:
                print(f"  - [{p['strength']:.2f}] {p['pattern_text']}")

    return 0


async def cmd_status(args):
    """Show current pattern status."""
    from src.query.models import initialize_database, Pattern, get_manager

    await initialize_database()

    m = get_manager()
    async with m:
        async with m.connection():
            # Count patterns by type
            patterns = []
            async for p in Pattern.select():
                patterns.append(p)

            total = len(patterns)
            by_type = {}
            promoted = 0
            high_strength = 0

            for p in patterns:
                by_type[p.pattern_type] = by_type.get(p.pattern_type, 0) + 1
                if p.promoted_to_heuristic_id:
                    promoted += 1
                if p.strength >= 0.7:
                    high_strength += 1

    print("Pattern Status:")
    print(f"  Total patterns: {total}")
    print(f"  Promoted: {promoted}")
    print(f"  High strength (>=0.7): {high_strength}")
    print("\n  By type:")
    for ptype, count in sorted(by_type.items()):
        print(f"    {ptype}: {count}")

    if args.verbose and patterns:
        print("\n  Top 5 by strength:")
        top = sorted(patterns, key=lambda p: p.strength, reverse=True)[:5]
        for p in top:
            status = " [promoted]" if p.promoted_to_heuristic_id else ""
            print(f"    [{p.strength:.2f}] {p.pattern_text[:50]}{status}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='ELF Observation & Distillation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # observe command
    observe_parser = subparsers.add_parser('observe', help='Extract patterns from session logs')
    observe_parser.add_argument('--session', type=str, required=True,
                                help='Path to session log file (or "today" for current day)')
    observe_parser.add_argument('--project', type=str, help='Project path for location-specific patterns')
    observe_parser.add_argument('--dry-run', action='store_true', help='Extract without saving to DB')
    observe_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    # distill command
    distill_parser = subparsers.add_parser('distill', help='Promote patterns to heuristics')
    distill_parser.add_argument('--run', action='store_true', help='Run full distillation')
    distill_parser.add_argument('--decay-only', action='store_true', help='Only apply decay')
    distill_parser.add_argument('--auto-append', action='store_true', help='Auto-append to golden rules')
    distill_parser.add_argument('--project', type=str, help='Project path filter')
    distill_parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    distill_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    # status command
    status_parser = subparsers.add_parser('status', help='Show pattern status')
    status_parser.add_argument('--verbose', '-v', action='store_true', help='Show top patterns')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run the appropriate command
    if args.command == 'observe':
        return asyncio.run(cmd_observe(args))
    elif args.command == 'distill':
        if not args.run and not args.decay_only and not args.dry_run:
            print("Error: specify --run, --decay-only, or --dry-run")
            return 1
        return asyncio.run(cmd_distill(args))
    elif args.command == 'status':
        return asyncio.run(cmd_status(args))
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
