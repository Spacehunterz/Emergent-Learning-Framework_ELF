#!/usr/bin/env python3
"""
Stop Hook: Clean up coordination state when session ends.

This hook:
1. Marks any active agents from this session as completed
2. Logs session summary to blackboard
3. Reports any unresolved blockers
4. Extracts patterns from session log for ELF learning
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add utils to path for blackboard import (required for standalone hook execution)
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from blackboard import Blackboard

# ELF paths
ELF_BASE = Path.home() / ".claude" / "emergent-learning"
SESSION_LOGS_DIR = ELF_BASE / "sessions" / "logs"


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError) as e:
        sys.stderr.write(f"Warning: Hook input error: {e}\n")
        return {}


def output_result(result: dict = None):
    """Output hook result to stdout."""
    print(json.dumps(result or {}))


async def run_elf_observation():
    """
    Extract patterns from today's session log and run lightweight distillation.

    This is non-blocking and failure-tolerant - if ELF isn't available or
    there's an error, we just log and continue.
    """
    try:
        # Add ELF to path
        sys.path.insert(0, str(ELF_BASE / "src"))

        from query.models import initialize_database
        from observe.elf_observe import extract_patterns_from_session
        from observe.elf_distill import apply_decay_only

        # Initialize database
        await initialize_database()

        # Find today's session log
        today = datetime.now().strftime("%Y-%m-%d")
        session_log = SESSION_LOGS_DIR / f"{today}_session.jsonl"

        if session_log.exists():
            patterns = await extract_patterns_from_session(str(session_log))
            sys.stderr.write(f"[ELF] Extracted {len(patterns)} patterns from session\n")

            # Apply decay (lightweight, no promotion)
            decayed = await apply_decay_only()
            if decayed > 0:
                sys.stderr.write(f"[ELF] Applied decay to {decayed} patterns\n")

    except ImportError as e:
        sys.stderr.write(f"[ELF] Not available: {e}\n")
    except Exception as e:
        sys.stderr.write(f"[ELF] Observation error (non-fatal): {e}\n")


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    # Check if coordination is enabled
    cwd = os.getcwd()
    coordination_dir = Path(cwd) / ".coordination"

    if not coordination_dir.exists():
        output_result()
        return

    # Initialize blackboard
    bb = Blackboard(cwd)

    try:
        # Get session summary for logging
        summary = bb.get_summary()

        # Check for any dangling active agents (shouldn't happen normally)
        active = bb.get_active_agents()
        if active:
            sys.stderr.write(f"Note: {len(active)} agents still marked active at session end\n")

        # Check for unresolved blockers
        questions = bb.get_open_questions()
        blocking = [q for q in questions if q.get("blocking")]
        if blocking:
            sys.stderr.write(f"Warning: {len(blocking)} unresolved blocking questions\n")
            for q in blocking:
                sys.stderr.write(f"  - {q['question']}\n")

    except Exception as e:
        sys.stderr.write(f"Warning: Session end hook error: {e}\n")

    # Run ELF observation (non-blocking, failure-tolerant)
    try:
        asyncio.run(run_elf_observation())
    except Exception as e:
        sys.stderr.write(f"Warning: ELF observation skipped: {e}\n")

    output_result()


if __name__ == "__main__":
    main()
