"""
Experiment and CEO review query mixin (async).
"""

from typing import Dict, List, Any, Optional

try:
    from query.models import Experiment, CeoReview, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, DatabaseError, QuerySystemError
except ImportError:
    from models import Experiment, CeoReview, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class ExperimentQueryMixin(BaseQueryMixin):
    """Mixin for experiment and CEO review queries (async)."""

    async def get_active_experiments(self, timeout: int = None) -> List[Dict[str, Any]]:
        """
        List all active experiments (async).

        Args:
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of active experiments
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug("Querying active experiments")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            async with AsyncTimeoutHandler(timeout):
                m = get_manager()
                async with m:
                    async with m.connection():
                        query = (Experiment
                            .select()
                            .where(Experiment.status == 'active')
                            .order_by(Experiment.created_at.desc()))
                        results = []
                        async for e in query:
                            results.append(e.__data__.copy())

            self._log_debug(f"Found {len(results)} active experiments")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            duration_ms = self._get_current_time_ms() - start_time
            experiments_count = len(results) if results else 0

            await self._log_query(
                query_type='get_active_experiments',
                results_returned=experiments_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                experiments_count=experiments_count,
                query_summary="Active experiments query"
            )

    async def get_pending_ceo_reviews(self, timeout: int = None) -> List[Dict[str, Any]]:
        """
        List all pending CEO reviews (async).

        Args:
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of pending CEO reviews
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug("Querying pending CEO reviews")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            async with AsyncTimeoutHandler(timeout):
                m = get_manager()
                async with m:
                    async with m.connection():
                        query = (CeoReview
                            .select()
                            .where(CeoReview.status == 'pending')
                            .order_by(CeoReview.created_at.desc()))
                        results = []
                        async for r in query:
                            results.append(r.__data__.copy())

            self._log_debug(f"Found {len(results)} pending CEO reviews")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            duration_ms = self._get_current_time_ms() - start_time
            ceo_reviews_count = len(results) if results else 0

            await self._log_query(
                query_type='get_pending_ceo_reviews',
                results_returned=ceo_reviews_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                ceo_reviews_count=ceo_reviews_count,
                query_summary="Pending CEO reviews query"
            )
