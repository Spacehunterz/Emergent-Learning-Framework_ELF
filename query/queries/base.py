"""
Base query mixin with shared methods for all query types (async version).

Provides logging, timing, and utility methods used across all query mixins.
"""

import sys
from datetime import datetime, timezone
from typing import Optional

# Import models with fallback
try:
    from query.models import BuildingQuery, get_manager
except ImportError:
    from models import BuildingQuery, get_manager


class BaseQueryMixin:
    """
    Base mixin providing shared query infrastructure (async).

    Attributes expected from composing class:
    - self.debug: bool
    - self.session_id: Optional[str]
    - self.agent_id: Optional[str]
    - self.db_path: Path
    """

    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _get_current_time_ms(self) -> int:
        """Get current time in milliseconds since epoch."""
        return int(datetime.now().timestamp() * 1000)

    async def _log_query(
        self,
        query_type: str,
        domain: Optional[str] = None,
        tags: Optional[str] = None,
        limit_requested: Optional[int] = None,
        max_tokens_requested: Optional[int] = None,
        results_returned: int = 0,
        tokens_approximated: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        golden_rules_returned: int = 0,
        heuristics_count: int = 0,
        learnings_count: int = 0,
        experiments_count: int = 0,
        ceo_reviews_count: int = 0,
        query_summary: Optional[str] = None,
        **kwargs
    ):
        """
        Log a query to the building_queries table (async).

        This is a non-blocking operation - if logging fails, it will not raise an exception.
        """
        try:
            m = get_manager()
            async with m:
                async with m.connection():
                    await BuildingQuery.create(
                        query_type=query_type,
                        session_id=self.session_id,
                        agent_id=self.agent_id,
                        domain=domain,
                        tags=tags,
                        limit_requested=limit_requested,
                        max_tokens_requested=max_tokens_requested,
                        results_returned=results_returned,
                        tokens_approximated=tokens_approximated,
                        duration_ms=duration_ms,
                        status=status,
                        error_message=error_message,
                        error_code=error_code,
                        golden_rules_returned=golden_rules_returned,
                        heuristics_count=heuristics_count,
                        learnings_count=learnings_count,
                        experiments_count=experiments_count,
                        ceo_reviews_count=ceo_reviews_count,
                        query_summary=query_summary,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
            self._log_debug(f"Logged query: {query_type} (status={status}, duration={duration_ms}ms)")
        except Exception as e:
            self._log_debug(f"Failed to log query to building_queries: {e}")
