#!/usr/bin/env python3
"""
Post-Tool Learning Hook: Validate heuristics and close the learning loop.

This hook completes the learning loop by:
1. Checking task outcomes (success/failure)
2. Validating heuristics that were consulted
3. Auto-recording failures when they happen
4. Incrementing validation counts on successful tasks
5. Flagging heuristics that may have led to failures

The key insight: If we showed heuristics before a task and the task succeeded,
those heuristics were useful. If the task failed, maybe they weren't.
"""

import json
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Paths - using Path.home() for portability
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
DB_PATH = EMERGENT_LEARNING_PATH / "memory" / "index.db"
STATE_FILE = Path.home() / ".claude" / "hooks" / "learning-loop" / "session-state.json"


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError):
        return {}


def output_result(result: dict):
    """Output hook result to stdout."""
    print(json.dumps(result))


def load_session_state() -> dict:
    """Load current session state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError, ValueError):
            pass
    return {
        "session_start": datetime.now().isoformat(),
        "heuristics_consulted": [],
        "domains_queried": [],
        "task_context": None
    }


def save_session_state(state: dict):
    """Save session state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_db_connection():
    """Get SQLite connection."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def determine_outcome(tool_output: dict) -> Tuple[str, str]:
    """Determine if the task succeeded or failed.

    Returns: (outcome, reason)
    - outcome: 'success', 'failure', 'unknown'
    - reason: description of why
    """
    if not tool_output:
        return "unknown", "No output to analyze"

    # Get content
    content = ""
    if isinstance(tool_output, dict):
        content = tool_output.get("content", "") or ""
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "") for item in content
                if isinstance(item, dict)
            )
    elif isinstance(tool_output, str):
        content = tool_output

    if not content:
        return "unknown", "Empty output"

    content_lower = content.lower()

    # Strong failure indicators (case-insensitive with word boundaries)
    failure_patterns = [
        (r'(?i)\berror\b[:\s]', "Error detected"),
        (r'(?i)\bexception\b[:\s]', "Exception raised"),
        (r'(?i)\bfailed\b[:\s]', "Operation failed"),
        (r'(?i)\bcould not\b', "Could not complete"),
        (r'(?i)\bunable to\b', "Unable to complete"),
        (r'\[BLOCKER\]', "Blocker encountered"),
        (r'(?i)\btraceback\b', "Exception traceback"),
        (r'(?i)\bpermission denied\b', "Permission denied"),
        (r'(?i)\btimeout\b', "Timeout occurred"),
        (r'(?i)^.*\bnot found\s*$', "Resource not found"),  # Only at end of line
    ]

    # Patterns to exclude false positives
    false_positive_patterns = [
        r'(?i)was not found to be',
        r'(?i)\berror handling\b',
        r'(?i)\bno errors?\b',
        r'(?i)\bwithout errors?\b',
        r'(?i)\berror.?free\b',
    ]

    for pattern, reason in failure_patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            # Verify this isn't a false positive by checking surrounding context
            match_start = max(0, match.start() - 30)
            match_end = min(len(content), match.end() + 30)
            context = content[match_start:match_end]

            # Skip if this match is part of a false positive pattern
            is_false_positive = any(
                re.search(fp, context) for fp in false_positive_patterns
            )
            if not is_false_positive:
                return "failure", reason

    # Strong success indicators
    success_patterns = [
        (r'successfully completed', "Successfully completed"),
        (r'task complete', "Task completed"),
        (r'done\.', "Done"),
        (r'finished', "Finished"),
        (r'all tests pass', "Tests passed"),
        (r'\[success\]', "Success marker found"),
        (r'## FINDINGS', "Findings reported (likely success)"),
    ]

    for pattern, reason in success_patterns:
        if re.search(pattern, content_lower):
            return "success", reason

    # If we got substantial output without errors, probably success
    if len(content) > 100:
        return "success", "Substantial output without errors"

    return "unknown", "Could not determine outcome"


def validate_heuristics(heuristic_ids: List[int], outcome: str):
    """Update heuristic validation counts based on outcome."""
    conn = get_db_connection()
    if not conn or not heuristic_ids:
        return

    try:
        cursor = conn.cursor()

        if outcome == "success":
            # Increment times_validated for consulted heuristics
            placeholders = ",".join("?" * len(heuristic_ids))
            cursor.execute(f"""
                UPDATE heuristics
                SET times_validated = times_validated + 1,
                    confidence = MIN(1.0, confidence + 0.01),
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, (datetime.now().isoformat(), *heuristic_ids))

            # Log the validation
            for hid in heuristic_ids:
                cursor.execute("""
                    INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                    VALUES ('heuristic_validated', 'validation', 1, ?, ?)
                """, (f"heuristic_id:{hid}", "success"))

        elif outcome == "failure":
            # Increment times_violated - heuristic might not be reliable
            placeholders = ",".join("?" * len(heuristic_ids))
            cursor.execute(f"""
                UPDATE heuristics
                SET times_violated = times_violated + 1,
                    confidence = MAX(0.0, confidence - 0.02),
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, (datetime.now().isoformat(), *heuristic_ids))

            # Log the violation
            for hid in heuristic_ids:
                cursor.execute("""
                    INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                    VALUES ('heuristic_violated', 'violation', 1, ?, ?)
                """, (f"heuristic_id:{hid}", "failure"))

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to validate heuristics: {e}\n")
    finally:
        conn.close()


def check_golden_rule_promotion(conn):
    """Check if any heuristics should be promoted to golden rules."""
    try:
        cursor = conn.cursor()

        # Find heuristics with high confidence and many validations
        cursor.execute("""
            SELECT id, domain, rule, confidence, times_validated, times_violated
            FROM heuristics
            WHERE is_golden = 0
              AND confidence >= 0.9
              AND times_validated >= 10
              AND (times_violated = 0 OR times_validated / times_violated > 10)
        """)

        candidates = cursor.fetchall()

        for c in candidates:
            # Promote to golden
            cursor.execute("""
                UPDATE heuristics
                SET is_golden = 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), c['id']))

            # Log the promotion
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                VALUES ('golden_rule_promotion', 'promotion', ?, ?, ?)
            """, (c['id'], f"domain:{c['domain']}", c['rule'][:100]))

            sys.stderr.write(f"PROMOTED TO GOLDEN RULE: {c['rule'][:50]}...\n")

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to check golden rule promotion: {e}\n")


def auto_record_failure(tool_input: dict, tool_output: dict, outcome_reason: str, domains: List[str]):
    """Auto-record a failure to the learnings table."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # Extract details
        prompt = tool_input.get("prompt", "")[:500]
        description = tool_input.get("description", "unknown task")

        # Get output content
        output_content = ""
        if isinstance(tool_output, dict):
            output_content = str(tool_output.get("content", ""))[:1000]
        elif isinstance(tool_output, str):
            output_content = tool_output[:1000]

        # Create failure record
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"auto-failures/failure_{timestamp}.md"
        title = f"Auto-captured: {description[:50]}"
        summary = f"Reason: {outcome_reason}\n\nTask: {description}\n\nOutput snippet: {output_content[:200]}"
        domain = domains[0] if domains else "general"

        cursor.execute("""
            INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
            VALUES ('failure', ?, ?, ?, ?, 3, ?)
        """, (filepath, title, summary, domain, datetime.now().isoformat()))

        # Log the auto-capture
        cursor.execute("""
            INSERT INTO metrics (metric_type, metric_name, metric_value, context)
            VALUES ('auto_failure_capture', 'capture', 1, ?)
        """, (title,))

        conn.commit()
        sys.stderr.write(f"AUTO-RECORDED FAILURE: {title}\n")

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to auto-record failure: {e}\n")
    finally:
        conn.close()


def extract_and_record_learnings(tool_output: dict, domains: List[str]):
    """Extract learnings from successful task output and record them."""
    conn = get_db_connection()
    if not conn:
        return

    # Get content
    content = ""
    if isinstance(tool_output, dict):
        content = tool_output.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "") for item in content
                if isinstance(item, dict)
            )

    # Look for explicit learning markers
    # Format: [LEARNED:domain] description
    learning_pattern = r'\[LEARN(?:ED|ING)?:?([^\]]*)\]\s*([^\n]+)'
    matches = re.findall(learning_pattern, content, re.IGNORECASE)

    if not matches:
        return

    try:
        cursor = conn.cursor()

        for domain_hint, learning in matches:
            domain = domain_hint.strip() if domain_hint.strip() else (domains[0] if domains else "general")

            # Check if this might be a heuristic (contains "always", "never", "should", etc.)
            is_heuristic = any(word in learning.lower() for word in
                              ["always", "never", "should", "must", "don't", "avoid", "prefer"])

            if is_heuristic:
                # Record as heuristic
                cursor.execute("""
                    INSERT INTO heuristics (domain, rule, explanation, confidence, source_type, created_at)
                    VALUES (?, ?, 'Auto-extracted from task output', 0.5, 'auto', ?)
                """, (domain, learning.strip(), datetime.now().isoformat()))

                sys.stderr.write(f"AUTO-EXTRACTED HEURISTIC: {learning[:50]}...\n")
            else:
                # Record as observation
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cursor.execute("""
                    INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
                    VALUES ('observation', ?, ?, ?, ?, 3, ?)
                """, (
                    f"auto-observations/obs_{timestamp}.md",
                    learning[:100],
                    learning,
                    domain,
                    datetime.now().isoformat()
                ))

        conn.commit()

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to record learnings: {e}\n")
    finally:
        conn.close()


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    tool_name = hook_input.get("tool_name", hook_input.get("tool"))
    tool_input = hook_input.get("tool_input", hook_input.get("input", {}))
    tool_output = hook_input.get("tool_output", hook_input.get("output", {}))

    if not tool_name:
        output_result({})
        return

    # Only process Task tool (subagent completions)
    if tool_name != "Task":
        output_result({})
        return

    # Load session state
    state = load_session_state()
    heuristics_consulted = state.get("heuristics_consulted", [])
    domains_queried = state.get("domains_queried", [])

    # Determine outcome
    outcome, reason = determine_outcome(tool_output)

    # Validate heuristics based on outcome
    if heuristics_consulted:
        validate_heuristics(heuristics_consulted, outcome)

    # Check for golden rule promotions
    conn = get_db_connection()
    if conn:
        check_golden_rule_promotion(conn)
        conn.close()

    # Auto-record failure if task failed
    if outcome == "failure":
        auto_record_failure(tool_input, tool_output, reason, domains_queried)

    # Extract any explicit learnings from output
    if outcome == "success":
        extract_and_record_learnings(tool_output, domains_queried)

    # Clear consulted heuristics for next task
    state["heuristics_consulted"] = []
    save_session_state(state)

    # Log outcome
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                VALUES ('task_outcome', ?, 1, ?, ?)
            """, (outcome, f"reason:{reason[:50]}", datetime.now().isoformat()))
            conn.commit()
        except:
            pass
        finally:
            conn.close()

    # Output (no modification to tool output)
    output_result({})


if __name__ == "__main__":
    main()
