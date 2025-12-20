#!/usr/bin/env python3
"""Regression tests for QuerySystem to verify existing functionality."""

import pytest
import sys
import os

# Add query directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from query import QuerySystem


@pytest.fixture
def query_system():
    """Provide a QuerySystem instance for tests."""
    qs = QuerySystem()
    yield qs
    qs.cleanup()


class TestGoldenRulesRegression:
    """Regression tests for golden rules functionality."""

    def test_golden_rules_load(self, query_system):
        """Golden rules should load and not be empty."""
        rules = query_system.get_golden_rules()
        assert len(rules) > 0, "Golden rules should not be empty"

    def test_golden_rules_contain_rule_1(self, query_system):
        """Golden rules should contain Rule 1: Query Before Acting."""
        rules = query_system.get_golden_rules()
        assert "Query Before Acting" in rules, "Should contain Rule 1"


class TestStatisticsRegression:
    """Regression tests for statistics functionality."""

    def test_statistics_work(self, query_system):
        """Statistics should return properly structured data."""
        stats = query_system.get_statistics()
        assert 'total_learnings' in stats, "Should have total_learnings"


class TestQueryByDomainRegression:
    """Regression tests for domain queries."""

    def test_query_by_domain_works(self, query_system):
        """Query by domain should return properly structured result."""
        result = query_system.query_by_domain('testing', limit=5)
        assert 'heuristics' in result, "Should have heuristics key"
        assert 'learnings' in result, "Should have learnings key"


class TestQueryRecentRegression:
    """Regression tests for recent queries."""

    def test_query_recent_works(self, query_system):
        """Query recent should return a list."""
        result = query_system.query_recent(limit=5)
        assert isinstance(result, list), "Should return list"


class TestBuildContextRegression:
    """Regression tests for context building."""

    def test_build_context_works(self, query_system):
        """Build context should produce non-empty output with golden rules."""
        ctx = query_system.build_context("test task", domain="testing", max_tokens=2000)
        assert len(ctx) > 0, "Context should not be empty"
        assert "Golden Rules" in ctx, "Should contain golden rules"


class TestExperimentsRegression:
    """Regression tests for experiments functionality."""

    def test_active_experiments_works(self, query_system):
        """Active experiments query should return a list."""
        exp = query_system.get_active_experiments()
        assert isinstance(exp, list), "Should return list"


class TestCEOReviewsRegression:
    """Regression tests for CEO reviews functionality."""

    def test_ceo_reviews_works(self, query_system):
        """CEO reviews query should return a list."""
        reviews = query_system.get_pending_ceo_reviews()
        assert isinstance(reviews, list), "Should return list"


class TestDatabaseValidationRegression:
    """Regression tests for database validation."""

    def test_database_validation_works(self, query_system):
        """Database validation should return structured result."""
        valid = query_system.validate_database()
        assert 'valid' in valid, "Should have 'valid' key"


class TestQueryByTagsRegression:
    """Regression tests for tag queries."""

    def test_query_by_tags_works(self, query_system):
        """Query by tags should return a list."""
        tag_results = query_system.query_by_tags(['testing'], limit=5)
        assert isinstance(tag_results, list), "Should return list"


class TestFindSimilarFailuresRegression:
    """Regression tests for similar failures functionality."""

    def test_find_similar_failures_works(self, query_system):
        """Find similar failures should return a list."""
        similar = query_system.find_similar_failures("test query", limit=5)
        assert isinstance(similar, list), "Should return list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
