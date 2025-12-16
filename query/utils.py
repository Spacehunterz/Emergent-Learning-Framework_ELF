"""
Utility functions and classes for the Query System.

Contains:
- TimeoutHandler: Context manager for query timeout enforcement
- escape_like: SQL LIKE wildcard escaping
- Windows console encoding fix
- Time utilities
"""

import sys
import io
import signal
import atexit
from datetime import datetime

# Import TimeoutError with fallback for script execution
try:
    from .exceptions import TimeoutError
except ImportError:
    from exceptions import TimeoutError


# Fix Windows console encoding for Unicode characters
def setup_windows_console():
    """
    Configure Windows console for UTF-8 output.

    This wraps stdout/stderr with UTF-8 encoding and registers
    cleanup handlers to restore original streams on exit.
    """
    if sys.platform != 'win32':
        return

    _original_stdout = sys.stdout
    _original_stderr = sys.stderr

    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )

    def _restore_streams():
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr

    atexit.register(_restore_streams)


class TimeoutHandler:
    """
    Handles query timeouts using signal alarms (Unix) or threading (Windows).

    Usage:
        with TimeoutHandler(seconds=30):
            # Long-running query
            result = execute_query()
    """

    def __init__(self, seconds: int = 30):
        """
        Initialize timeout handler.

        Args:
            seconds: Timeout duration in seconds (default: 30)
        """
        self.seconds = seconds
        self.timeout_occurred = False

    def __enter__(self):
        if sys.platform != 'win32':
            # Unix-based timeout using signals
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if sys.platform != 'win32':
            signal.alarm(0)  # Cancel alarm
        return False

    def _timeout_handler(self, signum, frame):
        self.timeout_occurred = True
        raise TimeoutError(
            f"Query timed out after {self.seconds} seconds. "
            f"Try reducing --limit or increasing --timeout. [QS003]"
        )


def escape_like(s: str) -> str:
    """
    Escape SQL LIKE wildcards to prevent wildcard injection.

    Args:
        s: String to escape

    Returns:
        String with SQL LIKE wildcards escaped
    """
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def get_current_time_ms() -> int:
    """
    Get current time in milliseconds since epoch.

    Returns:
        Integer timestamp in milliseconds
    """
    return int(datetime.now().timestamp() * 1000)
