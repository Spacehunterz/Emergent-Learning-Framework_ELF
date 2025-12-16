"""
Spike report query mixin - research/investigation knowledge (async).
"""

from functools import reduce
from operator import or_
from typing import Dict, List, Any, Optional

try:
    from query.models import SpikeReport, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import SpikeReport, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class SpikeQueryMixin(BaseQueryMixin):
    """Mixin for spike report queries (async)."""

    async def get_spike_reports(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get spike reports (research/investigation knowledge) (async).

        Spike reports capture knowledge from research sessions that would otherwise
        be lost when the session ends. They preserve time-invested research findings.

        Args:
            domain: Optional domain filter
            tags: Optional list of tags to match
            search: Optional search term for title/topic/findings
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of spike report dictionaries ordered by usefulness and recency

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying spike reports (domain={domain}, tags={tags}, limit={limit})")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        query_status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)

            async with AsyncTimeoutHandler(timeout):
                try:
                    m = get_manager()
                    async with m:
                        async with m.connection():
                            query = SpikeReport.select()

                            if domain:
                                domain = self._validate_domain(domain)
                                query = query.where(
                                    (SpikeReport.domain == domain) | (SpikeReport.domain.is_null())
                                )

                            if tags:
                                tags = self._validate_tags(tags)
                                tag_conditions = reduce(
                                    or_,
                                    [SpikeReport.tags.contains(tag) for tag in tags]
                                )
                                query = query.where(tag_conditions)

                            if search:
                                query = query.where(
                                    (SpikeReport.title.contains(search)) |
                                    (SpikeReport.topic.contains(search)) |
                                    (SpikeReport.question.contains(search)) |
                                    (SpikeReport.findings.contains(search))
                                )

                            query = query.order_by(
                                SpikeReport.usefulness_score.desc(),
                                SpikeReport.created_at.desc()
                            ).limit(limit)

                            results = []
                            async for sr in query:
                                results.append({
                                    'id': sr.id,
                                    'title': sr.title,
                                    'topic': sr.topic,
                                    'question': sr.question,
                                    'findings': sr.findings,
                                    'gotchas': sr.gotchas,
                                    'resources': sr.resources,
                                    'time_invested_minutes': sr.time_invested_minutes,
                                    'domain': sr.domain,
                                    'tags': sr.tags,
                                    'usefulness_score': sr.usefulness_score,
                                    'access_count': sr.access_count,
                                    'created_at': sr.created_at,
                                    'updated_at': sr.updated_at
                                })
                except Exception as e:
                    # Table might not exist yet
                    if 'no such table' in str(e).lower():
                        self._log_debug("spike_reports table does not exist yet - returning empty list")
                        return []
                    raise

            self._log_debug(f"Found {len(results)} spike reports")
            return results

        except TimeoutError as e:
            query_status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            duration_ms = self._get_current_time_ms() - start_time
            spike_count = len(results) if results else 0

            await self._log_query(
                query_type='get_spike_reports',
                domain=domain,
                limit_requested=limit,
                results_returned=spike_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Spike reports query"
            )
