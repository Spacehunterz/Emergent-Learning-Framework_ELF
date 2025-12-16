"""
Custom exceptions for the Emergent Learning Framework Query System.

Error codes:
- QS000: Base/unknown error
- QS001: Input validation failure
- QS002: Database operation failure
- QS003: Query timeout
- QS004: Configuration error
"""


class QuerySystemError(Exception):
    """Base exception for query system errors."""
    error_code = 'QS000'


class ValidationError(QuerySystemError):
    """Raised when input validation fails."""
    error_code = 'QS001'


class DatabaseError(QuerySystemError):
    """Raised when database operations fail."""
    error_code = 'QS002'


class TimeoutError(QuerySystemError):
    """Raised when query times out."""
    error_code = 'QS003'


class ConfigurationError(QuerySystemError):
    """Raised when configuration is invalid."""
    error_code = 'QS004'
