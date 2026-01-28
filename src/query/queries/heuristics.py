"""
Heuristic query mixin - golden rules, domain queries, tag queries (async).

Now includes semantic search (Option B) for relevance-based heuristic retrieval.
"""

import aiofiles
import time
from typing import Dict, List, Any, Optional

_golden_rules_cache: Dict[str, str] = {}
_golden_rules_cache_time: Dict[str, float] = {}
_GOLDEN_RULES_CACHE_TTL = 300

# Import with fallbacks
try:
    from query.models import Heuristic, Learning, get_manager
    from query.utils import AsyncTimeoutHandler, build_csv_tag_conditions
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
except ImportError:
    from models import Heuristic, Learning, get_manager
    from utils import AsyncTimeoutHandler, build_csv_tag_conditions
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError

from .base import BaseQueryMixin


class HeuristicQueryMixin(BaseQueryMixin):
    """Mixin for heuristic and golden rule queries (async)."""

    async def get_golden_rules(self, categories: Optional[List[str]] = None) -> str:
        """
        Read and return golden rules from memory/golden-rules.md (async with caching).

        Args:
            categories: Optional list of categories to filter by (e.g., ['core', 'git']).
                       If None, returns all rules.

        Returns:
            Content of golden rules file (filtered by category if specified),
            or empty string if file does not exist.
        """
        if not self.golden_rules_path.exists():
            return "# Golden Rules\n\nNo golden rules have been established yet."

        cache_key = str(self.golden_rules_path)
        now = time.time()

        if cache_key in _golden_rules_cache:
            if now - _golden_rules_cache_time.get(cache_key, 0) < _GOLDEN_RULES_CACHE_TTL:
                content = _golden_rules_cache[cache_key]
                if not categories:
                    self._log_debug(f"Golden rules from cache ({len(content)} chars)")
                    return content
                filtered = self._filter_golden_rules_by_category(content, categories)
                self._log_debug(f"Golden rules from cache filtered by {categories}")
                return filtered

        try:
            async with aiofiles.open(self.golden_rules_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            _golden_rules_cache[cache_key] = content
            _golden_rules_cache_time[cache_key] = now

            if not categories:
                self._log_debug(f"Loaded golden rules ({len(content)} chars)")
                return content

            filtered = self._filter_golden_rules_by_category(content, categories)
            self._log_debug(f"Loaded golden rules filtered by {categories} ({len(filtered)} chars)")
            return filtered

        except Exception as e:
            error_msg = f"# Error Reading Golden Rules\n\nError: {str(e)}"
            self._log_debug(f"Failed to read golden rules: {e}")
            return error_msg

    def _filter_golden_rules_by_category(self, content: str, categories: List[str]) -> str:
        """
        Filter golden rules markdown content by category.

        Args:
            content: Full golden rules markdown content
            categories: List of categories to include

        Returns:
            Filtered markdown with only rules matching categories
        """
        import re

        # Normalize categories to lowercase for comparison
        categories_lower = [c.lower() for c in categories]

        lines = content.split('\n')
        result_lines = []
        in_rule = False
        current_rule_lines = []
        include_current = False

        # Always include header
        header_ended = False

        for line in lines:
            # Check for rule header (## N. Title)
            if re.match(r'^## \d+\.', line):
                # Save previous rule if it should be included
                if in_rule and include_current:
                    result_lines.extend(current_rule_lines)

                # Start new rule
                in_rule = True
                current_rule_lines = [line]
                include_current = False
                header_ended = True

            elif in_rule:
                current_rule_lines.append(line)

                # Check for category line
                if line.startswith('**Category:**'):
                    category_match = re.search(r'\*\*Category:\*\*\s*(.+)', line)
                    if category_match:
                        rule_category = category_match.group(1).strip().lower()
                        if rule_category in categories_lower:
                            include_current = True

            elif not header_ended:
                # Include file header (before first rule)
                result_lines.append(line)

        # Don't forget the last rule
        if in_rule and include_current:
            result_lines.extend(current_rule_lines)

        # Add category filter note
        filter_note = f"\n*[Filtered to categories: {', '.join(categories)}]*\n"

        return '\n'.join(result_lines) + filter_note

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

            current_loc = getattr(self, 'current_location', None)
            self._log_debug(f"Querying domain '{domain}' with limit {limit}, location={current_loc}")
            async with AsyncTimeoutHandler(timeout):
                m = get_manager()
                async with m:
                    async with m.connection():
                        # Include global heuristics (project_path IS NULL) and location-specific ones
                        if current_loc:
                            heuristics_query = (Heuristic
                                .select()
                                .where(
                                    (Heuristic.domain == domain) &
                                    ((Heuristic.project_path.is_null()) | (Heuristic.project_path == current_loc))
                                )
                                .order_by(Heuristic.confidence.desc(), Heuristic.times_validated.desc())
                                .limit(limit))
                        else:
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
                        combined_conditions = build_csv_tag_conditions(Learning.tags, tags)

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

    async def query_semantic(
        self,
        task: str,
        threshold: float = 0.75,
        limit: int = 5,
        domain: Optional[str] = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Find heuristics semantically relevant to a task description (Option B).

        Uses embedding-based semantic similarity to match task descriptions against
        heuristics, returning only those with high relevance scores.

        Args:
            task: Task description to match against heuristics
            threshold: Minimum similarity score (0.0-1.0), default 0.75
            limit: Maximum number of results to return, default 5
            domain: Optional domain to filter by before semantic matching
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary containing:
            - 'task': The original task description
            - 'heuristics': List of heuristics with similarity scores
            - 'count': Number of heuristics returned
            - 'threshold': The threshold used for filtering
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        result = None

        try:
            # Validate inputs
            task = self._validate_query(task)
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT * 2  # Semantic search may take longer
            
            if not 0.0 <= threshold <= 1.0:
                raise ValidationError("Threshold must be between 0.0 and 1.0")

            self._log_debug(f"Semantic query for task: {task[:50]}... threshold={threshold}")
            
            # Import semantic search (with fallback if not available)
            try:
                from query.semantic_search import SemanticSearcher
            except ImportError:
                from semantic_search import SemanticSearcher
            
            async with AsyncTimeoutHandler(timeout):
                # Initialize semantic searcher
                searcher = await SemanticSearcher.create(base_path=self.base_path)
                
                # Find relevant heuristics
                heuristics = await searcher.find_relevant_heuristics(
                    task=task,
                    threshold=threshold,
                    limit=limit,
                    domain=domain
                )
                
                # Clean up searcher
                await searcher.cleanup()

            result = {
                'task': task,
                'heuristics': heuristics,
                'count': len(heuristics),
                'threshold': threshold
            }

            self._log_debug(f"Found {len(heuristics)} semantically relevant heuristics")
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

            await self._log_query(
                query_type='query_semantic',
                query_summary=f"Semantic query: {task[:50]}...",
                limit_requested=limit,
                results_returned=heuristics_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                heuristics_count=heuristics_count
            )
