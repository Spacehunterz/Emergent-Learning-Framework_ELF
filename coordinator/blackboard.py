#!/usr/bin/env python3
"""
Blackboard: File-based shared state for multi-agent coordination.

Thread-safe operations on .coordination/blackboard.json for:
- Agent registry (who's working on what)
- Findings (discoveries agents want to share)
- Messages (agent-to-agent communication)
- Task queue (pending work items)
- Questions (blockers needing resolution)

NOTE: For semantic search, use Basic Memory MCP tools instead:
- mcp__basic-memory__search_notes() for semantic/embedding search
- mcp__basic-memory__write_note() to persist findings

This blackboard handles REAL-TIME COORDINATION only:
- Who's working right now
- Delta tracking (what's new since last check)
- Task claiming (atomic operations)
- Question/answer protocol
"""

import json
import os
import time
import random
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime

# Windows-compatible file locking
try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import fcntl
    WINDOWS = False


class Blackboard:
    """File-based shared state with thread-safe operations.

    For semantic search, agents should use Basic Memory MCP tools directly.
    This class handles real-time coordination state only.
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.coordination_dir = self.project_root / ".coordination"
        self.blackboard_file = self.coordination_dir / "blackboard.json"
        self.lock_file = self.coordination_dir / ".blackboard.lock"

    def _ensure_dir(self):
        """Create coordination directory if it doesn't exist."""
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

    def _get_lock(self, timeout: float = 30.0) -> Optional[Any]:
        """Acquire file lock with timeout. Returns file handle or None."""
        self._ensure_dir()
        start = time.time()
        handle = None

        while time.time() - start < timeout:
            try:
                # Create/open lock file
                if WINDOWS:
                    handle = open(self.lock_file, 'w')
                    # Lock 1024 bytes for better protection against race conditions
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1024)
                    return handle
                else:
                    handle = open(self.lock_file, 'w')
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return handle
            except (IOError, OSError):
                # Lock held by another process - close handle before retry to prevent leak
                if handle is not None:
                    try:
                        handle.close()
                    except (IOError, OSError):
                        pass
                    handle = None
                time.sleep(0.1 + random.uniform(0, 0.1))

        # Timeout - ensure handle is closed if we somehow still have one
        if handle is not None:
            try:
                handle.close()
            except (IOError, OSError):
                pass
        return None  # Timeout

    def _release_lock(self, handle):
        """Release file lock."""
        if handle:
            try:
                if WINDOWS:
                    # Must unlock same number of bytes that were locked
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1024)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError, ValueError):
                # IOError/OSError: lock already released or file issue
                # ValueError: file already closed (fileno() fails)
                pass
            finally:
                try:
                    handle.close()
                except (IOError, OSError):
                    pass

    def _read_state(self) -> Dict:
        """Read current blackboard state."""
        if not self.blackboard_file.exists():
            return self._default_state()
        try:
            with open(self.blackboard_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._default_state()

    def _write_state(self, state: Dict):
        """Write blackboard state."""
        self._ensure_dir()
        with open(self.blackboard_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str)

    def _default_state(self) -> Dict:
        """Return default empty blackboard state."""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agents": {},
            "findings": [],
            "messages": [],
            "task_queue": [],
            "questions": [],
            "context": {}
        }

    def _with_lock(self, operation):
        """Execute operation with file lock."""
        lock = self._get_lock()
        if lock is None:
            raise TimeoutError("Could not acquire blackboard lock after 30 seconds")
        try:
            return operation()
        finally:
            self._release_lock(lock)

    # =========================================================================
    # Agent Registry
    # =========================================================================

    def register_agent(self, agent_id: str, task: str, scope: List[str] = None,
                       interests: List[str] = None) -> Dict:
        """Register an agent as working on a task.

        Args:
            agent_id: Unique identifier for the agent
            task: Description of what the agent is working on
            scope: List of file patterns this agent owns (e.g., ["src/auth/*"])
            interests: List of topic tags this agent cares about (e.g., ["auth", "security"])
        """
        def op():
            state = self._read_state()
            state["agents"][agent_id] = {
                "task": task,
                "scope": scope or [],
                "interests": interests or [],  # Topics this agent cares about
                "status": "active",
                "started_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "context_cursor": len(state.get("findings", []))  # Track last seen finding
            }
            state["updated_at"] = datetime.now().isoformat()
            self._write_state(state)
            return state["agents"][agent_id]
        return self._with_lock(op)

    def update_agent_status(self, agent_id: str, status: str, result: str = None) -> bool:
        """Update agent status (active, completed, failed, blocked)."""
        def op():
            state = self._read_state()
            if agent_id in state["agents"]:
                state["agents"][agent_id]["status"] = status
                state["agents"][agent_id]["last_seen"] = datetime.now().isoformat()
                if result:
                    state["agents"][agent_id]["result"] = result
                if status in ("completed", "failed"):
                    state["agents"][agent_id]["finished_at"] = datetime.now().isoformat()
                state["updated_at"] = datetime.now().isoformat()
                self._write_state(state)
                return True
            return False
        return self._with_lock(op)

    def get_active_agents(self) -> Dict:
        """Get all active agents."""
        state = self._read_state()
        return {k: v for k, v in state["agents"].items() if v["status"] == "active"}

    def get_all_agents(self) -> Dict:
        """Get all agents (any status)."""
        state = self._read_state()
        return state.get("agents", {})

    # =========================================================================
    # Findings
    # =========================================================================

    def add_finding(self, agent_id: str, finding_type: str, content: str,
                    files: List[str] = None, importance: str = "normal",
                    tags: List[str] = None) -> Dict:
        """Add a finding to share with other agents.

        Args:
            agent_id: ID of the agent reporting this finding
            finding_type: Type of finding (discovery, warning, decision, blocker, fact, hypothesis)
            content: The finding content
            files: Related file paths
            importance: low, normal, high, critical
            tags: Topic tags for filtering (e.g., ["auth", "jwt", "security"])

        NOTE: For semantic search, agents should also write findings to Basic Memory
        using mcp__basic-memory__write_note() for persistence and embedding search.
        """
        def op():
            state = self._read_state()
            finding = {
                "id": f"finding-{len(state['findings']) + 1}",
                "agent_id": agent_id,
                "type": finding_type,  # discovery, warning, decision, blocker, fact, hypothesis
                "content": content,
                "files": files or [],
                "importance": importance,  # low, normal, high, critical
                "tags": tags or [],  # Topic tags for filtering
                "timestamp": datetime.now().isoformat()
            }
            state["findings"].append(finding)
            state["updated_at"] = datetime.now().isoformat()
            self._write_state(state)
            return finding

        return self._with_lock(op)

    def get_findings(self, since: str = None, finding_type: str = None,
                     importance: str = None) -> List[Dict]:
        """Get findings, optionally filtered."""
        state = self._read_state()
        findings = state.get("findings", [])

        if since:
            findings = [f for f in findings if f["timestamp"] > since]
        if finding_type:
            findings = [f for f in findings if f["type"] == finding_type]
        if importance:
            findings = [f for f in findings if f["importance"] == importance]

        return findings

    def get_findings_since_cursor(self, cursor: int) -> List[Dict]:
        """Get findings added after a specific cursor position.

        This enables delta notifications - agents only see what's new
        since they last checked.
        """
        state = self._read_state()
        findings = state.get("findings", [])
        return findings[cursor:] if cursor < len(findings) else []

    def get_critical_findings(self) -> List[Dict]:
        """Get all critical/blocker findings that haven't been resolved."""
        state = self._read_state()
        findings = state.get("findings", [])
        return [
            f for f in findings
            if f.get("importance") == "critical" or f.get("type") == "blocker"
        ]

    def get_findings_for_interests(self, interests: List[str]) -> List[Dict]:
        """Get findings matching agent interests.

        Matches findings where:
        - Any tag matches an interest
        - The content contains an interest keyword
        """
        if not interests:
            return []

        state = self._read_state()
        findings = state.get("findings", [])
        interests_lower = [i.lower() for i in interests]

        relevant = []
        for f in findings:
            finding_tags = set(t.lower() for t in f.get("tags", []))
            content_lower = f.get("content", "").lower()

            for interest in interests_lower:
                if interest in finding_tags or interest in content_lower:
                    relevant.append(f)
                    break

        return relevant

    def search_findings(self, query: str, limit: int = 10) -> List[Dict]:
        """Simple substring search on findings.

        NOTE: For semantic search (finding related concepts), use Basic Memory:
        mcp__basic-memory__search_notes(query, project="coordination")

        This method only does basic keyword matching on content and tags.
        """
        state = self._read_state()
        findings = state.get("findings", [])
        query_lower = query.lower()

        matches = []
        for f in findings:
            content = f.get("content", "").lower()
            tags = " ".join(f.get("tags", [])).lower()
            if query_lower in content or query_lower in tags:
                matches.append(f)
                if len(matches) >= limit:
                    break

        return matches

    def update_agent_cursor(self, agent_id: str) -> int:
        """Update agent's cursor to current position. Returns new cursor.

        Call this after injecting context to mark what the agent has seen.
        """
        def op():
            state = self._read_state()
            if agent_id in state["agents"]:
                new_cursor = len(state.get("findings", []))
                state["agents"][agent_id]["context_cursor"] = new_cursor
                state["agents"][agent_id]["last_seen"] = datetime.now().isoformat()
                self._write_state(state)
                return new_cursor
            return 0
        return self._with_lock(op)

    def get_agent_cursor(self, agent_id: str) -> int:
        """Get the cursor position for an agent."""
        state = self._read_state()
        agent = state.get("agents", {}).get(agent_id, {})
        return agent.get("context_cursor", 0)

    def get_agent_interests(self, agent_id: str) -> List[str]:
        """Get the interest tags for an agent."""
        state = self._read_state()
        agent = state.get("agents", {}).get(agent_id, {})
        return agent.get("interests", [])

    # =========================================================================
    # Messages
    # =========================================================================

    def send_message(self, from_agent: str, to_agent: str, content: str,
                     msg_type: str = "info") -> Dict:
        """Send a message to another agent."""
        def op():
            state = self._read_state()
            message = {
                "id": f"msg-{len(state['messages']) + 1}",
                "from": from_agent,
                "to": to_agent,  # Use "*" for broadcast
                "type": msg_type,  # info, question, warning, handoff
                "content": content,
                "read": False,
                "timestamp": datetime.now().isoformat()
            }
            state["messages"].append(message)
            state["updated_at"] = datetime.now().isoformat()
            self._write_state(state)
            return message
        return self._with_lock(op)

    def get_messages(self, agent_id: str, unread_only: bool = False) -> List[Dict]:
        """Get messages for an agent (including broadcasts)."""
        state = self._read_state()
        messages = state.get("messages", [])

        result = [m for m in messages if m["to"] in (agent_id, "*")]
        if unread_only:
            result = [m for m in result if not m["read"]]

        return result

    def mark_message_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        def op():
            state = self._read_state()
            for msg in state["messages"]:
                if msg["id"] == message_id:
                    msg["read"] = True
                    state["updated_at"] = datetime.now().isoformat()
                    self._write_state(state)
                    return True
            return False
        return self._with_lock(op)

    # =========================================================================
    # Task Queue
    # =========================================================================

    def add_task(self, task: str, priority: int = 5, depends_on: List[str] = None,
                 assigned_to: str = None) -> Dict:
        """Add a task to the queue."""
        def op():
            state = self._read_state()
            task_item = {
                "id": f"task-{len(state['task_queue']) + 1}",
                "task": task,
                "priority": priority,  # 1 (highest) to 10 (lowest)
                "depends_on": depends_on or [],
                "assigned_to": assigned_to,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
            state["task_queue"].append(task_item)
            state["updated_at"] = datetime.now().isoformat()
            self._write_state(state)
            return task_item
        return self._with_lock(op)

    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """Claim a task for an agent."""
        def op():
            state = self._read_state()
            for task in state["task_queue"]:
                if task["id"] == task_id and task["status"] == "pending":
                    task["assigned_to"] = agent_id
                    task["status"] = "in_progress"
                    task["claimed_at"] = datetime.now().isoformat()
                    state["updated_at"] = datetime.now().isoformat()
                    self._write_state(state)
                    return True
            return False
        return self._with_lock(op)

    def complete_task(self, task_id: str, result: str = None) -> bool:
        """Mark a task as completed."""
        def op():
            state = self._read_state()
            for task in state["task_queue"]:
                if task["id"] == task_id:
                    task["status"] = "completed"
                    task["result"] = result
                    task["completed_at"] = datetime.now().isoformat()
                    state["updated_at"] = datetime.now().isoformat()
                    self._write_state(state)
                    return True
            return False
        return self._with_lock(op)

    def get_pending_tasks(self) -> List[Dict]:
        """Get all pending tasks sorted by priority."""
        state = self._read_state()
        pending = [t for t in state.get("task_queue", []) if t["status"] == "pending"]
        return sorted(pending, key=lambda t: t["priority"])

    # =========================================================================
    # Questions (Blockers)
    # =========================================================================

    def ask_question(self, agent_id: str, question: str, options: List[str] = None,
                     blocking: bool = True) -> Dict:
        """Ask a question (potentially blocking other agents)."""
        def op():
            state = self._read_state()
            q = {
                "id": f"q-{len(state['questions']) + 1}",
                "agent_id": agent_id,
                "question": question,
                "options": options,
                "blocking": blocking,
                "status": "open",
                "answer": None,
                "answered_by": None,
                "created_at": datetime.now().isoformat()
            }
            state["questions"].append(q)
            state["updated_at"] = datetime.now().isoformat()
            self._write_state(state)
            return q
        return self._with_lock(op)

    def answer_question(self, question_id: str, answer: str, answered_by: str) -> bool:
        """Answer a question."""
        def op():
            state = self._read_state()
            for q in state["questions"]:
                if q["id"] == question_id and q["status"] == "open":
                    q["answer"] = answer
                    q["answered_by"] = answered_by
                    q["status"] = "resolved"
                    q["answered_at"] = datetime.now().isoformat()
                    state["updated_at"] = datetime.now().isoformat()
                    self._write_state(state)
                    return True
            return False
        return self._with_lock(op)

    def get_open_questions(self) -> List[Dict]:
        """Get all open questions."""
        state = self._read_state()
        return [q for q in state.get("questions", []) if q["status"] == "open"]

    # =========================================================================
    # Context (Shared Key-Value Store)
    # =========================================================================

    def set_context(self, key: str, value: Any) -> None:
        """Set a shared context value."""
        def op():
            state = self._read_state()
            state["context"][key] = {
                "value": value,
                "updated_at": datetime.now().isoformat()
            }
            state["updated_at"] = datetime.now().isoformat()
            self._write_state(state)
        self._with_lock(op)

    def get_context(self, key: str = None) -> Any:
        """Get context value(s)."""
        state = self._read_state()
        if key:
            return state.get("context", {}).get(key, {}).get("value")
        return {k: v["value"] for k, v in state.get("context", {}).items()}

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_full_state(self) -> Dict:
        """Get complete blackboard state."""
        return self._read_state()

    def get_summary(self) -> str:
        """Get human-readable summary of blackboard state."""
        state = self._read_state()

        active_agents = [a for a in state["agents"].values() if a["status"] == "active"]
        pending_tasks = [t for t in state["task_queue"] if t["status"] == "pending"]
        open_questions = [q for q in state["questions"] if q["status"] == "open"]
        recent_findings = state["findings"][-5:] if state["findings"] else []

        lines = [
            "## Blackboard Summary",
            "",
            f"**Active Agents:** {len(active_agents)}",
        ]

        for agent_id, info in state["agents"].items():
            if info["status"] == "active":
                lines.append(f"  - {agent_id}: {info['task']}")

        lines.append(f"\n**Pending Tasks:** {len(pending_tasks)}")
        for task in pending_tasks[:3]:
            lines.append(f"  - [{task['priority']}] {task['task']}")

        if open_questions:
            lines.append(f"\n**Open Questions:** {len(open_questions)}")
            for q in open_questions:
                lines.append(f"  - {q['agent_id']}: {q['question']}")

        if recent_findings:
            lines.append(f"\n**Recent Findings:** {len(state['findings'])} total")
            for f in recent_findings:
                lines.append(f"  - [{f['type']}] {f['content'][:50]}...")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset blackboard to empty state."""
        def op():
            self._write_state(self._default_state())
        self._with_lock(op)


# CLI interface for testing
if __name__ == "__main__":
    import sys

    bb = Blackboard()

    if len(sys.argv) < 2:
        print(bb.get_summary())
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "summary":
        print(bb.get_summary())
    elif cmd == "state":
        print(json.dumps(bb.get_full_state(), indent=2))
    elif cmd == "reset":
        bb.reset()
        print("Blackboard reset.")
    elif cmd == "register" and len(sys.argv) >= 4:
        # register <id> <task> [interests...]
        interests = sys.argv[4:] if len(sys.argv) > 4 else []
        result = bb.register_agent(sys.argv[2], sys.argv[3], interests=interests)
        print(f"Registered: {result}")
    elif cmd == "finding" and len(sys.argv) >= 5:
        # finding <agent> <type> <content> [tags...]
        tags = sys.argv[5:] if len(sys.argv) > 5 else []
        result = bb.add_finding(sys.argv[2], sys.argv[3], sys.argv[4], tags=tags)
        print(f"Added: {result}")
    elif cmd == "search" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        results = bb.search_findings(query)
        if results:
            print(f"Found {len(results)} results (keyword match):")
            for r in results:
                tags = f" [{', '.join(r.get('tags', []))}]" if r.get('tags') else ""
                print(f"  - [{r.get('type', 'note')}]{tags} {r.get('content', '')[:60]}")
            print("\nNOTE: For semantic search, use Basic Memory:")
            print("  mcp__basic-memory__search_notes(query, project='coordination')")
        else:
            print("No keyword matches found.")
            print("\nTry semantic search via Basic Memory for related concepts.")
    elif cmd == "delta" and len(sys.argv) >= 3:
        agent_id = sys.argv[2]
        cursor = bb.get_agent_cursor(agent_id)
        new_findings = bb.get_findings_since_cursor(cursor)
        print(f"Agent {agent_id} cursor: {cursor}")
        if new_findings:
            print(f"New findings since cursor ({len(new_findings)}):")
            for f in new_findings:
                print(f"  - [{f.get('type')}] {f.get('content', '')[:60]}")
        else:
            print("No new findings.")
    else:
        print("""Usage: blackboard.py <command> [args]

Commands:
  summary                       Show blackboard summary
  state                         Show full JSON state
  reset                         Clear blackboard
  register <id> <task> [tags]   Register agent with optional interest tags
  finding <agent> <type> <msg> [tags]  Add finding with optional tags
  search <query>                Simple keyword search (for semantic search, use Basic Memory)
  delta <agent_id>              Show new findings since agent's cursor

For semantic search with embeddings, use Basic Memory MCP:
  mcp__basic-memory__search_notes(query, project="coordination")
""")
