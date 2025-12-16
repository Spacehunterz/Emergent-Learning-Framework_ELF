"""
Assumption query mixin - tracking assumptions and their validation status (async).
"""

from typing import Dict, List, Any, Optional

try:
    from query.models import Assumption, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import Assumption, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class AssumptionQueryMixin(BaseQueryMixin):
    """Mixin for assumption-related queries (async)."""

    async def get_assumptions(
        self,
        domain: Optional[str] = None,
        status: str = 'active',
        min_confidence: float = 0.0,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get assumptions, optionally filtered by domain and status (async).

        Args:
            domain: Optional domain filter
            status: Assumption status filter (active, verified, challenged, invalidated)
            min_confidence: Minimum confidence threshold (default: 0.0)
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of assumption dictionaries

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying assumptions (domain={domain}, status={status}, limit={limit})")

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
                            query = (Assumption
                                .select()
                                .where(
                                    (Assumption.status == status) &
                                    (Assumption.confidence >= min_confidence)
                                ))

                            if domain:
                                domain = self._validate_domain(domain)
                                query = query.where(
                                    (Assumption.domain == domain) | (Assumption.domain.is_null())
                                )

                            query = query.order_by(
                                Assumption.confidence.desc(),
                                Assumption.created_at.desc()
                            ).limit(limit)

                            results = []
                            async for a in query:
                                results.append({
                                    'id': a.id,
                                    'assumption': a.assumption,
                                    'context': a.context,
                                    'source': a.source,
                                    'confidence': a.confidence,
                                    'status': a.status,
                                    'domain': a.domain,
                                    'verified_count': a.verified_count,
                                    'challenged_count': a.challenged_count,
                                    'last_verified_at': a.last_verified_at,
                                    'created_at': a.created_at
                                })
                except Exception as e:
                    # Table might not exist yet
                    if 'no such table' in str(e).lower():
                        self._log_debug("Assumptions table does not exist yet - returning empty list")
                        return []
                    raise

            self._log_debug(f"Found {len(results)} assumptions")
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
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            assumptions_count = len(results) if results else 0

            await self._log_query(
                query_type='get_assumptions',
                domain=domain,
                limit_requested=limit,
                results_returned=assumptions_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Assumptions query (status={status}, min_confidence={min_confidence})"
            )

    async def get_challenged_assumptions(
        self,
        domain: Optional[str] = None,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get challenged or invalidated assumptions as warnings (async).

        These are assumptions that have been found to be incorrect or questionable.
        Future sessions should be aware of these to avoid repeating mistakes.

        Args:
            domain: Optional domain filter
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of challenged/invalidated assumption dictionaries
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying challenged assumptions (domain={domain}, limit={limit})")

        async with AsyncTimeoutHandler(timeout):
            try:
                m = get_manager()
                async with m:
                    async with m.connection():
                        query = (Assumption
                            .select()
                            .where(Assumption.status.in_(['challenged', 'invalidated'])))

                        if domain:
                            domain = self._validate_domain(domain)
                            query = query.where(
                                (Assumption.domain == domain) | (Assumption.domain.is_null())
                            )

                        query = query.order_by(
                            Assumption.challenged_count.desc(),
                            Assumption.created_at.desc()
                        ).limit(limit)

                        results = []
                        async for a in query:
                            results.append({
                                'id': a.id,
                                'assumption': a.assumption,
                                'context': a.context,
                                'source': a.source,
                                'confidence': a.confidence,
                                'status': a.status,
                                'domain': a.domain,
                                'verified_count': a.verified_count,
                                'challenged_count': a.challenged_count,
                                'created_at': a.created_at
                            })
            except Exception as e:
                # Table might not exist yet
                if 'no such table' in str(e).lower():
                    return []
                raise

        self._log_debug(f"Found {len(results)} challenged/invalidated assumptions")
        return results
