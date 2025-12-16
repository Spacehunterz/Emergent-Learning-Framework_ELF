"""
Violation query mixin - golden rule violations and summaries.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    from query.models import Violation
    from query.utils import TimeoutHandler
    from query.exceptions import TimeoutError, DatabaseError
except ImportError:
    from models import Violation
    from utils import TimeoutHandler
    from exceptions import TimeoutError, DatabaseError

from peewee import fn
from .base import BaseQueryMixin


class ViolationQueryMixin(BaseQueryMixin):
    """Mixin for violation-related queries."""

    def get_violations(self, days: int = 7, acknowledged: Optional[bool] = None,
                      timeout: int = None) -> List[Dict[str, Any]]:
        """
        Get Golden Rule violations from the specified time period.

        Args:
            days: Number of days to look back (default: 7)
            acknowledged: Filter by acknowledged status (None = all)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of violations
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying violations (days={days}, acknowledged={acknowledged})")

        with TimeoutHandler(timeout):
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            query = Violation.select().where(Violation.violation_date >= cutoff)

            if acknowledged is not None:
                query = query.where(Violation.acknowledged == acknowledged)

            query = query.order_by(Violation.violation_date.desc())
            results = [v.__data__.copy() for v in query]

        self._log_debug(f"Found {len(results)} violations")
        return results

    def get_violation_summary(self, days: int = 7, timeout: int = None) -> Dict[str, Any]:
        """
        Get summary statistics of Golden Rule violations.

        Args:
            days: Number of days to look back (default: 7)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary with violation statistics
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying violation summary (days={days})")

        with TimeoutHandler(timeout):
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

            # Total count
            total = Violation.select().where(Violation.violation_date >= cutoff).count()

            # By rule (group by)
            by_rule_query = (Violation
                .select(Violation.rule_id, Violation.rule_name, fn.COUNT(Violation.id).alias('count'))
                .where(Violation.violation_date >= cutoff)
                .group_by(Violation.rule_id, Violation.rule_name)
                .order_by(fn.COUNT(Violation.id).desc()))
            by_rule = [{'rule_id': r.rule_id, 'rule_name': r.rule_name, 'count': r.count}
                      for r in by_rule_query]

            # Acknowledged count
            acknowledged = (Violation
                .select()
                .where((Violation.violation_date >= cutoff) & (Violation.acknowledged == True))
                .count())

            # Recent violations (last 5)
            recent_query = (Violation
                .select(Violation.rule_id, Violation.rule_name, Violation.description, Violation.violation_date)
                .where(Violation.violation_date >= cutoff)
                .order_by(Violation.violation_date.desc())
                .limit(5))
            recent = [{'rule_id': r.rule_id, 'rule_name': r.rule_name,
                      'description': r.description, 'date': str(r.violation_date) if r.violation_date else None}
                     for r in recent_query]

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
