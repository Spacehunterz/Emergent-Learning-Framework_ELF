"""
Statistics query mixin - knowledge base statistics (async).
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any

try:
    from query.models import Learning, Heuristic, Experiment, CeoReview, Violation, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, DatabaseError
except ImportError:
    from models import Learning, Heuristic, Experiment, CeoReview, Violation, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, DatabaseError

from .base import BaseQueryMixin


class StatisticsQueryMixin(BaseQueryMixin):
    """Mixin for statistics queries (async)."""

    async def get_statistics(self, timeout: int = None) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base (async).

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

        async with AsyncTimeoutHandler(timeout):
            stats = {}

            m = get_manager()
            async with m:
                async with m.connection():
                    # Count learnings by type (aggregate manually for async)
                    learnings_by_type = {}
                    async for l in Learning.select():
                        t = l.type
                        learnings_by_type[t] = learnings_by_type.get(t, 0) + 1
                    stats['learnings_by_type'] = learnings_by_type

                    # Count learnings by domain
                    learnings_by_domain = {}
                    async for l in Learning.select():
                        d = l.domain
                        learnings_by_domain[d] = learnings_by_domain.get(d, 0) + 1
                    stats['learnings_by_domain'] = learnings_by_domain

                    # Count heuristics by domain
                    heuristics_by_domain = {}
                    async for h in Heuristic.select():
                        d = h.domain
                        heuristics_by_domain[d] = heuristics_by_domain.get(d, 0) + 1
                    stats['heuristics_by_domain'] = heuristics_by_domain

                    # Count golden heuristics
                    golden_count = 0
                    async for h in Heuristic.select().where(Heuristic.is_golden == True):
                        golden_count += 1
                    stats['golden_heuristics'] = golden_count

                    # Count experiments by status
                    experiments_by_status = {}
                    async for e in Experiment.select():
                        s = e.status
                        experiments_by_status[s] = experiments_by_status.get(s, 0) + 1
                    stats['experiments_by_status'] = experiments_by_status

                    # Count CEO reviews by status
                    ceo_by_status = {}
                    async for c in CeoReview.select():
                        s = c.status
                        ceo_by_status[s] = ceo_by_status.get(s, 0) + 1
                    stats['ceo_reviews_by_status'] = ceo_by_status

                    # Total counts
                    total_learnings = 0
                    async for _ in Learning.select():
                        total_learnings += 1
                    stats['total_learnings'] = total_learnings

                    total_heuristics = 0
                    async for _ in Heuristic.select():
                        total_heuristics += 1
                    stats['total_heuristics'] = total_heuristics

                    total_experiments = 0
                    async for _ in Experiment.select():
                        total_experiments += 1
                    stats['total_experiments'] = total_experiments

                    total_ceo_reviews = 0
                    async for _ in CeoReview.select():
                        total_ceo_reviews += 1
                    stats['total_ceo_reviews'] = total_ceo_reviews

                    # Violation statistics (last 7 days)
                    cutoff_7d = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
                    violations_7d = 0
                    async for _ in Violation.select().where(Violation.violation_date >= cutoff_7d):
                        violations_7d += 1
                    stats['violations_7d'] = violations_7d

                    violations_by_rule = {}
                    async for v in Violation.select().where(Violation.violation_date >= cutoff_7d):
                        key = f"Rule {v.rule_id}: {v.rule_name}"
                        violations_by_rule[key] = violations_by_rule.get(key, 0) + 1
                    stats['violations_by_rule_7d'] = violations_by_rule

        self._log_debug(f"Statistics gathered: {stats['total_learnings']} learnings total")
        return stats
