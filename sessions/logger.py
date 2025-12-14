#!/usr/bin/env python3
"""
Session Logger Module for Emergent Learning Framework.

Provides comprehensive session logging functionality:
- Appends tool usage to JSONL files
- Format: ~/.claude/emergent-learning/sessions/logs/YYYY-MM-DD_session.jsonl
- Tracks tool invocations, observations, and decisions
- Auto-creates directories as needed
- Handles session rotation (30-day retention)

This module is designed to be non-blocking and error-tolerant.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Literal
from threading import Lock
import hashlib

# Configuration
MAX_SUMMARY_LENGTH = 500
RETENTION_DAYS = 30
LOGS_DIR = Path.home() / ".claude" / "emergent-learning" / "sessions" / "logs"
PROCESSED_FILE = Path.home() / ".claude" / "emergent-learning" / "sessions" / ".processed"


# Thread-safe file writing lock
_write_lock = Lock()


class SessionLogger:
    """
    Session logger that appends tool usage entries to JSONL files.

    Thread-safe and error-tolerant. Designed to never block or fail
    the calling code, even if logging operations encounter errors.

    Usage:
        logger = SessionLogger()
        logger.log_tool_use("Bash", {"command": "ls -la"}, {"output": "..."}, "success")
        logger.log_observation("Found 3 Python files in directory")
        logger.log_decision("Will refactor the main function first")
    """

    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize the session logger.

        Args:
            logs_dir: Custom logs directory (default: ~/.claude/emergent-learning/sessions/logs)
        """
        self.logs_dir = logs_dir or LOGS_DIR
        self._ensure_dirs()

    def _ensure_dirs(self) -> bool:
        """Ensure the logs directory exists. Returns True on success."""
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self._log_error(f"Failed to create logs directory: {e}")
            return False

    def _get_log_file(self) -> Path:
        """Get the current session log file path based on today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.logs_dir / f"{today}_session.jsonl"

    @staticmethod
    def _truncate(value: Any, max_length: int = MAX_SUMMARY_LENGTH) -> str:
        """
        Truncate a value to max_length characters.

        Handles various input types: strings, dicts, lists, etc.
        Returns a string representation truncated if necessary.
        """
        if value is None:
            return ""

        # Convert to string if not already
        if isinstance(value, dict):
            text = json.dumps(value, default=str, ensure_ascii=False)
        elif isinstance(value, (list, tuple)):
            text = json.dumps(value, default=str, ensure_ascii=False)
        else:
            text = str(value)

        if len(text) <= max_length:
            return text

        # Truncate and add ellipsis
        return text[:max_length - 3] + "..."

    @staticmethod
    def _extract_summary(data: Any, max_length: int = MAX_SUMMARY_LENGTH) -> str:
        """
        Extract a meaningful summary from tool input/output.

        Attempts to find the most relevant content:
        - For dicts: looks for 'content', 'text', 'output', 'command', etc.
        - For lists: concatenates first few items
        - For strings: truncates directly
        """
        if data is None:
            return ""

        if isinstance(data, str):
            return SessionLogger._truncate(data, max_length)

        if isinstance(data, dict):
            # Priority order for extracting summary
            priority_keys = ['content', 'text', 'output', 'result', 'command',
                           'file_path', 'pattern', 'message', 'description']

            for key in priority_keys:
                if key in data and data[key]:
                    value = data[key]
                    # Handle nested content (e.g., {"content": [{"text": "..."}]})
                    if isinstance(value, list):
                        texts = []
                        for item in value:
                            if isinstance(item, dict) and 'text' in item:
                                texts.append(item['text'])
                            elif isinstance(item, str):
                                texts.append(item)
                        if texts:
                            return SessionLogger._truncate(' '.join(texts), max_length)
                    return SessionLogger._truncate(value, max_length)

            # Fallback: serialize the whole dict
            return SessionLogger._truncate(data, max_length)

        if isinstance(data, list):
            # For lists, join first few items
            texts = [SessionLogger._truncate(item, max_length // 3) for item in data[:3]]
            return SessionLogger._truncate(' | '.join(texts), max_length)

        return SessionLogger._truncate(data, max_length)

    def _log_error(self, message: str):
        """Log an error to stderr (non-blocking)."""
        try:
            sys.stderr.write(f"[SessionLogger] ERROR: {message}\n")
        except (IOError, OSError, AttributeError):
            pass  # Truly non-blocking - stderr may be unavailable

    def _log_debug(self, message: str):
        """Log a debug message to stderr."""
        try:
            # Only log in debug mode (check env var)
            if os.environ.get('ELF_DEBUG', '').lower() in ('1', 'true', 'yes'):
                sys.stderr.write(f"[SessionLogger] DEBUG: {message}\n")
        except (IOError, OSError, AttributeError):
            pass  # Debug logging is best-effort

    def _write_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Write an entry to the current log file (thread-safe).

        Returns True on success, False on failure.

        Uses binary mode append for better atomicity. Binary writes with flush
        reduce the risk of partial writes during process crashes.
        """
        try:
            log_file = self._get_log_file()

            # Ensure directory exists
            if not self._ensure_dirs():
                return False

            # Serialize entry and ensure it ends with newline
            line = json.dumps(entry, default=str, ensure_ascii=False)
            if not line.endswith('\n'):
                line += '\n'

            # Encode to bytes for atomic binary write
            line_bytes = line.encode('utf-8')

            # Thread-safe atomic write
            with _write_lock:
                with open(log_file, 'ab') as f:
                    f.write(line_bytes)
                    f.flush()  # Force write to OS buffer

            self._log_debug(f"Logged entry: {entry.get('type')} - {entry.get('tool', 'N/A')}")
            return True

        except Exception as e:
            self._log_error(f"Failed to write entry: {e}")
            return False

    def log_tool_use(
        self,
        tool: str,
        tool_input: Any,
        tool_output: Any = None,
        outcome: Literal["success", "failure", "unknown"] = "unknown"
    ) -> bool:
        """
        Log a tool usage event.

        Args:
            tool: Name of the tool (e.g., "Bash", "Read", "Edit")
            tool_input: Input parameters passed to the tool
            tool_output: Output returned by the tool (optional)
            outcome: Result status ("success", "failure", "unknown")

        Returns:
            True if logged successfully, False otherwise
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "type": "tool_use",
            "tool": tool,
            "input_summary": self._extract_summary(tool_input),
            "output_summary": self._extract_summary(tool_output),
            "outcome": outcome
        }
        return self._write_entry(entry)

    def log_observation(self, content: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log an observation (insight or note during session).

        Args:
            content: The observation text
            context: Optional context dictionary

        Returns:
            True if logged successfully, False otherwise
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "type": "observation",
            "content": self._truncate(content),
            "context": self._extract_summary(context) if context else None
        }
        return self._write_entry(entry)

    def log_decision(self, decision: str, reasoning: Optional[str] = None) -> bool:
        """
        Log a decision made during the session.

        Args:
            decision: The decision made
            reasoning: Optional reasoning behind the decision

        Returns:
            True if logged successfully, False otherwise
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "type": "decision",
            "decision": self._truncate(decision),
            "reasoning": self._truncate(reasoning) if reasoning else None
        }
        return self._write_entry(entry)

    def log_custom(
        self,
        entry_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Log a custom entry type.

        Args:
            entry_type: Custom type name
            data: Data dictionary to log

        Returns:
            True if logged successfully, False otherwise
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "type": entry_type,
            **{k: self._truncate(v) if isinstance(v, str) else v for k, v in data.items()}
        }
        return self._write_entry(entry)


class ProcessedTracker:
    """
    Tracks which session log files have been processed.

    Maintains a JSON file with:
    - List of processed files
    - Last processed timestamp

    Used by downstream systems (e.g., learning extraction, analytics)
    to know which logs have already been analyzed.
    """

    def __init__(self, processed_file: Optional[Path] = None):
        """
        Initialize the processed tracker.

        Args:
            processed_file: Custom processed file path
        """
        self.processed_file = processed_file or PROCESSED_FILE
        self._ensure_parent()

    def _ensure_parent(self) -> bool:
        """Ensure parent directory exists."""
        try:
            self.processed_file.parent.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def load(self) -> Dict[str, Any]:
        """
        Load the processed tracking data.

        Returns:
            Dict with 'processed_files' list and 'last_processed' timestamp
        """
        try:
            if self.processed_file.exists():
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

        return {
            "processed_files": [],
            "last_processed": None
        }

    def save(self, data: Dict[str, Any]) -> bool:
        """
        Save the processed tracking data using atomic write pattern.

        Writes to temporary file first, then atomically replaces original.
        This prevents corruption if process crashes during write.

        Args:
            data: Dict with 'processed_files' and 'last_processed'

        Returns:
            True on success, False on failure
        """
        try:
            self._ensure_parent()

            # Write to temporary file first
            temp_file = self.processed_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            # Atomically replace original file
            # os.replace() is atomic on both Windows and Unix
            os.replace(temp_file, self.processed_file)
            return True

        except Exception:
            # Clean up temp file if it exists
            try:
                temp_file = self.processed_file.with_suffix('.tmp')
                if temp_file.exists():
                    temp_file.unlink()
            except (IOError, OSError, PermissionError):
                pass  # Best effort cleanup - file may be locked or missing
            return False

    def is_processed(self, filename: str) -> bool:
        """Check if a file has been processed."""
        data = self.load()
        return filename in data.get("processed_files", [])

    def mark_processed(self, filename: str) -> bool:
        """
        Mark a file as processed.

        Args:
            filename: Name of the file to mark (not full path)

        Returns:
            True on success
        """
        data = self.load()
        if filename not in data.get("processed_files", []):
            data.setdefault("processed_files", []).append(filename)
        data["last_processed"] = datetime.now().isoformat()
        return self.save(data)

    def get_unprocessed_files(self, logs_dir: Optional[Path] = None) -> list:
        """
        Get list of log files that haven't been processed yet.

        Args:
            logs_dir: Directory to scan for log files

        Returns:
            List of unprocessed file paths
        """
        logs_dir = logs_dir or LOGS_DIR
        data = self.load()
        processed = set(data.get("processed_files", []))

        unprocessed = []
        try:
            for f in logs_dir.glob("*_session.jsonl"):
                if f.name not in processed:
                    unprocessed.append(f)
        except Exception:
            pass

        return sorted(unprocessed)


class SessionRotation:
    """
    Handles session log rotation and cleanup.

    - Keeps last N days of logs (default: 30)
    - Auto-cleans old logs on startup
    - Provides methods for manual cleanup
    """

    def __init__(
        self,
        logs_dir: Optional[Path] = None,
        retention_days: int = RETENTION_DAYS
    ):
        """
        Initialize session rotation.

        Args:
            logs_dir: Directory containing log files
            retention_days: Number of days to retain logs
        """
        self.logs_dir = logs_dir or LOGS_DIR
        self.retention_days = retention_days

    def get_old_files(self) -> list:
        """
        Get list of log files older than retention period.

        Returns:
            List of Path objects for files to be cleaned
        """
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        old_files = []

        try:
            for f in self.logs_dir.glob("*_session.jsonl"):
                # Parse date from filename: YYYY-MM-DD_session.jsonl
                try:
                    date_str = f.name.split("_session.jsonl")[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < cutoff:
                        old_files.append(f)
                except (ValueError, IndexError):
                    # Skip files with invalid naming
                    continue
        except Exception:
            pass

        return old_files

    def cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up old log files.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Dict with cleanup results:
            - 'deleted': list of deleted files
            - 'errors': list of files that failed to delete
            - 'dry_run': whether this was a dry run
        """
        old_files = self.get_old_files()
        result = {
            "deleted": [],
            "errors": [],
            "dry_run": dry_run,
            "cutoff_date": (datetime.now() - timedelta(days=self.retention_days)).isoformat()
        }

        for f in old_files:
            if dry_run:
                result["deleted"].append(str(f))
            else:
                try:
                    f.unlink()
                    result["deleted"].append(str(f))
                except Exception as e:
                    result["errors"].append({
                        "file": str(f),
                        "error": str(e)
                    })

        return result

    def run_startup_cleanup(self) -> Dict[str, Any]:
        """
        Run cleanup on startup.

        This should be called when the session logger is first initialized.
        It cleans up old logs and returns the result.

        Returns:
            Cleanup result dict
        """
        return self.cleanup(dry_run=False)


def get_logger() -> SessionLogger:
    """
    Get a singleton-like session logger instance.

    Returns:
        SessionLogger instance
    """
    return SessionLogger()


def get_tracker() -> ProcessedTracker:
    """
    Get a processed tracker instance.

    Returns:
        ProcessedTracker instance
    """
    return ProcessedTracker()


def get_rotation() -> SessionRotation:
    """
    Get a session rotation instance.

    Returns:
        SessionRotation instance
    """
    return SessionRotation()


def run_startup():
    """
    Run startup tasks:
    - Create directories
    - Clean old logs

    Call this when the system starts.
    """
    # Ensure directories exist
    logger = get_logger()

    # Clean old logs
    rotation = get_rotation()
    result = rotation.run_startup_cleanup()

    if result["deleted"]:
        sys.stderr.write(
            f"[SessionLogger] Cleaned up {len(result['deleted'])} old log files\n"
        )

    return result


# Run startup on module import (non-blocking)
try:
    _startup_result = run_startup()
except Exception as e:
    sys.stderr.write(f"[SessionLogger] Startup warning: {e}\n")


if __name__ == "__main__":
    # Demo/test when run directly
    import argparse

    parser = argparse.ArgumentParser(description="Session Logger for ELF")
    parser.add_argument("--test", action="store_true", help="Run test logging")
    parser.add_argument("--cleanup", action="store_true", help="Run cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for cleanup")
    parser.add_argument("--unprocessed", action="store_true", help="List unprocessed files")
    args = parser.parse_args()

    if args.cleanup:
        rotation = get_rotation()
        result = rotation.cleanup(dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.unprocessed:
        tracker = get_tracker()
        files = tracker.get_unprocessed_files()
        for f in files:
            print(f)

    elif args.test:
        logger = get_logger()

        # Test tool use
        logger.log_tool_use(
            tool="Bash",
            tool_input={"command": "ls -la /tmp"},
            tool_output={"content": "total 1024\ndrwxr-xr-x 2 user user 4096 Dec 11 10:00 ."},
            outcome="success"
        )

        # Test observation
        logger.log_observation(
            "Found 3 Python files that need refactoring",
            context={"files": ["a.py", "b.py", "c.py"]}
        )

        # Test decision
        logger.log_decision(
            "Will refactor a.py first due to highest complexity",
            reasoning="Complexity score: 0.85, other files < 0.5"
        )

        print(f"Test entries written to: {logger._get_log_file()}")

    else:
        parser.print_help()
