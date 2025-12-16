"""
Heuristic query mixin - golden rules, domain queries, tag queries (async).
"""

import aiofiles
from functools import reduce
from operator import or_
from typing import Dict, List, Any, Optional

# Import with fallbacks
try:
    from query.models import Heuristic, Learning, get_manager
    from query.utils import AsyncTimeoutHandler, escape_like
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import Heuristic, Learning, get_manager
    from utils import AsyncTimeoutHandler, escape_like
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class HeuristicQueryMixin(BaseQueryMixin):
    """Mixin for heuristic and golden rule queries (async)."""

    async def get_golden_rules(self) -> str:
        """
        Read and return golden rules from memory/golden-rules.md (async).

        Returns:
            Content of golden rules file, or empty string if file does not exist.
        """
        if not self.golden_rules_path.exists():
            return "# Golden Rules\n\nNo golden rules have been established yet."

        try:
            async with aiofiles.open(self.golden_rules_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            self._log_debug(f"Loaded golden rules ({len(content)} chars)")
            return content
        except Exception as e:
            error_msg = f"# Error Reading Golden Rules\n\nError: {str(e)}"
            self._log_debug(f"Failed to read golden rules: {e}")
            return error_msg

    async def query_by_domain(self, domain: str, limit: int = 10, timeout: int = None) -> Dict[str, Any]:
        """
        Get heuristics and learnings for a specific domain (async).

        Args:
            domain: The domain to query (e.g., 'coordination', 'debugging')
            limit: Maximum number of results to return
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary containing heuristics and learnings for the domain
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        result = None

        try:
            domain = self._validate_domain(domain)
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT

            self._log_debug(f"Querying domain '{domain}' with limit {limit}")
            async with AsyncTimeoutHandler(timeout):
                m = get_manager()
                async with m:
                    async with m.connection():
                        heuristics_query = (Heuristic
                            .select()
                            .where(Heuristic.domain == domain)
                            .order_by(Heuristic.confidence.desc(), Heuristic.times_validated.desc())
                            .limit(limit))
                        heuristics = []
                        async for h in heuristics_query:
                            heuristics.append(h.__data__.copy())

                        learnings_query = (Learning
                            .select()
                            .where(Learning.domain == domain)
                            .order_by(Learning.created_at.desc())
                            .limit(limit))
                        learnings = []
                        async for l in learnings_query:
                            learnings.append(l.__data__.copy())

            result = {
                'domain': domain,
                'heuristics': heuristics,
                'learnings': learnings,
                'count': {
                    'heuristics': len(heuristics),
                    'learnings': len(learnings)
                }
            }

            self._log_debug(f"Found {len(heuristics)} heuristics and {len(learnings)} learnings")
            return result

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
            heuristics_count = len(result['heuristics']) if result else 0
            learnings_count = len(result['learnings']) if result else 0
            total_results = heuristics_count + learnings_count

            await self._log_query(
                query_type='query_by_domain',
                domain=domain,
                limit_requested=limit,
                results_returned=total_results,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                heuristics_count=heuristics_count,
                learnings_count=learnings_count,
                query_summary=f"Domain query for '{domain}'"
            )

    async def query_by_tags(self, tags: List[str], limit: int = 10, timeout: int = None) -> List[Dict[str, Any]]:
        """
        Get learnings matching specified tags (async).

        Args:
            tags: List of tags to search for
            limit: Maximum number of results to return
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of learnings matching any of the tags
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            tags = self._validate_tags(tags)
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT

            self._log_debug(f"Querying tags {tags} with limit {limit}")
            async with AsyncTimeoutHandler(timeout):
                m = get_manager()
                async with m:
                    async with m.connection():
                        conditions = [Learning.tags.contains(escape_like(tag)) for tag in tags]
                        combined_conditions = reduce(or_, conditions)

                        query = (Learning
                            .select()
                            .where(combined_conditions)
                            .order_by(Learning.created_at.desc())
                            .limit(limit))
                        results = []
                        async for l in query:
                            results.append(l.__data__.copy())

            self._log_debug(f"Found {len(results)} results for tags")
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
                query_type='query_by_tags',
                tags=','.join(tags),
                limit_requested=limit,
                results_returned=learnings_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                learnings_count=learnings_count,
                query_summary=f"Tag query for {len(tags)} tags"
            )
