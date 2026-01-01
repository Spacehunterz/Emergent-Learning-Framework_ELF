"""
Event Watcher for TalkinHead

Polls for hook events from Claude Code hooks via a JSON event file.
Uses timestamp-based deduplication to only process new events.
"""

import json
from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class EventWatcher(QObject):
    """
    Watches for events written by Claude Code hooks.

    Polls ~/.claude/ivy_events.json every 200ms and emits signals
    when new events are detected based on timestamp comparison.
    """

    # Signal emitted when a new event is detected
    # Parameters: event_type (str), message (str)
    event_triggered = pyqtSignal(str, str)

    def __init__(self, poll_interval_ms: int = 200, parent=None):
        """
        Initialize the event watcher.

        Args:
            poll_interval_ms: Polling interval in milliseconds (default 200ms)
            parent: Parent QObject
        """
        super().__init__(parent)

        # Path to the events file
        self._events_file = Path.home() / ".claude" / "ivy_events.json"

        # Track the last processed event timestamp for deduplication
        self._last_timestamp: float = 0.0

        # Setup polling timer
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self._check_events)

    def start(self) -> None:
        """Start polling for events."""
        self._timer.start()

    def stop(self) -> None:
        """Stop polling for events."""
        self._timer.stop()

    def _check_events(self) -> None:
        """
        Timer callback to check for new events.

        Reads the event file, checks if the timestamp is newer than
        the last processed event, and emits a signal if so.
        """
        # Check if file exists
        if not self._events_file.exists():
            return

        try:
            # Read and parse the event file
            content = self._events_file.read_text(encoding="utf-8")
            event_data = json.loads(content)

            # Extract fields with defaults for missing values
            timestamp = float(event_data.get("timestamp", 0.0))
            event_type = str(event_data.get("event", "unknown"))
            message = str(event_data.get("message", ""))

            # Only process if this is a newer event
            if timestamp > self._last_timestamp:
                self._last_timestamp = timestamp
                self.event_triggered.emit(event_type, message)

        except (json.JSONDecodeError, ValueError, TypeError, OSError):
            # Ignore errors:
            # - JSONDecodeError: Invalid JSON
            # - ValueError: Invalid timestamp conversion
            # - TypeError: Unexpected data types
            # - OSError: File read errors
            pass

    @property
    def is_running(self) -> bool:
        """Check if the watcher is currently polling."""
        return self._timer.isActive()

    @property
    def events_file_path(self) -> Path:
        """Get the path to the events file being watched."""
        return self._events_file


# Module-level convenience for testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    def on_event(event_type: str, message: str):
        print(f"Event received: type={event_type}, message={message}")

    watcher = EventWatcher()
    watcher.event_triggered.connect(on_event)
    watcher.start()

    print(f"Watching: {watcher.events_file_path}")
    print("Press Ctrl+C to stop...")

    sys.exit(app.exec_())
