#!/usr/bin/env python3
"""
UserPromptSubmit hook - ENFORCES ELF context loading before every response.

This is not optional. Every prompt gets context injected so Claude cannot
skip the learning framework.

The hook:
1. Runs query.py --context to get relevant heuristics/golden rules
2. Injects the context as a system-reminder in the response
3. Claude sees this context BEFORE responding

This replaces the stub that was doing nothing.
"""
import json
import sys
import subprocess
import os
from pathlib import Path


def get_elf_context(prompt_text: str = "") -> str:
    """Query the ELF building for relevant context."""
    # Get paths
    elf_base = Path(__file__).parent.parent.parent.parent  # emergent-learning/
    venv_python = elf_base / ".venv" / "Scripts" / "python.exe"
    query_script = elf_base / "src" / "query" / "query.py"

    # Fallback for non-Windows
    if not venv_python.exists():
        venv_python = elf_base / ".venv" / "bin" / "python"

    if not query_script.exists():
        return "[ELF] Query script not found"

    try:
        # Run query with minimal depth for speed, but include golden rules
        # Use UTF-8 encoding explicitly for Windows compatibility
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            [str(venv_python), str(query_script), "--context", "--depth", "minimal"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Replace undecodable chars instead of crashing
            timeout=10,  # Don't block forever
            cwd=str(elf_base / "src" / "query"),
            env=env
        )

        if result.returncode == 0 and result.stdout and result.stdout.strip():
            # Strip emoji/unicode that might cause issues
            output = result.stdout.strip()
            # Remove box-drawing chars and emoji for cleaner injection
            clean_output = output.replace("━", "-").replace("🏢", "[ELF]")
            return clean_output
        elif result.stderr:
            return f"[ELF] Query error: {result.stderr[:200]}"
        else:
            return "[ELF] No context returned"

    except subprocess.TimeoutExpired:
        return "[ELF] Query timeout - proceeding without context"
    except Exception as e:
        return f"[ELF] Error: {str(e)[:100]}"


def main():
    """Inject ELF context into every user prompt."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # Get the user's prompt text if available
        prompt_text = ""
        if "prompt" in input_data:
            prompt_text = input_data.get("prompt", "")

        # Query ELF for context
        elf_context = get_elf_context(prompt_text)

        # Build the injection message
        # This appears as a system-reminder that Claude will see
        injection = f"""<elf-context>
{elf_context}
</elf-context>

Remember: Query the building BEFORE taking action. The above context contains relevant heuristics and golden rules."""

        # Return with injected context
        result = {
            "continue": True,
            "message": injection
        }

        print(json.dumps(result))

    except Exception as e:
        # On error, still continue but note the failure
        error_msg = f"[ELF hook error: {str(e)[:50]}]"
        print(json.dumps({
            "continue": True,
            "message": error_msg
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()
