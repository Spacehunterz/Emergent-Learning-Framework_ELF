"""
Invariant query mixin - statements about what must ALWAYS be true (async).
"""

from typing import Dict, List, Any, Optional

try:
    from query.models import Invariant, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import Invariant, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class InvariantQueryMixin(BaseQueryMixin):
    """Mixin for invariant-related queries (async)."""

    async def get_invariants(
        self,
        domain: Optional[str] = None,
        status: str = 'active',
        scope: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get invariants, optionally filtered by domain, status, scope, or severity (async).

        Invariants are statements about what must ALWAYS be true, different from
        Golden Rules which say "don't do X". Invariants can be validated automatically.

        Args:
            domain: Optional domain filter
            status: Invariant status filter (active, deprecated, violated)
            scope: Scope filter (codebase, module, function, runtime)
            severity: Severity filter (error, warning, info)
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of invariant dictionaries with id, statement, rationale, etc.

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying invariants (domain={domain}, status={status}, limit={limit})")

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
                            query = Invariant.select()

                            if status:
                                query = query.where(Invariant.status == status)

                            if domain:
                                domain = self._validate_domain(domain)
                                query = query.where(
                                    (Invariant.domain == domain) | (Invariant.domain.is_null())
                                )

                            if scope:
                                query = query.where(Invariant.scope == scope)

                            if severity:
                                query = query.where(Invariant.severity == severity)

                            query = query.order_by(Invariant.created_at.desc()).limit(limit)

                            results = []
                            async for inv in query:
                                results.append({
                                    'id': inv.id,
                                    'statement': inv.statement,
                                    'rationale': inv.rationale,
                                    'domain': inv.domain,
                                    'scope': inv.scope,
                                    'severity': inv.severity,
                                    'status': inv.status,
                                    'created_at': inv.created_at
                                })
                except Exception as e:
                    # Table might not exist yet
                    if 'no such table' in str(e).lower():
                        self._log_debug("Invariants table does not exist yet - returning empty list")
                        return []
                    raise

            self._log_debug(f"Found {len(results)} invariants")
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
            invariants_count = len(results) if results else 0

            await self._log_query(
                query_type='get_invariants',
                domain=domain,
                limit_requested=limit,
                results_returned=invariants_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Invariants query (status={status})"
            )
