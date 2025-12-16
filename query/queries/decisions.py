"""
Decision (ADR) query mixin.
"""

from typing import Dict, List, Any, Optional

try:
    from query.models import Decision
    from query.utils import TimeoutHandler
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import Decision
    from utils import TimeoutHandler
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class DecisionQueryMixin(BaseQueryMixin):
    """Mixin for architecture decision record (ADR) queries."""

    def get_decisions(
        self,
        domain: Optional[str] = None,
        status: str = 'accepted',
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get architecture decisions (ADRs), optionally filtered by domain.

        Args:
            domain: Optional domain filter
            status: Decision status filter (default: 'accepted')
            limit: Maximum number of results to return
            timeout: Query timeout in seconds

        Returns:
            List of decision dictionaries
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying decisions (domain={domain}, status={status}, limit={limit})")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        query_status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)

            with TimeoutHandler(timeout):
                query = Decision.select(
                    Decision.id, Decision.title, Decision.context,
                    Decision.decision, Decision.rationale, Decision.domain,
                    Decision.status, Decision.created_at
                ).where(Decision.status == status)

                if domain:
                    domain = self._validate_domain(domain)
                    query = query.where((Decision.domain == domain) | (Decision.domain.is_null()))

                query = query.order_by(Decision.created_at.desc()).limit(limit)
                results = [d.__data__.copy() for d in query]

            self._log_debug(f"Found {len(results)} decisions")
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
            decisions_count = len(results) if results else 0

            self._log_query(
                query_type='get_decisions',
                domain=domain,
                limit_requested=limit,
                results_returned=decisions_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Decisions query (status={status})"
            )
