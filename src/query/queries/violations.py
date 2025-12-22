"""
Violation query mixin - golden rule violations and summaries (async).
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    from query.models import Violation, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, DatabaseError
except ImportError:
    from models import Violation, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, DatabaseError

from peewee import fn
from .base import BaseQueryMixin


class ViolationQueryMixin(BaseQueryMixin):
    """Mixin for violation-related queries (async)."""

    async def get_violations(self, days: int = 7, acknowledged: Optional[bool] = None,
                      timeout: int = None) -> List[Dict[str, Any]]:
        """
        Get Golden Rule violations from the specified time period (async).

        Args:
            days: Number of days to look back (default: 7)
            acknowledged: Filter by acknowledged status (None = all)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of violations
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying violations (days={days}, acknowledged={acknowledged})")

        async with AsyncTimeoutHandler(timeout):
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

            m = get_manager()
            async with m:
                async with m.connection():
                    query = Violation.select().where(Violation.violation_date >= cutoff)

                    if acknowledged is not None:
                        query = query.where(Violation.acknowledged == acknowledged)

                    query = query.order_by(Violation.violation_date.desc())
                    results = []
                    async for v in query:
                        results.append(v.__data__.copy())

        self._log_debug(f"Found {len(results)} violations")
        return results

    async def get_violation_summary(self, days: int = 7, timeout: int = None) -> Dict[str, Any]:
        """
        Get summary statistics of Golden Rule violations (async).

        Args:
            days: Number of days to look back (default: 7)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary with violation statistics
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying violation summary (days={days})")

        async with AsyncTimeoutHandler(timeout):
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

            m = get_manager()
            async with m:
                async with m.connection():
                    # Total count
                    total = 0
                    async for _ in Violation.select().where(Violation.violation_date >= cutoff):
                        total += 1

                    # By rule (group by) - need to aggregate manually for async
                    by_rule_dict = {}
                    async for v in Violation.select().where(Violation.violation_date >= cutoff):
                        key = (v.rule_id, v.rule_name)
                        by_rule_dict[key] = by_rule_dict.get(key, 0) + 1

                    by_rule = [{'rule_id': k[0], 'rule_name': k[1], 'count': v}
                              for k, v in sorted(by_rule_dict.items(), key=lambda x: -x[1])]

                    # Acknowledged count
                    acknowledged = 0
                    async for _ in Violation.select().where(
                        (Violation.violation_date >= cutoff) & (Violation.acknowledged == True)
                    ):
                        acknowledged += 1

                    # Recent violations (last 5)
                    recent_query = (Violation
                        .select()
                        .where(Violation.violation_date >= cutoff)
                        .order_by(Violation.violation_date.desc())
                        .limit(5))
                    recent = []
                    async for r in recent_query:
                        recent.append({
                            'rule_id': r.rule_id,
                            'rule_name': r.rule_name,
                            'description': r.description,
                            'date': str(r.violation_date) if r.violation_date else None
                        })

        summary = {
            'total': total,
            'acknowledged': acknowledged,
            'unacknowledged': total - acknowledged,
            'by_rule': by_rule,
            'recent': recent,
            'days': days
        }

        self._log_debug(f"Violation summary: {total} total in {days} days")
        return summary

    def _calculate_relevance_score(self, learning: Dict, task: str,
                                    domain: str = None) -> float:
        """
        Calculate relevance score with decay factors.

        Args:
            learning: Learning dictionary with created_at, domain, times_validated
            task: Task description (for future keyword matching)
            domain: Optional domain filter

        Returns:
            Relevance score between 0.25 and 1.0
        """
        score = 0.5  # Base score

        # Recency decay (half-life: 7 days)
        created_at = learning.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_at = created_at.replace('Z', '+00:00')
                    if 'T' in created_at:
                        created_at = datetime.fromisoformat(created_at)
                    else:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')

                age_days = (datetime.now() - created_at).days
                recency_factor = 0.5 ** (age_days / 7)
                score *= (0.5 + 0.5 * recency_factor)
            except (ValueError, TypeError) as e:
                self._log_debug(f"Failed to parse date {created_at}: {e}")

        # Domain match boost
        if domain and learning.get('domain') == domain:
            score *= 1.5

        # Validation boost
        times_validated = learning.get('times_validated', 0)
        if times_validated > 10:
            score *= 1.4
        elif times_validated > 5:
            score *= 1.2

        return min(score, 1.0)
