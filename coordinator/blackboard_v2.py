#!/usr/bin/env python3
"""
Blackboard V2: Dual-write adapter for safe migration to event log.

PHASE 1 (current): Write to BOTH old blackboard.json AND new event log.
                   Read from OLD blackboard.json (source of truth).

This allows:
- Zero API changes for existing code
- Validation that event log produces same state
- Rollback by just removing this adapter
- Gradual confidence building before cutover

Usage:
    # Drop-in replacement - same interface as Blackboard
    from blackboard_v2 import BlackboardV2 as Blackboard
    bb = Blackboard(project_root)
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "plugins" / "agent-coordination" / "utils"))
sys.path.insert(0, str(Path(__file__).parent))

# Import both systems
try:
    from event_log import EventLog
except ImportError:
    # Fallback: try local import
    from coordinator.event_log import EventLog

# Import original blackboard from plugins
try:
    # Try the plugins path first
    plugins_path = Path(__file__).parent.parent / "plugins" / "agent-coordination" / "utils"
    if plugins_path.exists():
        sys.path.insert(0, str(plugins_path))
    from blackboard import Blackboard as OriginalBlackboard
except ImportError:
    # Fallback: assume it's in same directory
    from blackboard import Blackboard as OriginalBlackboard


class BlackboardV2:
    """Dual-write blackboard adapter.

    Same interface as original Blackboard, but writes to both:
    1. Original blackboard.json (for backward compatibility)
    2. New event log (for validation and eventual cutover)

    Reads from original blackboard.json (Phase 1).
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()

        # Original blackboard (source of truth for reads in Phase 1)
        self.blackboard = OriginalBlackboard(project_root)

        # New event log (write-only in Phase 1)
        self.event_log = EventLog(project_root)

        # Track if event log is healthy
        self._event_log_healthy = True

    def _write_to_event_log(self, event_type: str, data: Dict) -> Optional[int]:
        """Write to event log, gracefully handling failures."""
        if not self._event_log_healthy:
            return None
        try:
            return self.event_log.append_event(event_type, data)
        except Exception as e:
            # Log but don't fail - old blackboard is still source of truth
            print(f"[BlackboardV2] Event log write failed (non-fatal): {e}")
            return None

    # =========================================================================
    # Agent Registry (dual-write)
    # =========================================================================

    def register_agent(self, agent_id: str, task: str, scope: List[str] = None,
                       interests: List[str] = None) -> Dict:
        """Register an agent - writes to both systems."""
        # Write to event log first (non-blocking)
        self._write_to_event_log("agent.registered", {
            "agent_id": agent_id,
            "task": task,
            "scope": scope or [],
            "interests": interests or []
        })

        # Write to original blackboard (source of truth)
        return self.blackboard.register_agent(agent_id, task, scope, interests)

    def update_agent_status(self, agent_id: str, status: str, result: str = None) -> bool:
        """Update agent status - writes to both systems."""
        self._write_to_event_log("agent.status_updated", {
            "agent_id": agent_id,
            "status": status,
            "result": result
        })
        return self.blackboard.update_agent_status(agent_id, status, result)

    def get_active_agents(self) -> Dict:
        """Get active agents - reads from original blackboard."""
        return self.blackboard.get_active_agents()

    def get_all_agents(self) -> Dict:
        """Get all agents - reads from original blackboard."""
        return self.blackboard.get_all_agents()

    # =========================================================================
    # Findings (dual-write)
    # =========================================================================

    def add_finding(self, agent_id: str, finding_type: str, content: str,
                    files: List[str] = None, importance: str = "normal",
                    tags: List[str] = None) -> Dict:
        """Add a finding - writes to both systems."""
        self._write_to_event_log("finding.added", {
            "agent_id": agent_id,
            "finding_type": finding_type,
            "content": content,
            "files": files or [],
            "importance": importance,
            "tags": tags or []
        })
        return self.blackboard.add_finding(agent_id, finding_type, content, files, importance, tags)

    def get_findings(self, since: str = None, finding_type: str = None,
                     importance: str = None) -> List[Dict]:
        """Get findings - reads from original blackboard."""
        return self.blackboard.get_findings(since, finding_type, importance)

    def get_findings_since_cursor(self, cursor: int) -> List[Dict]:
        """Get findings since cursor - reads from original blackboard."""
        return self.blackboard.get_findings_since_cursor(cursor)

    def get_critical_findings(self) -> List[Dict]:
        """Get critical findings - reads from original blackboard."""
        return self.blackboard.get_critical_findings()

    def get_findings_for_interests(self, interests: List[str]) -> List[Dict]:
        """Get findings matching interests - reads from original blackboard."""
        return self.blackboard.get_findings_for_interests(interests)

    def search_findings(self, query: str, limit: int = 10) -> List[Dict]:
        """Search findings - reads from original blackboard."""
        return self.blackboard.search_findings(query, limit)

    def update_agent_cursor(self, agent_id: str) -> int:
        """Update cursor - writes to both systems."""
        self._write_to_event_log("agent.cursor_updated", {
            "agent_id": agent_id
        })
        return self.blackboard.update_agent_cursor(agent_id)

    def get_agent_cursor(self, agent_id: str) -> int:
        """Get cursor - reads from original blackboard."""
        return self.blackboard.get_agent_cursor(agent_id)

    def get_agent_interests(self, agent_id: str) -> List[str]:
        """Get interests - reads from original blackboard."""
        return self.blackboard.get_agent_interests(agent_id)

    # =========================================================================
    # Messages (dual-write)
    # =========================================================================

    def send_message(self, from_agent: str, to_agent: str, content: str,
                     msg_type: str = "info") -> Dict:
        """Send message - writes to both systems."""
        self._write_to_event_log("message.sent", {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "content": content,
            "msg_type": msg_type
        })
        return self.blackboard.send_message(from_agent, to_agent, content, msg_type)

    def get_messages(self, agent_id: str, unread_only: bool = False) -> List[Dict]:
        """Get messages - reads from original blackboard."""
        return self.blackboard.get_messages(agent_id, unread_only)

    def mark_message_read(self, message_id: str) -> bool:
        """Mark read - writes to both systems."""
        self._write_to_event_log("message.read", {
            "message_id": message_id
        })
        return self.blackboard.mark_message_read(message_id)

    # =========================================================================
    # Task Queue (dual-write)
    # =========================================================================

    def add_task(self, task: str, priority: int = 5, depends_on: List[str] = None,
                 assigned_to: str = None) -> Dict:
        """Add task - writes to both systems."""
        self._write_to_event_log("task.added", {
            "task": task,
            "priority": priority,
            "depends_on": depends_on or [],
            "assigned_to": assigned_to
        })
        return self.blackboard.add_task(task, priority, depends_on, assigned_to)

    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """Claim task - writes to both systems."""
        self._write_to_event_log("task.claimed", {
            "task_id": task_id,
            "agent_id": agent_id
        })
        return self.blackboard.claim_task(task_id, agent_id)

    def complete_task(self, task_id: str, result: str = None) -> bool:
        """Complete task - writes to both systems."""
        self._write_to_event_log("task.completed", {
            "task_id": task_id,
            "result": result
        })
        return self.blackboard.complete_task(task_id, result)

    def get_pending_tasks(self) -> List[Dict]:
        """Get pending tasks - reads from original blackboard."""
        return self.blackboard.get_pending_tasks()

    # =========================================================================
    # Questions (dual-write)
    # =========================================================================

    def ask_question(self, agent_id: str, question: str, options: List[str] = None,
                     blocking: bool = True) -> Dict:
        """Ask question - writes to both systems."""
        self._write_to_event_log("question.asked", {
            "agent_id": agent_id,
            "question": question,
            "options": options,
            "blocking": blocking
        })
        return self.blackboard.ask_question(agent_id, question, options, blocking)

    def answer_question(self, question_id: str, answer: str, answered_by: str) -> bool:
        """Answer question - writes to both systems."""
        self._write_to_event_log("question.answered", {
            "question_id": question_id,
            "answer": answer,
            "answered_by": answered_by
        })
        return self.blackboard.answer_question(question_id, answer, answered_by)

    def get_open_questions(self) -> List[Dict]:
        """Get open questions - reads from original blackboard."""
        return self.blackboard.get_open_questions()

    # =========================================================================
    # Context (dual-write)
    # =========================================================================

    def set_context(self, key: str, value: Any) -> None:
        """Set context - writes to both systems."""
        self._write_to_event_log("context.set", {
            "key": key,
            "value": value
        })
        self.blackboard.set_context(key, value)

    def get_context(self, key: str = None) -> Any:
        """Get context - reads from original blackboard."""
        return self.blackboard.get_context(key)

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_full_state(self) -> Dict:
        """Get full state - reads from original blackboard."""
        return self.blackboard.get_full_state()

    def get_summary(self) -> str:
        """Get summary - reads from original blackboard."""
        return self.blackboard.get_summary()

    def reset(self) -> None:
        """Reset both systems."""
        self._write_to_event_log("system.reset", {})
        self.blackboard.reset()

    # =========================================================================
    # Validation helpers (for Phase 2)
    # =========================================================================

    def validate_state_consistency(self) -> Dict:
        """Compare state between old blackboard and new event log.

        Returns dict with:
        - consistent: bool
        - differences: list of discrepancies
        - blackboard_state: current blackboard state
        - event_log_state: current event log state
        """
        bb_state = self.blackboard.get_full_state()
        el_state = self.event_log.get_current_state()

        differences = []

        # Compare agent counts
        bb_agents = set(bb_state.get("agents", {}).keys())
        el_agents = set(el_state.get("agents", {}).keys())
        if bb_agents != el_agents:
            differences.append(f"Agent mismatch: blackboard has {bb_agents}, event_log has {el_agents}")

        # Compare finding counts
        bb_findings = len(bb_state.get("findings", []))
        el_findings = len(el_state.get("findings", []))
        if bb_findings != el_findings:
            differences.append(f"Finding count mismatch: blackboard has {bb_findings}, event_log has {el_findings}")

        # Compare question counts
        bb_questions = len(bb_state.get("questions", []))
        el_questions = len(el_state.get("questions", []))
        if bb_questions != el_questions:
            differences.append(f"Question count mismatch: blackboard has {bb_questions}, event_log has {el_questions}")

        return {
            "consistent": len(differences) == 0,
            "differences": differences,
            "blackboard_state": bb_state,
            "event_log_state": el_state
        }

    def get_event_log_stats(self) -> Dict:
        """Get event log statistics for monitoring."""
        return self.event_log.get_stats()


# CLI interface for testing
if __name__ == "__main__":
    import json

    bb = BlackboardV2()

    if len(sys.argv) < 2:
        print("BlackboardV2 - Dual-write adapter")
        print("=" * 40)
        print("\nBlackboard state:")
        print(bb.get_summary())
        print("\nEvent log stats:")
        print(json.dumps(bb.get_event_log_stats(), indent=2))
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "validate":
        result = bb.validate_state_consistency()
        print("State Validation")
        print("=" * 40)
        if result["consistent"]:
            print("CONSISTENT - Both systems match!")
        else:
            print("INCONSISTENT - Found differences:")
            for diff in result["differences"]:
                print(f"  - {diff}")
    elif cmd == "stats":
        print("Event Log Stats:")
        print(json.dumps(bb.get_event_log_stats(), indent=2))
    elif cmd == "test":
        # Quick test of dual-write
        print("Testing dual-write...")
        bb.register_agent("test-agent", "Testing dual-write", interests=["testing"])
        bb.add_finding("test-agent", "fact", "Dual-write test finding", tags=["test"])
        print("  Registered agent and added finding")

        result = bb.validate_state_consistency()
        if result["consistent"]:
            print("  PASS - Both systems consistent!")
        else:
            print("  FAIL - Systems diverged:")
            for diff in result["differences"]:
                print(f"    - {diff}")
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: validate, stats, test")
