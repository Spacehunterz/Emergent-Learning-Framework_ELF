#!/usr/bin/env python3
"""
Session Integration Module for Emergent Learning Framework

Extends the QuerySystem with:
1. Session context loading (from previous session logs)
2. Pending proposals display (from Opus learning extractor)
3. Trigger Opus extractor when unprocessed logs exist
4. Session log search capability

This module is designed to be imported by query.py or used standalone.
"""

import json
import os
import subprocess
import sys
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import re

# Windows-compatible file locking
try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import fcntl
    WINDOWS = False

# Paths
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
SESSIONS_PATH = EMERGENT_LEARNING_PATH / "sessions"
LOGS_PATH = SESSIONS_PATH / "logs"
PROCESSED_MARKER = SESSIONS_PATH / ".processed"
PROCESSED_MARKER_LOCK = SESSIONS_PATH / ".processed.lock"
PROPOSALS_PATH = EMERGENT_LEARNING_PATH / "proposals"
PENDING_PROPOSALS_PATH = PROPOSALS_PATH / "pending"


class SessionIntegration:
    """
    Handles session log integration for check-in context.

    Responsibilities:
    - Detect unprocessed session logs
    - Trigger Opus learning extractor (async)
    - Load session context for check-in
    - Load pending proposals
    - Provide session search capability
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._ensure_directories()

    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[SESSION_DEBUG] {message}", file=sys.stderr)

    def _ensure_directories(self):
        """Ensure required directories exist."""
        for path in [SESSIONS_PATH, LOGS_PATH, PROPOSALS_PATH, PENDING_PROPOSALS_PATH]:
            path.mkdir(parents=True, exist_ok=True)

    def _get_marker_lock(self, timeout: float = 10.0) -> Optional[Any]:
        """Acquire lock for processed marker file. Returns file handle or None."""
        PROCESSED_MARKER_LOCK.parent.mkdir(parents=True, exist_ok=True)
        start = time.time()
        handle = None

        while time.time() - start < timeout:
            try:
                # Create/open lock file
                if WINDOWS:
                    handle = open(PROCESSED_MARKER_LOCK, 'w')
                    # Lock 1024 bytes for better protection against race conditions
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1024)
                    return handle
                else:
                    handle = open(PROCESSED_MARKER_LOCK, 'w')
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
                time.sleep(0.1)

        # Timeout - ensure handle is closed if we somehow still have one
        if handle is not None:
            try:
                handle.close()
            except (IOError, OSError):
                pass
        return None  # Timeout

    def _release_marker_lock(self, handle):
        """Release processed marker lock."""
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

    def _write_marker_atomic(self, data: Dict):
        """Write processed marker atomically using temp file + rename.

        This prevents corruption if process crashes mid-write.
        Uses os.replace() which is atomic on both Unix and Windows.
        """
        SESSIONS_PATH.mkdir(parents=True, exist_ok=True)

        # Write to temp file in same directory (ensures same filesystem)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=SESSIONS_PATH,
            prefix='.processed_',
            suffix='.tmp'
        )

        try:
            # Write JSON to temp file
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Atomic replace (works on both Unix and Windows)
            os.replace(temp_path, PROCESSED_MARKER)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def get_processed_files(self) -> List[str]:
        """Get list of already processed session log files."""
        if not PROCESSED_MARKER.exists():
            return []
        try:
            data = json.loads(PROCESSED_MARKER.read_text(encoding='utf-8'))
            return data.get('processed_files', [])
        except (json.JSONDecodeError, IOError):
            return []

    def get_unprocessed_logs(self) -> List[Path]:
        """Get list of session log files that haven't been processed yet."""
        if not LOGS_PATH.exists():
            return []

        processed = set(self.get_processed_files())
        unprocessed = []

        for log_file in LOGS_PATH.glob("*.jsonl"):
            if log_file.name not in processed:
                # Don't process today's log (still being written to)
                today = datetime.now().strftime("%Y-%m-%d")
                if not log_file.name.startswith(today):
                    unprocessed.append(log_file)

        self._log_debug(f"Found {len(unprocessed)} unprocessed log files")
        return sorted(unprocessed)

    def mark_as_processed(self, log_files: List[Path]):
        """Mark log files as processed (thread-safe with file locking)."""
        lock = self._get_marker_lock()
        if lock is None:
            raise TimeoutError("Could not acquire processed marker lock after 10 seconds")

        try:
            # Read current state inside lock
            processed = self.get_processed_files()

            # Add new files
            for f in log_files:
                if f.name not in processed:
                    processed.append(f.name)

            # Prepare data
            data = {
                'processed_files': processed,
                'last_processed': datetime.now().isoformat()
            }

            # Atomic write
            self._write_marker_atomic(data)
            self._log_debug(f"Marked {len(log_files)} files as processed")
        finally:
            self._release_marker_lock(lock)

    def trigger_learning_extractor(self, log_files: List[Path]) -> bool:
        """
        Trigger the Opus learning extractor agent in background.

        Args:
            log_files: List of log files to process

        Returns:
            True if extractor was triggered, False otherwise
        """
        extractor_script = EMERGENT_LEARNING_PATH / "agents" / "learning-extractor" / "run_extractor.py"

        if not extractor_script.exists():
            self._log_debug(f"Learning extractor not found at {extractor_script}")
            return False

        try:
            # Run in background (non-blocking)
            log_paths = [str(f) for f in log_files]
            cmd = [sys.executable, str(extractor_script)] + log_paths

            # Use subprocess.Popen for non-blocking execution
            if sys.platform == 'win32':
                # Windows: use CREATE_NEW_PROCESS_GROUP
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: use nohup-style
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

            self._log_debug(f"Triggered learning extractor for {len(log_files)} files")
            return True

        except Exception as e:
            self._log_debug(f"Failed to trigger learning extractor: {e}")
            return False

    def get_session_context(self, days: int = 1, max_entries: int = 10) -> Optional[str]:
        """
        Get context from recent session logs.

        Args:
            days: How many days back to look
            max_entries: Maximum number of entries to include

        Returns:
            Formatted session context string, or None if no recent sessions
        """
        if not LOGS_PATH.exists():
            return None

        cutoff = datetime.now() - timedelta(days=days)
        entries = []

        # Read recent log files
        for log_file in sorted(LOGS_PATH.glob("*.jsonl"), reverse=True):
            # Parse date from filename (YYYY-MM-DD_session.jsonl)
            try:
                date_str = log_file.stem.split('_')[0]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    continue
            except (ValueError, IndexError):
                continue

            # Read entries from file
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            except IOError:
                continue

        if not entries:
            return None

        # Sort by timestamp and take most recent
        entries.sort(key=lambda x: x.get('ts', ''), reverse=True)
        entries = entries[:max_entries]

        # Format output
        lines = ["## Recent Session Activity\n"]

        # Group by outcome for summary
        outcomes = {'success': 0, 'failure': 0, 'unknown': 0}
        tools_used = set()

        for entry in entries:
            outcome = entry.get('outcome', 'unknown')
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            tools_used.add(entry.get('tool', 'unknown'))

            # Format entry
            ts = entry.get('ts', '')[:16]  # Trim to minute precision
            tool = entry.get('tool', 'unknown')
            input_summary = entry.get('input_summary', '')[:80]
            outcome_marker = {'success': '+', 'failure': '!', 'unknown': '?'}.get(outcome, '?')

            lines.append(f"[{ts}] [{outcome_marker}] {tool}: {input_summary}")

        # Add summary
        lines.insert(1, f"Tools: {', '.join(sorted(tools_used))}")
        lines.insert(2, f"Outcomes: {outcomes['success']} success, {outcomes['failure']} failure, {outcomes['unknown']} unknown\n")

        return "\n".join(lines)

    def get_pending_proposals(self) -> List[Dict]:
        """
        Get pending proposals awaiting review.

        Returns:
            List of proposal dictionaries with title, type, confidence, summary
        """
        if not PENDING_PROPOSALS_PATH.exists():
            return []

        proposals = []

        for proposal_file in PENDING_PROPOSALS_PATH.glob("*.md"):
            try:
                content = proposal_file.read_text(encoding='utf-8')
                proposal = self._parse_proposal(content, proposal_file.name)
                if proposal:
                    proposals.append(proposal)
            except IOError:
                continue

        # Sort by confidence (highest first)
        proposals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return proposals

    def _parse_proposal(self, content: str, filename: str) -> Optional[Dict]:
        """Parse a proposal markdown file into a dictionary."""
        proposal = {'filename': filename}

        # Extract title
        title_match = re.search(r'^# Proposal: (.+)$', content, re.MULTILINE)
        if title_match:
            proposal['title'] = title_match.group(1).strip()
        else:
            proposal['title'] = filename

        # Extract type
        type_match = re.search(r'\*\*Type:\*\* (.+)$', content, re.MULTILINE)
        if type_match:
            proposal['type'] = type_match.group(1).strip()

        # Extract confidence
        conf_match = re.search(r'\*\*Confidence:\*\* ([\d.]+)', content)
        if conf_match:
            try:
                proposal['confidence'] = float(conf_match.group(1))
            except ValueError:
                proposal['confidence'] = 0.5

        # Extract domain
        domain_match = re.search(r'\*\*Domain:\*\* (.+)$', content, re.MULTILINE)
        if domain_match:
            proposal['domain'] = domain_match.group(1).strip()

        # Extract summary
        summary_match = re.search(r'## Summary\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if summary_match:
            proposal['summary'] = summary_match.group(1).strip()[:200]

        return proposal if 'title' in proposal else None

    def format_proposals_for_checkin(self, proposals: List[Dict]) -> str:
        """Format proposals for check-in display."""
        if not proposals:
            return ""

        lines = ["\n# Pending Proposals (Opus Learning Extractor)\n"]
        lines.append(f"_{len(proposals)} proposal(s) awaiting review_\n")

        for p in proposals[:5]:  # Max 5 in check-in
            conf = p.get('confidence', 0)
            conf_bar = '*' * int(conf * 5)  # Visual confidence indicator

            lines.append(f"- **{p['title']}** [{p.get('type', 'unknown')}]")
            lines.append(f"  Confidence: {conf:.1%} {conf_bar}")
            if p.get('summary'):
                lines.append(f"  {p['summary'][:100]}...")
            lines.append("")

        if len(proposals) > 5:
            lines.append(f"_...and {len(proposals) - 5} more_\n")

        lines.append("Run `review-proposals` to approve/reject\n")
        return "\n".join(lines)

    def build_session_checkin_context(self) -> Tuple[str, bool]:
        """
        Build the session-related context for check-in.

        Returns:
            Tuple of (context_string, extractor_triggered)
        """
        context_parts = []
        extractor_triggered = False

        # Check for unprocessed logs and trigger extractor
        unprocessed = self.get_unprocessed_logs()
        if unprocessed:
            context_parts.append(f"\n## Session Logs Pending Analysis")
            context_parts.append(f"_{len(unprocessed)} session log(s) from previous sessions await Opus analysis_\n")

            # Trigger extractor in background
            if self.trigger_learning_extractor(unprocessed):
                context_parts.append("*Opus Learning Extractor launched in background...*\n")
                extractor_triggered = True
            else:
                context_parts.append("*Learning extractor not available - logs will be processed next time*\n")

        # Get session context from recent logs
        session_context = self.get_session_context(days=1, max_entries=10)
        if session_context:
            context_parts.append(session_context)

        # Get pending proposals
        proposals = self.get_pending_proposals()
        if proposals:
            context_parts.append(self.format_proposals_for_checkin(proposals))

        return "\n".join(context_parts), extractor_triggered


def extend_query_system_build_context():
    """
    Returns code snippet to add to QuerySystem.build_context() method.

    Add this after the CEO reviews section:

    ```python
    # Session integration (NEW)
    from query.session_integration import SessionIntegration
    session_int = SessionIntegration(debug=self.debug)
    session_context, _ = session_int.build_session_checkin_context()
    if session_context:
        context_parts.append(session_context)
    ```
    """
    pass


if __name__ == "__main__":
    # Test the integration
    integration = SessionIntegration(debug=True)

    print("=== Unprocessed Logs ===")
    for log in integration.get_unprocessed_logs():
        print(f"  {log}")

    print("\n=== Session Context ===")
    ctx = integration.get_session_context()
    print(ctx or "No recent session context")

    print("\n=== Pending Proposals ===")
    for p in integration.get_pending_proposals():
        print(f"  {p['title']} ({p.get('type', 'unknown')})")

    print("\n=== Full Check-in Context ===")
    full_ctx, triggered = integration.build_session_checkin_context()
    print(full_ctx or "No session context to add")
    print(f"\nExtractor triggered: {triggered}")
