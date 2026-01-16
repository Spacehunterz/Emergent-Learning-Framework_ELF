"""
ELF Observation & Distillation System.

This package provides pattern extraction from session logs (Ralph loops)
and distillation of patterns into heuristics for the Emergent Learning Framework.

Components:
- elf_observe: Extract patterns from session logs
- elf_distill: Apply decay, promote patterns to heuristics

Usage:
    # Extract patterns from a session log
    from src.observe.elf_observe import extract_patterns_from_session
    patterns = await extract_patterns_from_session('/path/to/session.log')

    # Run distillation
    from src.observe.elf_distill import run_distillation
    result = await run_distillation(auto_append=True)

CLI:
    python -m src.observe observe --session /path/to/log
    python -m src.observe distill --run --auto-append
"""

from .elf_observe import (
    extract_patterns_from_session,
    upsert_pattern,
    PatternExtractor,
)

from .elf_distill import (
    run_distillation,
    apply_decay,
    is_promotion_candidate,
    promote_pattern_to_heuristic,
)

__all__ = [
    # Observation
    'extract_patterns_from_session',
    'upsert_pattern',
    'PatternExtractor',
    # Distillation
    'run_distillation',
    'apply_decay',
    'is_promotion_candidate',
    'promote_pattern_to_heuristic',
]
