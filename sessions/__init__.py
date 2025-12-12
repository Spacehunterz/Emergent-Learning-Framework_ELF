"""
Session logging module for Emergent Learning Framework.

Provides session logging, tracking, and rotation capabilities.

Usage:
    from sessions import get_logger, get_tracker, get_rotation

    # Log tool usage
    logger = get_logger()
    logger.log_tool_use("Bash", {"command": "ls"}, {"output": "..."}, "success")

    # Track processed files
    tracker = get_tracker()
    unprocessed = tracker.get_unprocessed_files()

    # Clean old logs
    rotation = get_rotation()
    rotation.cleanup()
"""

from .logger import (
    SessionLogger,
    ProcessedTracker,
    SessionRotation,
    get_logger,
    get_tracker,
    get_rotation,
    run_startup,
    MAX_SUMMARY_LENGTH,
    RETENTION_DAYS,
    LOGS_DIR,
    PROCESSED_FILE,
)

__all__ = [
    'SessionLogger',
    'ProcessedTracker',
    'SessionRotation',
    'get_logger',
    'get_tracker',
    'get_rotation',
    'run_startup',
    'MAX_SUMMARY_LENGTH',
    'RETENTION_DAYS',
    'LOGS_DIR',
    'PROCESSED_FILE',
]
