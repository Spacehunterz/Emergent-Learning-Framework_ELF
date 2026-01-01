#!/usr/bin/env python3
"""
UserPromptSubmit hook - ENFORCES ELF context loading before every response.

This is not optional. Every prompt gets context injected so Claude cannot
skip the learning framework.

The hook:
1. Runs query.py --context to get relevant heuristics/golden rules
2. Prints context to stdout (plain text injection)
3. Exits with code 0 - Claude sees this as system context

FIX (2025-12-31): Changed from JSON "message" field to plain text stdout.
The "message" field was being shown as "Success" feedback, not injected.
Plain text to stdout with exit 0 is the correct injection mechanism.
"""
import json
import sys
import subprocess
import os
from pathlib import Path


def get_elf_context(prompt_text: str = "", session_cwd: str = "") -> str:
    """Query the ELF building for relevant context.

    Args:
        prompt_text: The user's prompt (for future semantic matching)
        session_cwd: Claude Code's actual working directory (for project detection)
    """
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

        # Build command with location argument if we have the session CWD
        cmd = [str(venv_python), str(query_script), "--context", "--depth", "standard"]
        if session_cwd:
            cmd.extend(["--location", session_cwd])

        # Use standard depth to include golden rules (minimal filters too aggressively)
        result = subprocess.run(
            cmd,
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
        # CRITICAL: Capture CWD BEFORE any operations
        # This is Claude Code's actual working directory, not ELF's location
        session_cwd = os.getcwd()

        # Read input from stdin (required by hook protocol)
        input_data = json.loads(sys.stdin.read())

        # Get the user's prompt text if available
        prompt_text = ""
        if "prompt" in input_data:
            prompt_text = input_data.get("prompt", "")

        # Query ELF for context, passing the session's actual CWD
        elf_context = get_elf_context(prompt_text, session_cwd)

        # Print context directly to stdout - this IS the injection
        # Claude Code adds stdout text as context when exit code is 0
        print(f"""<elf-context>
{elf_context}
</elf-context>

Remember: Apply golden rules. Query building for domain-specific heuristics if needed.""")

        # Exit 0 = success, stdout becomes context
        sys.exit(0)

    except Exception as e:
        # On error, still inject minimal context
        print(f"[ELF] Hook error: {str(e)[:100]}")
        sys.exit(0)


if __name__ == "__main__":
    main()
