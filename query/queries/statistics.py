"""
Statistics query mixin - knowledge base statistics.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from peewee import fn

try:
    from query.models import Learning, Heuristic, Experiment, CeoReview, Violation
    from query.utils import TimeoutHandler
    from query.exceptions import TimeoutError, DatabaseError
except ImportError:
    from models import Learning, Heuristic, Experiment, CeoReview, Violation
    from utils import TimeoutHandler
    from exceptions import TimeoutError, DatabaseError

from .base import BaseQueryMixin


class StatisticsQueryMixin(BaseQueryMixin):
    """Mixin for statistics queries."""

    def get_statistics(self, timeout: int = None) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.

        Args:
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary containing various statistics

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug("Gathering statistics")

        with TimeoutHandler(timeout):
            stats = {}

            # Count learnings by type
            learnings_type_query = (Learning
                .select(Learning.type, fn.COUNT(Learning.id).alias('count'))
                .group_by(Learning.type))
            stats['learnings_by_type'] = {r.type: r.count for r in learnings_type_query}

            # Count learnings by domain
            learnings_domain_query = (Learning
                .select(Learning.domain, fn.COUNT(Learning.id).alias('count'))
                .group_by(Learning.domain))
            stats['learnings_by_domain'] = {r.domain: r.count for r in learnings_domain_query}

            # Count heuristics by domain
            heuristics_domain_query = (Heuristic
                .select(Heuristic.domain, fn.COUNT(Heuristic.id).alias('count'))
                .group_by(Heuristic.domain))
            stats['heuristics_by_domain'] = {r.domain: r.count for r in heuristics_domain_query}

            # Count golden heuristics
            stats['golden_heuristics'] = Heuristic.select().where(Heuristic.is_golden == True).count()

            # Count experiments by status
            experiments_status_query = (Experiment
                .select(Experiment.status, fn.COUNT(Experiment.id).alias('count'))
                .group_by(Experiment.status))
            stats['experiments_by_status'] = {r.status: r.count for r in experiments_status_query}

            # Count CEO reviews by status
            ceo_status_query = (CeoReview
                .select(CeoReview.status, fn.COUNT(CeoReview.id).alias('count'))
                .group_by(CeoReview.status))
            stats['ceo_reviews_by_status'] = {r.status: r.count for r in ceo_status_query}

            # Total counts
            stats['total_learnings'] = Learning.select().count()
            stats['total_heuristics'] = Heuristic.select().count()
            stats['total_experiments'] = Experiment.select().count()
            stats['total_ceo_reviews'] = CeoReview.select().count()

            # Violation statistics (last 7 days)
            cutoff_7d = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
            stats['violations_7d'] = Violation.select().where(Violation.violation_date >= cutoff_7d).count()

            violations_rule_query = (Violation
                .select(Violation.rule_id, Violation.rule_name, fn.COUNT(Violation.id).alias('count'))
                .where(Violation.violation_date >= cutoff_7d)
                .group_by(Violation.rule_id, Violation.rule_name)
                .order_by(fn.COUNT(Violation.id).desc()))
            stats['violations_by_rule_7d'] = {f"Rule {r.rule_id}: {r.rule_name}": r.count
                                              for r in violations_rule_query}

        self._log_debug(f"Statistics gathered: {stats['total_learnings']} learnings total")
        return stats
