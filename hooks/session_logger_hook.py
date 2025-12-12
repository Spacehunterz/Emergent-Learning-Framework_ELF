#!/usr/bin/env python3
"""
Session Logger Hook for Emergent Learning Framework.

A post-tool hook that captures ALL tool usage and logs it to session files.
This provides a comprehensive audit trail of agent activities.

Key Features:
- Captures every tool invocation (not just Task)
- Non-blocking (errors logged but don't fail the tool)
- Integrates with the session logger module
- Thread-safe for parallel tool execution

Hook Protocol:
- Reads JSON from stdin: {"tool_name": str, "tool_input": dict, "tool_output": dict}
- Writes JSON to stdout: {} (no modification, just observation)
- All errors go to stderr

This is a POST-tool hook, meaning it runs AFTER the tool completes.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add the sessions directory to path for logger import
SESSIONS_DIR = Path.home() / ".claude" / "emergent-learning" / "sessions"
sys.path.insert(0, str(SESSIONS_DIR))

try:
    from logger import SessionLogger, get_logger
except ImportError:
    # Fallback: define minimal logger inline
    class SessionLogger:
        """Minimal fallback logger if main module not available."""
        def __init__(self):
            self.logs_dir = Path.home() / ".claude" / "emergent-learning" / "sessions" / "logs"
            self.logs_dir.mkdir(parents=True, exist_ok=True)

        def log_tool_use(self, tool, tool_input, tool_output, outcome):
            try:
                from datetime import datetime
                log_file = self.logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}_session.jsonl"
                entry = {
                    "ts": datetime.now().isoformat(),
                    "type": "tool_use",
                    "tool": tool,
                    "input_summary": str(tool_input)[:500],
                    "output_summary": str(tool_output)[:500],
                    "outcome": outcome
                }
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + "\n")
                return True
            except Exception:
                return False

    def get_logger():
        return SessionLogger()


def log_error(message: str):
    """Log error to stderr (non-blocking)."""
    try:
        sys.stderr.write(f"[SessionLoggerHook] ERROR: {message}\n")
    except:
        pass


def log_debug(message: str):
    """Log debug message to stderr."""
    try:
        if os.environ.get('ELF_DEBUG', '').lower() in ('1', 'true', 'yes'):
            sys.stderr.write(f"[SessionLoggerHook] DEBUG: {message}\n")
    except:
        pass


def get_hook_input() -> dict:
    """
    Read hook input from stdin.

    Expected format:
    {
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_output": {"content": "..."}
    }

    Returns empty dict on parse failure.
    """
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError) as e:
        log_error(f"Failed to parse hook input: {e}")
        return {}


def output_result(result: dict):
    """
    Output hook result to stdout.

    For observation hooks, this is typically empty {} to indicate
    no modification to tool behavior.
    """
    try:
        print(json.dumps(result))
    except Exception as e:
        log_error(f"Failed to output result: {e}")
        print("{}")


def determine_outcome(tool_output: Any) -> str:
    """
    Determine if the tool execution succeeded or failed.

    Analyzes the output content for success/failure indicators.

    Args:
        tool_output: The output from the tool

    Returns:
        "success", "failure", or "unknown"
    """
    if not tool_output:
        return "unknown"

    # Extract content string
    content = ""
    if isinstance(tool_output, dict):
        content = tool_output.get("content", "")
        if isinstance(content, list):
            # Handle Claude API format: [{"type": "text", "text": "..."}]
            texts = []
            for item in content:
                if isinstance(item, dict):
                    texts.append(item.get("text", ""))
            content = "\n".join(texts)
        # Check for explicit error field
        if tool_output.get("error"):
            return "failure"
        if tool_output.get("success") is True:
            return "success"
        if tool_output.get("success") is False:
            return "failure"
    elif isinstance(tool_output, str):
        content = tool_output

    if not content:
        return "unknown"

    content_lower = content.lower()

    # Failure indicators
    failure_patterns = [
        "error:", "exception:", "failed:", "traceback",
        "permission denied", "not found", "could not",
        "unable to", "[blocker]", "command not found",
        "no such file", "syntax error"
    ]

    for pattern in failure_patterns:
        if pattern in content_lower:
            return "failure"

    # Success indicators
    success_patterns = [
        "successfully", "completed", "created",
        "wrote", "updated", "modified"
    ]

    for pattern in success_patterns:
        if pattern in content_lower:
            return "success"

    # If we have substantial output without errors, assume success
    if len(content) > 50:
        return "success"

    return "unknown"


def extract_tool_context(tool_name: str, tool_input: dict) -> Dict[str, Any]:
    """
    Extract context-specific information based on tool type.

    This helps enrich the log entry with tool-specific metadata.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        Dict with extracted context
    """
    context = {}

    if tool_name == "Bash":
        context["command"] = tool_input.get("command", "")[:200]
        context["timeout"] = tool_input.get("timeout")

    elif tool_name == "Read":
        context["file_path"] = tool_input.get("file_path", "")
        context["offset"] = tool_input.get("offset")
        context["limit"] = tool_input.get("limit")

    elif tool_name == "Write":
        context["file_path"] = tool_input.get("file_path", "")
        content = tool_input.get("content", "")
        context["content_length"] = len(content) if content else 0

    elif tool_name == "Edit":
        context["file_path"] = tool_input.get("file_path", "")
        context["replace_all"] = tool_input.get("replace_all", False)

    elif tool_name == "Grep":
        context["pattern"] = tool_input.get("pattern", "")
        context["path"] = tool_input.get("path", "")
        context["output_mode"] = tool_input.get("output_mode", "files_with_matches")

    elif tool_name == "Glob":
        context["pattern"] = tool_input.get("pattern", "")
        context["path"] = tool_input.get("path", "")

    elif tool_name == "Task":
        context["description"] = tool_input.get("description", "")[:100]
        prompt = tool_input.get("prompt", "")
        context["prompt_length"] = len(prompt) if prompt else 0

    elif tool_name == "WebFetch":
        context["url"] = tool_input.get("url", "")
        context["prompt"] = tool_input.get("prompt", "")[:100]

    elif tool_name == "WebSearch":
        context["query"] = tool_input.get("query", "")

    return context


def main():
    """
    Main hook entry point.

    Reads tool execution details from stdin and logs them to the session file.
    Always outputs {} to indicate no modification to tool behavior.
    """
    try:
        # Read input
        hook_input = get_hook_input()

        if not hook_input:
            output_result({})
            return

        # Extract fields (handle both naming conventions)
        tool_name = hook_input.get("tool_name") or hook_input.get("tool", "")
        tool_input = hook_input.get("tool_input") or hook_input.get("input", {})
        tool_output = hook_input.get("tool_output") or hook_input.get("output", {})

        if not tool_name:
            log_debug("No tool name provided, skipping")
            output_result({})
            return

        # Determine outcome
        outcome = determine_outcome(tool_output)

        # Extract context
        context = extract_tool_context(tool_name, tool_input)

        log_debug(f"Logging tool: {tool_name}, outcome: {outcome}")

        # Log to session file
        try:
            logger = get_logger()

            # Merge context into tool_input for logging
            enriched_input = {**tool_input, "_context": context}

            success = logger.log_tool_use(
                tool=tool_name,
                tool_input=enriched_input,
                tool_output=tool_output,
                outcome=outcome
            )

            if success:
                log_debug(f"Successfully logged {tool_name}")
            else:
                log_error(f"Failed to log {tool_name}")

        except Exception as e:
            log_error(f"Logging exception: {e}")

    except Exception as e:
        log_error(f"Hook exception: {e}")

    # Always output empty result (no modification)
    output_result({})


if __name__ == "__main__":
    main()
