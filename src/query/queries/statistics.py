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
                    learnings_by_type = {}
                    learnings_by_domain = {}
                    total_learnings = 0
                    async for l in Learning.select():
                        total_learnings += 1
                        learnings_by_type[l.type] = learnings_by_type.get(l.type, 0) + 1
                        learnings_by_domain[l.domain] = learnings_by_domain.get(l.domain, 0) + 1
                    stats['learnings_by_type'] = learnings_by_type
                    stats['learnings_by_domain'] = learnings_by_domain
                    stats['total_learnings'] = total_learnings

                    heuristics_by_domain = {}
                    golden_count = 0
                    total_heuristics = 0
                    async for h in Heuristic.select():
                        total_heuristics += 1
                        heuristics_by_domain[h.domain] = heuristics_by_domain.get(h.domain, 0) + 1
                        if h.is_golden:
                            golden_count += 1
                    stats['heuristics_by_domain'] = heuristics_by_domain
                    stats['golden_heuristics'] = golden_count
                    stats['total_heuristics'] = total_heuristics

                    experiments_by_status = {}
                    total_experiments = 0
                    async for e in Experiment.select():
                        total_experiments += 1
                        experiments_by_status[e.status] = experiments_by_status.get(e.status, 0) + 1
                    stats['experiments_by_status'] = experiments_by_status
                    stats['total_experiments'] = total_experiments

                    ceo_by_status = {}
                    total_ceo_reviews = 0
                    async for c in CeoReview.select():
                        total_ceo_reviews += 1
                        ceo_by_status[c.status] = ceo_by_status.get(c.status, 0) + 1
                    stats['ceo_reviews_by_status'] = ceo_by_status
                    stats['total_ceo_reviews'] = total_ceo_reviews

                    cutoff_7d = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
                    violations_7d = 0
                    violations_by_rule = {}
                    async for v in Violation.select().where(Violation.violation_date >= cutoff_7d):
                        violations_7d += 1
                        key = f"Rule {v.rule_id}: {v.rule_name}"
                        violations_by_rule[key] = violations_by_rule.get(key, 0) + 1
                    stats['violations_7d'] = violations_7d
                    stats['violations_by_rule_7d'] = violations_by_rule

        self._log_debug(f"Statistics gathered: {stats['total_learnings']} learnings total")
        return stats
