#!/usr/bin/env python3
"""
Pre-Tool Learning Hook: Auto-inject relevant heuristics and complexity warnings before investigation.

This hook closes the learning loop by:
1. Auto-querying the building for relevant heuristics
2. Scoring task complexity and risk level
3. Injecting applicable rules and warnings into the agent's context
4. Tracking which heuristics are being consulted (for validation)

Works with: Task, Bash, Grep, Read, Glob, Edit, Write (all investigation and modification tools)

Bug fixes applied:
- Bug #82: Now processes ALL tools, not just Task
- Bug #83: Domain keywords now map directly to DB domain names (no alias expansion)
- Bug #85: Silent exception handlers now log errors
"""

import json
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Paths - resolve from repo/root detection or explicit ELF_BASE_PATH
def _resolve_base_path() -> Path:
    try:
        from elf_paths import get_base_path
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from elf_paths import get_base_path
    return get_base_path(Path(__file__))


EMERGENT_LEARNING_PATH = _resolve_base_path()
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
    # Check if this is a new session by comparing session start time
    current_session_start = datetime.now().strftime("%Y-%m-%d")

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            # Check if state is from a previous day (new session)
            if state.get("session_start", ""):
                try:
                    last_session = datetime.fromisoformat(state["session_start"])
                    if last_session.strftime("%Y-%m-%d") != current_session_start:
                        # New session - clear state
                        return {
                            "session_start": datetime.now().isoformat(),
                            "heuristics_consulted": [],
                            "domains_queried": [],
                            "task_context": None
                        }
                except (ValueError, KeyError):
                    pass
            return state
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


DOMAIN_ALIASES = {
    # Critical domains - map extraction keywords to actual DB domain names
    "architecture": ["architecture", "software-architecture", "design-patterns", "system-design", "architectural"],
    "debugging": ["debugging", "troubleshooting", "error-analysis", "debug"],
    "typescript": ["typescript", "javascript", "type-safety", "ts"],
    "api-design": ["api-design", "api-design-patterns", "endpoint-design"],
    "api-integration": ["api-integration", "webhook", "api-consumption", "third-party-integration"],
    "ui": ["ui", "frontend", "user-interface", "ui-architecture", "ui-interaction", "ui-layout", "react", "vue", "jsx", "tsx"],
    "software-architecture": ["software-architecture", "system-architecture", "architectural-design"],
    "code-quality": ["code-quality", "clean-code", "refactoring", "technical-debt"],
    "communication": ["communication", "messaging", "notifications"],
    "feature-planning": ["feature-planning", "feature-design", "requirements-analysis"],
    "problem-solving": ["problem-solving", "troubleshooting", "solution-strategy"],
    "requirements": ["requirements", "specifications", "acceptance-criteria"],
    "llm-output-processing": ["llm-output-processing", "response-parsing", "output-extraction"],
    "user-experience": ["user-experience", "ux", "usability", "user-flow"],
    "ai-models": ["ai-models", "ml-models", "machine-learning", "model-inference"],
    # Existing mappings - updated to match DB domains
    "frontend": ["ui"],  # Maps to ui domain in DB
    "javascript": ["ui", "typescript"],  # Maps to ui/typescript domains
    "database": ["database-operations", "database-optimization", "database-maintenance"],
    "api": ["api-design", "api-integration", "api-polling"],  # Maps to api-design/api-integration
    "testing": ["integration-test", "visual-testing", "mcp-testing"],
    "git": ["git-workflow"],
    "python": ["pyqt"],
    "configuration": ["configuration-management"],
    "error-handling": [],
    "security": [],
    "performance": ["caching", "react-performance"],
    "authentication": ["security"],
    "production": ["devops", "infrastructure"],
    "agent": ["agent-behavior", "agent-architecture", "agent-coordination", "multi-agent", "multi-agent-coordination"],
    "workflow": ["workflow-design", "development-workflow"],
    "windows": ["windows-compatibility", "windows-gotchas", "cross-platform"],
    "hooks": ["learning"],
    "documentation": [],
    "coordination": ["service-coordination", "multi-agent-coordination"],
    "cli": ["cli-architecture", "cli-design"],
    "file": ["file-io", "file-operations", "file-organization", "file-write-safety"],
}


def expand_domains_with_aliases(domains: List[str]) -> List[str]:
    """Expand extracted domains with their aliases for broader matching."""
    expanded = set(domains)
    for domain in domains:
        if domain in DOMAIN_ALIASES:
            expanded.update(DOMAIN_ALIASES[domain])
    return list(expanded)


def extract_domain_from_context(tool_name: str, tool_input: dict) -> List[str]:
    """Extract likely domains from the tool call context."""
    domains = []

    text = ""
    if tool_name == "Task":
        text = tool_input.get("prompt", "") + " " + tool_input.get("description", "")
    elif tool_name == "Bash":
        text = tool_input.get("command", "")
    elif tool_name in ("Grep", "Read", "Glob"):
        text = tool_input.get("pattern", "") + " " + tool_input.get("file_path", "") + " " + tool_input.get("path", "")
    elif tool_name in ("Edit", "Write"):
        # Include file path and content for Edit/Write operations
        text = tool_input.get("file_path", "") + " " + tool_input.get("old_string", "") + " " + tool_input.get("new_string", "") + " " + tool_input.get("content", "")

    text = text.lower()

    domain_keywords = {
        # Critical domains missing from original mapping
        "architecture": ["architecture", "design pattern", "system design", "pattern", "structural", "layer", "component architecture"],
        "debugging": ["debug", "troubleshoot", "fix bug", "issue", "breakpoint", "inspect", "diagnose"],
        "typescript": ["typescript", "ts", "type", "typing", "interface", "type annotation", ".ts", ".tsx"],
        "api-design": ["api design", "endpoint design", "rest design", "api contract", "api specification"],
        "api-integration": ["api integration", "api call", "fetch api", "consume api", "webhook", "third-party api"],
        "ui": ["ui", "user interface", "react", "vue", "component", "jsx", "tsx", "dom", "css", "style", "frontend"],
        "software-architecture": ["software architecture", "system architecture", "architectural", "design principle"],
        "code-quality": ["code quality", "clean code", "refactor", "code smell", "technical debt", "lint"],
        "communication": ["communicate", "message", "notify", "alert", "notification", "broadcast"],
        "feature-planning": ["feature", "planning", "plan", "requirement", "user story", "feature request"],
        "problem-solving": ["solve", "problem", "solution", "approach", "strategy"],
        "requirements": ["requirement", "spec", "specification", "acceptance criteria"],
        "llm-output-processing": ["llm output", "parse output", "process response", "extract from response"],
        "user-experience": ["ux", "user experience", "usability", "user flow", "interaction"],
        "ai-models": ["ai model", "ml model", "machine learning", "model", "inference", "training"],
        # Original domains that map to DB domains
        "authentication": ["auth", "login", "session", "jwt", "token", "oauth", "password"],
        "database": ["sql", "query", "schema", "migration", "db", "database", "sqlite", "postgres"],
        "database-migration": ["migration", "migrate", "schema change", "alter table"],
        "api": ["api", "endpoint", "rest", "graphql", "route", "controller"],
        "security": ["security", "vulnerability", "injection", "xss", "csrf", "sanitiz"],
        "testing": ["test", "spec", "coverage", "mock", "fixture", "assert"],
        "react": ["react", "usestate", "useeffect", "react component"],
        "performance": ["performance", "cache", "optimize", "memory", "speed", "optimization"],
        "error-handling": ["error", "exception", "catch", "throw", "try", "error handling"],
        "configuration": ["config", "env", "setting", "option"],
        "production": ["production", "prod", "deploy", "release"],
        "git": ["git", "commit", "branch", "merge", "rebase"],
        "python": ["python", "pip", "venv", ".py"],
        "hooks": ["hook", "pre_tool", "post_tool", "learning-loop"],
        "agent": ["agent", "subagent", "task tool", "swarm"],
        "workflow": ["workflow", "pipeline", "automation"],
        "windows": ["windows", "powershell", "cmd", "taskkill", "netstat"],
        "file": ["file", "read", "write", "path", "directory"],
        "cli": ["cli", "command", "terminal", "shell"],
        "coordination": ["coordination", "handoff", "blackboard"],
        "documentation": ["document", "readme", "claude.md"],
        "general": ["general", "misc"],
    }

    for domain, keywords in domain_keywords.items():
        if any(kw in text for kw in keywords):
            domains.append(domain)

    # Bug #83 fix: Return canonical domain names directly for database queries.
    # The domain_keywords dict already returns canonical names that match DB entries.
    # The expand_domains_with_aliases() function was adding non-existent aliases.
    return list(set(domains))[:10]


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
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to query failures: {e}\n")
        return []
    finally:
        conn.close()


def check_ceo_decisions() -> bool:
    """Check for pending CEO decisions that might block this operation."""
    ceo_inbox = EMERGENT_LEARNING_PATH / 'ceo-inbox'

    if not ceo_inbox.exists():
        return False

    pending = list(ceo_inbox.glob('*.md'))
    if pending:
        # Log the pending decision
        sys.stderr.write(f"[CEO_DECISION_BLOCKER] {len(pending)} pending CEO decisions detected:\n")
        for decision in pending[:3]:  # Show first 3
            sys.stderr.write(f"  - {decision.stem}\n")
        if len(pending) > 3:
            sys.stderr.write(f"  ... and {len(pending) - 3} more\n")

        # Block operation if there are pending CEO decisions
        return True

    return False


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

    # Enforce CEO decisions - block if there are pending decisions
    if check_ceo_decisions():
        output_result({
            "decision": "reject",
            "reason": "Operation blocked by pending CEO decisions. Please resolve pending decisions before proceeding."
        })
        return

    # Learning loop processes ALL investigation and modification tools
    # This enables learning from Grep, Read, Glob, Edit, Write, Bash operations
    INVESTIGATION_TOOLS = {"Task", "Bash", "Grep", "Read", "Glob", "Edit", "Write"}
    if tool_name not in INVESTIGATION_TOOLS:
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
