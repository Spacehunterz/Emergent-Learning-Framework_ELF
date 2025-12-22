#!/usr/bin/env python3
"""
Pre-Tool Learning Hook: Auto-inject relevant heuristics and complexity warnings before investigation.

This hook closes the learning loop by:
1. Auto-querying the building for relevant heuristics
2. Scoring task complexity and risk level
3. Injecting applicable rules and warnings into the agent's context
4. Tracking which heuristics are being consulted (for validation)

Works with: Grep, Read, Glob, Task, Bash (investigation tools)
"""

import json
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

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


class ComplexityScorer:
    """Scores task complexity and risk level."""

    HIGH_RISK_PATTERNS = {
        'files': [r'auth', r'crypto', r'security', r'password', r'token', r'secret', r'\.env'],
        'domains': ['authentication', 'security', 'database-migration', 'production'],
        'keywords': ['delete', 'drop', 'truncate', 'force', 'sudo', 'rm -rf', 'password', 'credential']
    }

    MEDIUM_RISK_PATTERNS = {
        'files': [r'api', r'config', r'schema', r'migration', r'database'],
        'domains': ['api', 'configuration', 'database'],
        'keywords': ['update', 'modify', 'change', 'refactor', 'migrate']
    }

    @classmethod
    def score(cls, tool_name: str, tool_input: dict, domains: List[str]) -> Dict:
        """
        Score task complexity and risk.

        Returns:
            {
                'level': 'HIGH' | 'MEDIUM' | 'LOW',
                'reasons': List[str],
                'recommendation': str
            }
        """
        reasons = []
        high_score = 0
        medium_score = 0

        # Get text to analyze
        text = ""
        file_paths = ""

        if tool_name == "Task":
            text = tool_input.get("prompt", "") + " " + tool_input.get("description", "")
        elif tool_name == "Bash":
            text = tool_input.get("command", "")
        elif tool_name in ("Grep", "Read", "Glob", "Edit", "Write"):
            text = tool_input.get("pattern", "") + " " + tool_input.get("old_string", "") + " " + tool_input.get("new_string", "")
            file_paths = tool_input.get("file_path", "") + " " + tool_input.get("path", "")

        text_lower = text.lower()
        file_paths_lower = file_paths.lower()

        # Check HIGH risk patterns
        for pattern in cls.HIGH_RISK_PATTERNS['files']:
            # Check both file paths and text (task prompts might mention files)
            if re.search(pattern, file_paths_lower) or re.search(pattern, text_lower):
                high_score += 2
                reasons.append(f"High-risk file pattern: {pattern}")

        for keyword in cls.HIGH_RISK_PATTERNS['keywords']:
            if keyword in text_lower:
                high_score += 2
                reasons.append(f"High-risk keyword: {keyword}")

        for domain in cls.HIGH_RISK_PATTERNS['domains']:
            if domain in domains:
                high_score += 1
                reasons.append(f"High-risk domain: {domain}")

        # Check MEDIUM risk patterns
        for pattern in cls.MEDIUM_RISK_PATTERNS['files']:
            # Check both file paths and text (task prompts might mention files)
            if re.search(pattern, file_paths_lower) or re.search(pattern, text_lower):
                medium_score += 1
                reasons.append(f"Medium-risk file pattern: {pattern}")

        for keyword in cls.MEDIUM_RISK_PATTERNS['keywords']:
            if keyword in text_lower:
                medium_score += 1
                reasons.append(f"Medium-risk keyword: {keyword}")

        for domain in cls.MEDIUM_RISK_PATTERNS['domains']:
            if domain in domains:
                medium_score += 1
                reasons.append(f"Medium-risk domain: {domain}")

        # Determine level and recommendation
        if high_score >= 2:
            level = 'HIGH'
            recommendation = "Extra scrutiny recommended. Consider CEO escalation if uncertain. Verify changes carefully before applying."
        elif high_score >= 1 or medium_score >= 3:
            level = 'MEDIUM'
            recommendation = "Moderate care required. Review changes and test thoroughly."
        elif medium_score >= 1:
            level = 'LOW-MEDIUM'
            recommendation = "Standard care. Review as normal."
        else:
            level = 'LOW'
            recommendation = "Routine task. Proceed normally."

        return {
            'level': level,
            'reasons': reasons,
            'recommendation': recommendation
        }


def extract_domain_from_context(tool_name: str, tool_input: dict) -> List[str]:
    """Extract likely domains from the tool call context."""
    domains = []

    # Get text to analyze
    text = ""
    if tool_name == "Task":
        text = tool_input.get("prompt", "") + " " + tool_input.get("description", "")
    elif tool_name == "Bash":
        text = tool_input.get("command", "")
    elif tool_name in ("Grep", "Read", "Glob"):
        text = tool_input.get("pattern", "") + " " + tool_input.get("file_path", "") + " " + tool_input.get("path", "")

    text = text.lower()

    # Domain keyword mapping
    domain_keywords = {
        "authentication": ["auth", "login", "session", "jwt", "token", "oauth", "password"],
        "database": ["sql", "query", "schema", "migration", "db", "database", "sqlite", "postgres"],
        "database-migration": ["migration", "migrate", "schema change", "alter table"],
        "api": ["api", "endpoint", "rest", "graphql", "route", "controller"],
        "security": ["security", "vulnerability", "injection", "xss", "csrf", "sanitiz"],
        "testing": ["test", "spec", "coverage", "mock", "fixture", "assert"],
        "frontend": ["react", "vue", "component", "css", "style", "ui", "dom"],
        "performance": ["performance", "cache", "optimize", "memory", "speed"],
        "error-handling": ["error", "exception", "catch", "throw", "try"],
        "configuration": ["config", "env", "setting", "option"],
        "production": ["production", "prod", "deploy", "release"],
        "git": ["git", "commit", "branch", "merge", "rebase"],
        "python": ["python", "pip", "venv", ".py"],
        "javascript": ["node", "npm", "yarn", "bun", ".js", ".ts"],
    }

    for domain, keywords in domain_keywords.items():
        if any(kw in text for kw in keywords):
            domains.append(domain)

    return domains[:5]  # Limit to 5


def get_relevant_heuristics(domains: List[str], limit: int = 5) -> List[Dict]:
    """Get heuristics relevant to the given domains."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        if domains:
            placeholders = ",".join("?" * len(domains))
            cursor.execute(f"""
                SELECT id, domain, rule, explanation, confidence, times_validated, is_golden
                FROM heuristics
                WHERE domain IN ({placeholders})
                   OR is_golden = 1
                ORDER BY is_golden DESC, confidence DESC, times_validated DESC
                LIMIT ?
            """, (*domains, limit))
        else:
            # Just get golden rules and top heuristics
            cursor.execute("""
                SELECT id, domain, rule, explanation, confidence, times_validated, is_golden
                FROM heuristics
                WHERE is_golden = 1 OR confidence > 0.7
                ORDER BY is_golden DESC, confidence DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to query heuristics: {e}\n")
        return []
    finally:
        conn.close()


def get_recent_failures(domains: List[str], limit: int = 3) -> List[Dict]:
    """Get recent failures in relevant domains."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        if domains:
            placeholders = ",".join("?" * len(domains))
            cursor.execute(f"""
                SELECT id, title, summary, domain
                FROM learnings
                WHERE type = 'failure'
                  AND domain IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT ?
            """, (*domains, limit))
        else:
            cursor.execute("""
                SELECT id, title, summary, domain
                FROM learnings
                WHERE type = 'failure'
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]
    except:
        return []
    finally:
        conn.close()


def record_heuristics_consulted(heuristic_ids: List[int]):
    """Record which heuristics were shown to the agent."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        # Record in a consultation log for later validation
        for hid in heuristic_ids:
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
                VALUES ('heuristic_consulted', 'consultation', ?, ?, ?)
            """, (hid, f"heuristic_id:{hid}", datetime.now().isoformat()))

        conn.commit()
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to record consultation: {e}\n")
    finally:
        conn.close()


def format_learning_context(heuristics: List[Dict], failures: List[Dict], domains: List[str], complexity: Optional[Dict] = None) -> str:
    """Format the learning context for injection."""
    lines = [
        "",
        "---",
        "## Building Knowledge (Auto-Injected)",
        ""
    ]

    # Complexity warning (if applicable)
    if complexity and complexity['level'] in ('HIGH', 'MEDIUM'):
        warning_symbol = "⚠️" if complexity['level'] == 'HIGH' else "⚡"
        lines.append(f"### Task Complexity: {complexity['level']} {warning_symbol}")
        if complexity['reasons']:
            lines.append("**Reasons:**")
            for reason in complexity['reasons']:
                lines.append(f"- {reason}")
        lines.append(f"**Recommendation:** {complexity['recommendation']}")
        lines.append("")

    # Golden rules first
    golden = [h for h in heuristics if h.get("is_golden")]
    if golden:
        lines.append("### Golden Rules (Must Follow)")
        for h in golden:
            lines.append(f"- **{h['rule']}**")
        lines.append("")

    # Domain-specific heuristics
    domain_h = [h for h in heuristics if not h.get("is_golden")]
    if domain_h:
        lines.append(f"### Relevant Heuristics ({', '.join(domains) if domains else 'general'})")
        for h in domain_h:
            conf = h.get('confidence', 0) * 100
            validated = h.get('times_validated', 0)
            lines.append(f"- [{h['domain']}] {h['rule']} ({conf:.0f}% confidence, {validated}x validated)")
        lines.append("")

    # Recent failures to avoid
    if failures:
        lines.append("### Recent Failures (Avoid These)")
        for f in failures:
            lines.append(f"- [{f['domain']}] {f['title']}: {(f.get('summary') or '')[:100]}")
        lines.append("")

    lines.extend([
        "---",
        ""
    ])

    return "\n".join(lines)


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    tool_name = hook_input.get("tool_name", hook_input.get("tool"))
    tool_input = hook_input.get("tool_input", hook_input.get("input", {}))

    if not tool_name:
        output_result({"decision": "approve"})
        return

    # Only inject for Task tool (subagent spawning)
    # Other tools get the golden-rule-enforcer treatment
    if tool_name != "Task":
        output_result({"decision": "approve"})
        return

    # Load session state
    state = load_session_state()

    # Extract domains from context
    domains = extract_domain_from_context(tool_name, tool_input)
    state["domains_queried"].extend(domains)
    state["domains_queried"] = list(set(state["domains_queried"]))

    # Score task complexity
    complexity = ComplexityScorer.score(tool_name, tool_input, domains)

    # Get relevant heuristics
    heuristics = get_relevant_heuristics(domains)

    # Get recent failures
    failures = get_recent_failures(domains)

    # Track consulted heuristics
    heuristic_ids = [h["id"] for h in heuristics]
    state["heuristics_consulted"].extend(heuristic_ids)
    state["heuristics_consulted"] = list(set(state["heuristics_consulted"]))

    # Record consultation (for validation loop)
    if heuristic_ids:
        record_heuristics_consulted(heuristic_ids)

    # Save state
    save_session_state(state)

    # If we have learning context or complexity warning, inject it
    if heuristics or failures or complexity['level'] != 'LOW':
        learning_context = format_learning_context(heuristics, failures, domains, complexity)

        # Modify the prompt to include learning context
        original_prompt = tool_input.get("prompt", "")
        modified_prompt = original_prompt + learning_context

        modified_input = tool_input.copy()
        modified_input["prompt"] = modified_prompt

        output_result({
            "decision": "approve",
            "tool_input": modified_input
        })
    else:
        output_result({"decision": "approve"})


if __name__ == "__main__":
    main()
