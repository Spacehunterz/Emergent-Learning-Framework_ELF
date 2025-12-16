"""
Learning query mixin - recent learnings and similar failure search (async).
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    from query.models import Learning, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import Learning, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class LearningQueryMixin(BaseQueryMixin):
    """Mixin for learning-related queries (async)."""

    async def query_recent(self, type_filter: Optional[str] = None, limit: int = 10,
                    timeout: int = None, days: int = 2) -> List[Dict[str, Any]]:
        """
        Get recent learnings, optionally filtered by type (async).

        Args:
            type_filter: Optional type filter (e.g., 'incident', 'success')
            limit: Maximum number of results to return
            timeout: Query timeout in seconds (default: 30)
            days: Only return learnings from the last N days (default: 2)

        Returns:
            List of recent learnings
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT

            if type_filter:
                type_filter = self._validate_query(type_filter)

            self._log_debug(f"Querying recent learnings (type={type_filter}, limit={limit}, days={days})")
            async with AsyncTimeoutHandler(timeout):
                cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

                m = get_manager()
                async with m:
                    async with m.connection():
                        query = Learning.select()
                        if type_filter:
                            query = query.where(
                                (Learning.type == type_filter) &
                                (Learning.created_at >= cutoff)
                            )
                        else:
                            query = query.where(Learning.created_at >= cutoff)

                        query = query.order_by(Learning.created_at.desc()).limit(limit)
                        results = []
                        async for l in query:
                            results.append(l.__data__.copy())

            self._log_debug(f"Found {len(results)} recent learnings")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            duration_ms = self._get_current_time_ms() - start_time
            learnings_count = len(results) if results else 0

            await self._log_query(
                query_type='query_recent',
                limit_requested=limit,
                results_returned=learnings_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                learnings_count=learnings_count,
                query_summary=f"Recent learnings query{' (type=' + type_filter + ')' if type_filter else ''}"
            )

    async def find_similar_failures(self, task_description: str, limit: int = 5,
                             timeout: int = None) -> List[Dict[str, Any]]:
        """
        Find failures similar to a task description using keyword matching (async).

        Args:
            task_description: Description of the current task
            limit: Maximum number of similar failures to return
            timeout: Query timeout in seconds

        Returns:
            List of similar failure records with relevance scores
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Finding similar failures for: {task_description[:50]}...")

        async with AsyncTimeoutHandler(timeout):
            m = get_manager()
            async with m:
                async with m.connection():
                    # Get failure learnings
                    query = (Learning
                        .select()
                        .where(Learning.type == 'failure')
                        .order_by(Learning.created_at.desc())
                        .limit(100))  # Get recent failures to score

                    failures = []
                    async for f in query:
                        failures.append(f)

            # Score each failure by keyword overlap
            task_words = set(task_description.lower().split())
            scored = []

            for failure in failures:
                title = (failure.title or '').lower()
                summary = (failure.summary or '').lower()
                content_words = set(title.split() + summary.split())

                overlap = len(task_words & content_words)
                if overlap > 0:
                    scored.append({
                        'learning': failure.__data__.copy(),
                        'relevance_score': overlap / max(len(task_words), 1),
                        'matching_words': overlap
                    })

            # Sort by relevance and return top matches
            scored.sort(key=lambda x: x['relevance_score'], reverse=True)
            return scored[:limit]
