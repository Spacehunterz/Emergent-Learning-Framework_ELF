"""
ELF Pattern Distillation - Promote patterns to heuristics and golden rules.

This module handles:
- Time-based decay of pattern strength
- Promotion of high-confidence patterns to heuristics
- Auto-append of promoted patterns to golden-rules.md
- Token budget management for golden rules section

Usage:
    from src.observe.elf_distill import run_distillation
    result = await run_distillation(auto_append=True)
"""

import json
import re
from datetime import datetime, timedelta
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
    Pattern = None
    Heuristic = None
    manager = None


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Decay settings
DECAY_HALF_LIFE_DAYS = 7.0  # Strength halves every 7 days without reinforcement

# Promotion thresholds
PROMOTION_THRESHOLDS = {
    'strength': 0.7,           # Minimum strength to consider
    'occurrence_count': 3,     # Minimum occurrences
    'age_days': 1,             # Minimum age (avoid flash-in-pan)
    'session_diversity': 2,    # Patterns from multiple sessions
}

# Token budget for auto-generated golden rules section
TOKEN_BUDGET = 2000
CHARS_PER_TOKEN = 4  # Rough approximation

# Golden rules file path
def get_golden_rules_path() -> Path:
    """Get the path to golden-rules.md."""
    return Path.home() / ".claude" / "emergent-learning" / "memory" / "golden-rules.md"


# -----------------------------------------------------------------------------
# Decay Functions
# -----------------------------------------------------------------------------

def calculate_decay_factor(age_days: float, half_life: float = DECAY_HALF_LIFE_DAYS) -> float:
    """
    Calculate decay factor based on age.

    Uses exponential decay: factor = 0.5^(age/half_life)

    Args:
        age_days: Age in days since last observation
        half_life: Half-life in days

    Returns:
        Decay factor (0.0 to 1.0)
    """
    return 0.5 ** (age_days / half_life)


async def apply_decay(project_path: Optional[str] = None) -> int:
    """
    Apply time-based decay to all patterns.

    Args:
        project_path: Optional project path to filter patterns

    Returns:
        Number of patterns updated
    """
    if Pattern is None:
        raise ImportError("Pattern model not available")

    now = datetime.utcnow()
    updated = 0

    m = get_manager()
    async with m:
        async with m.connection():
            # Build query
            query = Pattern.select()
            if project_path:
                query = query.where(Pattern.project_path == project_path)

            patterns = []
            async for p in query:
                patterns.append(p)

            for pattern in patterns:
                last_seen = pattern.last_seen
                if not last_seen:
                    continue

                age_days = (now - last_seen).total_seconds() / 86400
                decay_factor = calculate_decay_factor(age_days)
                new_strength = pattern.strength * decay_factor

                # Floor at 0.01 to allow recovery
                new_strength = max(0.01, new_strength)

                if abs(new_strength - pattern.strength) > 0.001:
                    pattern.strength = new_strength
                    pattern.updated_at = now
                    await pattern.aio_save()
                    updated += 1

    return updated


# -----------------------------------------------------------------------------
# Promotion Functions
# -----------------------------------------------------------------------------

def is_promotion_candidate(pattern) -> bool:
    """
    Check if a pattern meets promotion criteria.

    Args:
        pattern: Pattern model instance

    Returns:
        True if pattern should be considered for promotion
    """
    # Already promoted
    if pattern.promoted_to_heuristic_id is not None:
        return False

    # Check strength threshold
    if pattern.strength < PROMOTION_THRESHOLDS['strength']:
        return False

    # Check occurrence count
    if pattern.occurrence_count < PROMOTION_THRESHOLDS['occurrence_count']:
        return False

    # Check age (avoid flash-in-pan patterns)
    if pattern.first_seen:
        age_days = (datetime.utcnow() - pattern.first_seen).total_seconds() / 86400
        if age_days < PROMOTION_THRESHOLDS['age_days']:
            return False

    # Check session diversity
    try:
        session_ids = json.loads(pattern.session_ids or '[]')
        if len(session_ids) < PROMOTION_THRESHOLDS['session_diversity']:
            return False
    except json.JSONDecodeError:
        return False

    return True


def estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    return len(text) // CHARS_PER_TOKEN


def format_pattern_for_golden_rules(pattern, rule_number: int) -> str:
    """
    Format a pattern as a golden rule entry.

    Args:
        pattern: Pattern model instance
        rule_number: Rule number for the entry

    Returns:
        Formatted markdown string
    """
    try:
        session_count = len(json.loads(pattern.session_ids or '[]'))
    except json.JSONDecodeError:
        session_count = 0

    return f"""---

## {rule_number}. {pattern.pattern_text[:50]}
> {pattern.pattern_text}

**Why:** Observed {pattern.occurrence_count}x across {session_count} sessions. Auto-distilled pattern.
**Domain:** {pattern.domain}
**Confidence:** {pattern.strength:.2f} | Validated: {pattern.occurrence_count} | Violated: 0

"""


def select_patterns_for_promotion(
    candidates: List,
    token_budget: int = TOKEN_BUDGET
) -> List:
    """
    Select patterns for promotion within token budget.

    Priority:
    1. Highest strength
    2. Highest occurrence count
    3. Most recent (within high-strength tier)

    Args:
        candidates: List of Pattern instances
        token_budget: Maximum tokens for auto-generated section

    Returns:
        List of selected patterns
    """
    # Sort by strength descending, then occurrence count
    sorted_candidates = sorted(
        candidates,
        key=lambda p: (p.strength, p.occurrence_count),
        reverse=True
    )

    selected = []
    remaining_budget = token_budget

    for pattern in sorted_candidates:
        formatted = format_pattern_for_golden_rules(pattern, 0)
        tokens_needed = estimate_tokens(formatted)

        if tokens_needed <= remaining_budget:
            selected.append(pattern)
            remaining_budget -= tokens_needed

        if remaining_budget < 100:  # Minimum viable space
            break

    return selected


async def promote_pattern_to_heuristic(pattern) -> int:
    """
    Promote a pattern to the heuristics table.

    Args:
        pattern: Pattern model instance

    Returns:
        New heuristic ID
    """
    if Heuristic is None:
        raise ImportError("Heuristic model not available")

    try:
        session_count = len(json.loads(pattern.session_ids or '[]'))
    except json.JSONDecodeError:
        session_count = 0

    m = get_manager()
    async with m:
        async with m.connection():
            # Create heuristic
            heuristic = await Heuristic.aio_create(
                domain=pattern.domain,
                rule=pattern.pattern_text,
                explanation=f"Auto-extracted pattern: {pattern.signature or 'behavioral'}. "
                           f"Observed {pattern.occurrence_count}x across {session_count} sessions.",
                source_type='auto_distilled',
                source_id=pattern.id,
                confidence=pattern.strength,
                times_validated=pattern.occurrence_count,
                times_violated=0,
                is_golden=False,  # Not golden until explicitly marked
                project_path=pattern.project_path,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Mark pattern as promoted
            pattern.promoted_to_heuristic_id = heuristic.id
            pattern.updated_at = datetime.utcnow()
            await pattern.aio_save()

            return heuristic.id


def append_to_golden_rules(patterns: List, rules_path: Optional[Path] = None) -> int:
    """
    Append auto-distilled patterns to golden-rules.md.

    Args:
        patterns: List of Pattern instances to append
        rules_path: Path to golden-rules.md (default: auto-detect)

    Returns:
        Number of rules appended
    """
    if not patterns:
        return 0

    rules_path = rules_path or get_golden_rules_path()

    if not rules_path.exists():
        print(f"[elf_distill] Golden rules file not found: {rules_path}", file=sys.stderr)
        return 0

    # Read current content
    content = rules_path.read_text(encoding='utf-8')

    # Find current max rule number
    numbers = re.findall(r'^## (\d+)\.', content, re.MULTILINE)
    next_num = max(int(n) for n in numbers) + 1 if numbers else 1

    # Check if auto-distilled section exists
    auto_section_marker = "# Auto-Distilled Patterns"
    if auto_section_marker in content:
        # Find and update existing section
        # Remove old auto-distilled content
        parts = content.split(auto_section_marker)
        if len(parts) == 2:
            # Keep everything before the marker
            content = parts[0].rstrip() + "\n\n"

    # Build new auto-distilled section
    new_section = f"{auto_section_marker}\n"
    new_section += f"> Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    new_section += "> These patterns were extracted from session observations.\n\n"

    for pattern in patterns:
        new_section += format_pattern_for_golden_rules(pattern, next_num)
        next_num += 1

    # Append to content
    content = content.rstrip() + "\n\n" + new_section

    # Write back
    rules_path.write_text(content, encoding='utf-8')

    return len(patterns)


# -----------------------------------------------------------------------------
# Main Distillation Pipeline
# -----------------------------------------------------------------------------

async def run_distillation(
    project_path: Optional[str] = None,
    auto_append: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run the full distillation pipeline.

    1. Apply decay to all patterns
    2. Identify promotion candidates
    3. Select within token budget
    4. Promote to heuristics
    5. Optionally append to golden-rules.md

    Args:
        project_path: Optional project path to filter patterns
        auto_append: Whether to auto-append to golden-rules.md
        dry_run: If True, report what would happen without making changes

    Returns:
        Summary dict with actions taken
    """
    if Pattern is None:
        raise ImportError("Pattern model not available")

    result = {
        'patterns_decayed': 0,
        'candidates_found': 0,
        'patterns_promoted': 0,
        'heuristics_created': [],
        'golden_rules_appended': 0,
        'dry_run': dry_run,
    }

    # Step 1: Apply decay (unless dry run)
    if not dry_run:
        result['patterns_decayed'] = await apply_decay(project_path)
    else:
        # Still calculate how many would be affected
        m = get_manager()
        async with m:
            async with m.connection():
                query = Pattern.select()
                if project_path:
                    query = query.where(Pattern.project_path == project_path)
                patterns = []
                async for p in query:
                    patterns.append(p)
                result['patterns_decayed'] = len([
                    p for p in patterns
                    if p.last_seen and (datetime.utcnow() - p.last_seen).days > 0
                ])

    # Step 2: Find promotion candidates
    m = get_manager()
    async with m:
        async with m.connection():
            query = Pattern.select().where(Pattern.promoted_to_heuristic_id.is_null())
            if project_path:
                query = query.where(Pattern.project_path == project_path)

            patterns = []
            async for p in query:
                patterns.append(p)
            candidates = [p for p in patterns if is_promotion_candidate(p)]
            result['candidates_found'] = len(candidates)

    if not candidates:
        return result

    # Step 3: Select within budget
    selected = select_patterns_for_promotion(candidates)

    # Step 4: Promote to heuristics
    if not dry_run:
        for pattern in selected:
            try:
                heuristic_id = await promote_pattern_to_heuristic(pattern)
                result['heuristics_created'].append({
                    'pattern_id': pattern.id,
                    'heuristic_id': heuristic_id,
                    'pattern_text': pattern.pattern_text[:80],
                })
                result['patterns_promoted'] += 1
            except Exception as e:
                print(f"[elf_distill] Failed to promote pattern {pattern.id}: {e}", file=sys.stderr)
    else:
        result['would_promote'] = [
            {'pattern_text': p.pattern_text[:80], 'strength': p.strength}
            for p in selected
        ]

    # Step 5: Auto-append to golden rules
    if auto_append and not dry_run and selected:
        result['golden_rules_appended'] = append_to_golden_rules(selected)

    return result


async def apply_decay_only(project_path: Optional[str] = None) -> int:
    """
    Lightweight operation: just apply decay, no promotion.

    Useful for mid-session checkpoints.

    Args:
        project_path: Optional project path filter

    Returns:
        Number of patterns updated
    """
    return await apply_decay(project_path)


# -----------------------------------------------------------------------------
# CLI Support
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description='Distill patterns to heuristics')
    parser.add_argument('--run', action='store_true', help='Run full distillation')
    parser.add_argument('--decay-only', action='store_true', help='Only apply decay')
    parser.add_argument('--auto-append', action='store_true', help='Auto-append to golden rules')
    parser.add_argument('--project', type=str, help='Project path filter')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    async def main():
        from src.query.models import initialize_database
        await initialize_database()

        if args.decay_only:
            decayed = await apply_decay_only(args.project)
            print(f"Applied decay to {decayed} patterns")

        elif args.run or args.dry_run:
            result = await run_distillation(
                project_path=args.project,
                auto_append=args.auto_append,
                dry_run=args.dry_run,
            )

            print(f"Distillation {'(dry run)' if args.dry_run else 'complete'}:")
            print(f"  Patterns decayed: {result['patterns_decayed']}")
            print(f"  Candidates found: {result['candidates_found']}")
            print(f"  Patterns promoted: {result['patterns_promoted']}")
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
        else:
            parser.print_help()

    asyncio.run(main())
