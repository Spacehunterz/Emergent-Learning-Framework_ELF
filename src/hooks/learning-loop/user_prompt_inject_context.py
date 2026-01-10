#!/usr/bin/env python3
"""
UserPromptSubmit hook - ENFORCES ELF context loading before every response.

This hook directly imports and calls the query system instead of spawning
a subprocess, which eliminates console window flashes on Windows.
"""
import json
import sys
import os
import asyncio
from pathlib import Path

elf_base = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(elf_base / "src" / "query"))

from core import QuerySystem


async def get_elf_context_async(session_cwd: str = "") -> str:
    """Query the ELF building for relevant context."""
    query_system = None
    try:
        query_system = await QuerySystem.create(
            current_location=session_cwd if session_cwd else None,
            debug=False
        )
        result = await query_system.build_context(
            task="Agent task context generation",
            domain=None,
            tags=None,
            max_tokens=5000,
            timeout=10,
            depth="standard"
        )
        if result:
            clean_output = result.replace("━", "-").replace("🏢", "[ELF]")
            return clean_output
        return "[ELF] No context returned"
    except Exception as e:
        return f"[ELF] Error: {str(e)[:100]}"
    finally:
        if query_system:
            try:
                await query_system.cleanup()
            except Exception:
                pass


def get_elf_context(session_cwd: str = "") -> str:
    """Sync wrapper for async context retrieval."""
    try:
        return asyncio.run(get_elf_context_async(session_cwd))
    except Exception as e:
        return f"[ELF] Error: {str(e)[:100]}"


def main():
    """Inject ELF context into every user prompt."""
    try:
        session_cwd = os.getcwd()
        input_data = json.loads(sys.stdin.read())
        elf_context = get_elf_context(session_cwd)

        print(f"""<elf-context>
{elf_context}
</elf-context>

Remember: Apply golden rules. Query building for domain-specific heuristics if needed.""")

        sys.exit(0)

    except Exception as e:
        print(f"[ELF] Hook error: {str(e)[:100]}")
        sys.exit(0)


if __name__ == "__main__":
    main()
