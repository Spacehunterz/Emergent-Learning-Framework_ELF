"""
Utility functions and classes for the Query System.

Contains:
- AsyncTimeoutHandler: Async context manager for query timeout enforcement
- TimeoutHandler: Sync context manager (legacy, for CLI bootstrap)
- escape_like: SQL LIKE wildcard escaping
- Windows console encoding fix
- Time utilities
"""

import sys
import io
import signal
import asyncio
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


class AsyncTimeoutHandler:
    """
    Async timeout handler using asyncio.timeout (Python 3.11+).

    Usage:
        async with AsyncTimeoutHandler(seconds=30):
            result = await execute_query()

    Raises:
        TimeoutError: If the operation exceeds the specified timeout.
    """

    def __init__(self, seconds: int = 30):
        """
        Initialize async timeout handler.

        Args:
            seconds: Timeout duration in seconds (default: 30)
        """
        self.seconds = seconds
        self._timeout_context = None

    async def __aenter__(self):
        # Python 3.11+ has asyncio.timeout(), earlier versions use wait_for()
        if hasattr(asyncio, 'timeout'):
            self._timeout_context = asyncio.timeout(self.seconds)
            return await self._timeout_context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._timeout_context:
            try:
                return await self._timeout_context.__aexit__(exc_type, exc_val, exc_tb)
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Query timed out after {self.seconds} seconds. "
                    f"Try reducing --limit or increasing --timeout. [QS003]"
                )
        if exc_type is asyncio.TimeoutError:
            raise TimeoutError(
                f"Query timed out after {self.seconds} seconds. "
                f"Try reducing --limit or increasing --timeout. [QS003]"
            )
        return False


async def async_timeout(coro, seconds: int = 30):
    """
    Execute a coroutine with a timeout.

    Args:
        coro: The coroutine to execute
        seconds: Timeout duration in seconds (default: 30)

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If the operation exceeds the specified timeout.
    """
    try:
        if hasattr(asyncio, 'timeout'):
            async with asyncio.timeout(seconds):
                return await coro
        else:
            return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Query timed out after {seconds} seconds. "
            f"Try reducing --limit or increasing --timeout. [QS003]"
        )


class TimeoutHandler:
    """
    Sync timeout handler using signal alarms (Unix) or no-op (Windows).

    Legacy handler for CLI bootstrap operations. Use AsyncTimeoutHandler
    for async query operations.

    Usage:
        with TimeoutHandler(seconds=30):
            # Long-running operation
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
