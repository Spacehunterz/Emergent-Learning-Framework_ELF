#!/usr/bin/env python3
"""Regression tests for QuerySystem to verify existing functionality."""

import sys
import os

# Add query directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from query import QuerySystem

def run_regression_tests():
    """Run all regression tests."""
    print("=" * 60)
    print("REGRESSION TESTS - Existing Functionality")
    print("=" * 60)
    print()

    qs = QuerySystem()
    results = []

    # Test 1: Golden rules still load
    try:
        rules = qs.get_golden_rules()
        assert len(rules) > 0, "Golden rules should not be empty"
        assert "Query Before Acting" in rules, "Should contain Rule 1"
        results.append(('PASS', 'Test 1: Golden rules load', f"{len(rules)} chars"))
    except Exception as e:
        results.append(('FAIL', 'Test 1: Golden rules failed', str(e)))

    # Test 2: Stats still work
    try:
        stats = qs.get_statistics()
        assert 'total_learnings' in stats, "Should have total_learnings"
        results.append(('PASS', 'Test 2: Statistics work', f"learnings: {stats['total_learnings']}"))
    except Exception as e:
        results.append(('FAIL', 'Test 2: Statistics failed', str(e)))

    # Test 3: Query by domain still works
    try:
        result = qs.query_by_domain('testing', limit=5)
        assert 'heuristics' in result, "Should have heuristics key"
        assert 'learnings' in result, "Should have learnings key"
        results.append(('PASS', 'Test 3: Query by domain works', "Domain query functional"))
    except Exception as e:
        results.append(('FAIL', 'Test 3: Query by domain failed', str(e)))

    # Test 4: Query recent still works
    try:
        result = qs.query_recent(limit=5)
        assert isinstance(result, list), "Should return list"
        results.append(('PASS', 'Test 4: Query recent works', f"{len(result)} results"))
    except Exception as e:
        results.append(('FAIL', 'Test 4: Query recent failed', str(e)))

    # Test 5: Build context still works
    try:
        ctx = qs.build_context("test task", domain="testing", max_tokens=2000)
        assert len(ctx) > 0, "Context should not be empty"
        assert "Golden Rules" in ctx, "Should contain golden rules"
        results.append(('PASS', 'Test 5: Build context works', f"{len(ctx)} chars"))
    except Exception as e:
        results.append(('FAIL', 'Test 5: Build context failed', str(e)))

    # Test 6: Active experiments query
    try:
        exp = qs.get_active_experiments()
        assert isinstance(exp, list), "Should return list"
        results.append(('PASS', 'Test 6: Active experiments works', f"{len(exp)} experiments"))
    except Exception as e:
        results.append(('FAIL', 'Test 6: Active experiments failed', str(e)))

    # Test 7: CEO reviews query
    try:
        reviews = qs.get_pending_ceo_reviews()
        assert isinstance(reviews, list), "Should return list"
        results.append(('PASS', 'Test 7: CEO reviews works', f"{len(reviews)} pending"))
    except Exception as e:
        results.append(('FAIL', 'Test 7: CEO reviews failed', str(e)))

    # Test 8: Validate database
    try:
        valid = qs.validate_database()
        results.append(('PASS', 'Test 8: Database validation', f"{'PASSED' if valid['valid'] else 'ISSUES'}"))
    except Exception as e:
        results.append(('FAIL', 'Test 8: Database validation failed', str(e)))

    # Test 9: Query by tags
    try:
        tag_results = qs.query_by_tags(['testing'], limit=5)
        assert isinstance(tag_results, list), "Should return list"
        results.append(('PASS', 'Test 9: Query by tags', f"{len(tag_results)} results"))
    except Exception as e:
        results.append(('FAIL', 'Test 9: Query by tags failed', str(e)))

    # Test 10: Find similar failures
    try:
        similar = qs.find_similar_failures("test query", limit=5)
        assert isinstance(similar, list), "Should return list"
        results.append(('PASS', 'Test 10: Find similar failures', f"{len(similar)} results"))
    except Exception as e:
        results.append(('FAIL', 'Test 10: Find similar failures failed', str(e)))

    qs.cleanup()

    # Print results
    print()
    passed = 0
    failed = 0

    for status, test, detail in results:
        symbol = "✓" if status == "PASS" else "✗"
        print(f"{symbol} {test}: {detail}")
        if status == "PASS":
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} PASSED, {failed} FAILED")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = run_regression_tests()
    sys.exit(0 if success else 1)
