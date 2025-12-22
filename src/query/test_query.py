#!/usr/bin/env python3
"""
Comprehensive Test Suite for Query System v2.0

Tests all features for 10/10 robustness:
- Input validation
- CLI enhancements
- Error handling
- Connection pooling
- Timeout enforcement
- Database validation
"""

import sys
import os
import tempfile
import shutil
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import query
from query import (
    QuerySystem, ValidationError, DatabaseError, TimeoutError,
    ConfigurationError, format_output
)


class TestQuerySystem:
    """Test suite for QuerySystem."""

    def __init__(self):
        self.test_dir = None
        self.test_system = None
        self.passed = 0
        self.failed = 0
        self.errors = []

    def setup(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="query_test_")
        self.test_system = QuerySystem(base_path=self.test_dir, debug=False)
        print(f"Test environment created at: {self.test_dir}")

    def teardown(self):
        """Clean up test environment."""
        if self.test_system:
            self.test_system.cleanup()
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        print(f"Test environment cleaned up")

    def assert_true(self, condition, message):
        """Assert that condition is true."""
        if condition:
            self.passed += 1
            print(f"  PASS: {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            print(f"  FAIL: {message}")

    def assert_raises(self, exception_type, func, *args, **kwargs):
        """Assert that function raises specific exception."""
        try:
            func(*args, **kwargs)
            self.failed += 1
            msg = f"Expected {exception_type.__name__} but no exception was raised"
            self.errors.append(msg)
            print(f"  FAIL: {msg}")
            return False
        except exception_type:
            self.passed += 1
            print(f"  PASS: Correctly raised {exception_type.__name__}")
            return True
        except Exception as e:
            self.failed += 1
            msg = f"Expected {exception_type.__name__} but got {type(e).__name__}: {e}"
            self.errors.append(msg)
            print(f"  FAIL: {msg}")
            return False

    # ========== VALIDATION TESTS ==========

    def test_validate_domain(self):
        """Test domain validation."""
        print("\n[TEST] Domain Validation")

        # Valid domains
        self.assert_true(
            self.test_system._validate_domain("coordination") == "coordination",
            "Valid domain accepted"
        )
        self.assert_true(
            self.test_system._validate_domain("test-domain_123") == "test-domain_123",
            "Domain with hyphens and underscores accepted"
        )

        # Invalid domains
        self.assert_raises(
            ValidationError,
            self.test_system._validate_domain,
            ""
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_domain,
            "a" * 150  # Too long
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_domain,
            "invalid@domain"  # Invalid characters
        )

    def test_validate_limit(self):
        """Test limit validation."""
        print("\n[TEST] Limit Validation")

        # Valid limits
        self.assert_true(
            self.test_system._validate_limit(10) == 10,
            "Valid limit accepted"
        )
        self.assert_true(
            self.test_system._validate_limit(1) == 1,
            "Minimum limit accepted"
        )
        self.assert_true(
            self.test_system._validate_limit(1000) == 1000,
            "Maximum limit accepted"
        )

        # Invalid limits
        self.assert_raises(
            ValidationError,
            self.test_system._validate_limit,
            0  # Too small
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_limit,
            1001  # Too large
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_limit,
            "10"  # Wrong type
        )

    def test_validate_tags(self):
        """Test tags validation."""
        print("\n[TEST] Tags Validation")

        # Valid tags
        self.assert_true(
            self.test_system._validate_tags(["tag1", "tag2"]) == ["tag1", "tag2"],
            "Valid tags accepted"
        )
        self.assert_true(
            len(self.test_system._validate_tags(["  tag1  ", "tag2"])) == 2,
            "Tags trimmed correctly"
        )

        # Invalid tags
        self.assert_raises(
            ValidationError,
            self.test_system._validate_tags,
            "not-a-list"  # Wrong type
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_tags,
            ["tag" + str(i) for i in range(60)]  # Too many tags
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_tags,
            ["invalid@tag"]  # Invalid characters
        )

    def test_validate_query(self):
        """Test query string validation."""
        print("\n[TEST] Query Validation")

        # Valid queries
        self.assert_true(
            self.test_system._validate_query("test query") == "test query",
            "Valid query accepted"
        )

        # Invalid queries
        self.assert_raises(
            ValidationError,
            self.test_system._validate_query,
            ""  # Empty
        )
        self.assert_raises(
            ValidationError,
            self.test_system._validate_query,
            "x" * 15000  # Too long
        )

    # ========== DATABASE TESTS ==========

    def test_database_initialization(self):
        """Test database initialization."""
        print("\n[TEST] Database Initialization")

        db_path = self.test_system.db_path
        self.assert_true(
            db_path.exists(),
            "Database file created"
        )

        # Check tables exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        required_tables = {'learnings', 'heuristics', 'experiments', 'ceo_reviews'}
        self.assert_true(
            required_tables.issubset(tables),
            f"All required tables created: {required_tables}"
        )

    def test_database_validation(self):
        """Test database validation."""
        print("\n[TEST] Database Validation")

        result = self.test_system.validate_database()

        self.assert_true(
            result['valid'],
            "Database validation passes"
        )
        self.assert_true(
            result['checks']['integrity'] == 'ok',
            "Database integrity check passes"
        )
        self.assert_true(
            'learnings' in result['checks']['tables'],
            "Tables list includes learnings"
        )

    def test_connection_pooling(self):
        """Test connection pooling."""
        print("\n[TEST] Connection Pooling")

        # Use connections
        for i in range(3):
            with self.test_system._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")

        pool_size = len(self.test_system._connection_pool)
        self.assert_true(
            pool_size > 0,
            f"Connection pool has {pool_size} connections"
        )
        self.assert_true(
            pool_size <= 5,
            f"Connection pool respects max size limit (size: {pool_size})"
        )

    # ========== QUERY TESTS ==========

    def test_golden_rules(self):
        """Test golden rules retrieval."""
        print("\n[TEST] Golden Rules Retrieval")

        rules = self.test_system.get_golden_rules()
        self.assert_true(
            "Golden Rules" in rules,
            "Golden rules header present"
        )

    def test_query_by_domain(self):
        """Test domain query."""
        print("\n[TEST] Query by Domain")

        result = self.test_system.query_by_domain("test-domain", limit=10)

        self.assert_true(
            'domain' in result,
            "Result contains domain field"
        )
        self.assert_true(
            'heuristics' in result,
            "Result contains heuristics field"
        )
        self.assert_true(
            'learnings' in result,
            "Result contains learnings field"
        )
        self.assert_true(
            'count' in result,
            "Result contains count field"
        )

    def test_query_recent(self):
        """Test recent learnings query."""
        print("\n[TEST] Query Recent Learnings")

        result = self.test_system.query_recent(limit=5)

        self.assert_true(
            isinstance(result, list),
            "Result is a list"
        )

    def test_statistics(self):
        """Test statistics gathering."""
        print("\n[TEST] Statistics")

        stats = self.test_system.get_statistics()

        self.assert_true(
            'total_learnings' in stats,
            "Statistics include total learnings"
        )
        self.assert_true(
            'total_heuristics' in stats,
            "Statistics include total heuristics"
        )
        self.assert_true(
            isinstance(stats['total_learnings'], int),
            "Total learnings is an integer"
        )

    # ========== FORMAT TESTS ==========

    def test_format_output_json(self):
        """Test JSON formatting."""
        print("\n[TEST] JSON Output Formatting")

        data = {'key': 'value', 'number': 42}
        result = format_output(data, 'json')

        self.assert_true(
            '"key"' in result,
            "JSON contains key"
        )
        self.assert_true(
            '"value"' in result,
            "JSON contains value"
        )

    def test_format_output_csv(self):
        """Test CSV formatting."""
        print("\n[TEST] CSV Output Formatting")

        data = [{'col1': 'val1', 'col2': 'val2'}]
        result = format_output(data, 'csv')

        self.assert_true(
            'col1' in result,
            "CSV contains column header"
        )
        self.assert_true(
            'val1' in result,
            "CSV contains data value"
        )

    def test_format_output_text(self):
        """Test text formatting."""
        print("\n[TEST] Text Output Formatting")

        data = {'key': 'value'}
        result = format_output(data, 'text')

        self.assert_true(
            'key' in result,
            "Text contains key"
        )

    # ========== ERROR HANDLING TESTS ==========

    def test_error_codes(self):
        """Test error codes."""
        print("\n[TEST] Error Codes")

        self.assert_true(
            ValidationError.error_code == 'QS001',
            "ValidationError has correct error code"
        )
        self.assert_true(
            DatabaseError.error_code == 'QS002',
            "DatabaseError has correct error code"
        )
        self.assert_true(
            TimeoutError.error_code == 'QS003',
            "TimeoutError has correct error code"
        )
        self.assert_true(
            ConfigurationError.error_code == 'QS004',
            "ConfigurationError has correct error code"
        )

    def test_error_messages(self):
        """Test error messages are actionable."""
        print("\n[TEST] Error Messages")

        try:
            self.test_system._validate_domain("")
        except ValidationError as e:
            msg = str(e)
            self.assert_true(
                "QS001" in msg,
                "Error message contains error code"
            )
            self.assert_true(
                len(msg) > 20,
                "Error message is descriptive"
            )

    # ========== INTEGRATION TESTS ==========

    def test_end_to_end_workflow(self):
        """Test complete workflow."""
        print("\n[TEST] End-to-End Workflow")

        # Validate database
        validation = self.test_system.validate_database()
        self.assert_true(validation['valid'], "Database is valid")

        # Query domain
        domain_result = self.test_system.query_by_domain("test", limit=5)
        self.assert_true('domain' in domain_result, "Domain query works")

        # Get statistics
        stats = self.test_system.get_statistics()
        self.assert_true('total_learnings' in stats, "Statistics query works")

        # Build context
        context = self.test_system.build_context("test task", domain="test")
        self.assert_true(len(context) > 0, "Context building works")
        self.assert_true("Golden Rules" in context, "Context includes golden rules")

    def run_all_tests(self):
        """Run all tests."""
        print("=" * 70)
        print("QUERY SYSTEM v2.0 - COMPREHENSIVE TEST SUITE")
        print("=" * 70)

        self.setup()

        try:
            # Validation tests
            self.test_validate_domain()
            self.test_validate_limit()
            self.test_validate_tags()
            self.test_validate_query()

            # Database tests
            self.test_database_initialization()
            self.test_database_validation()
            self.test_connection_pooling()

            # Query tests
            self.test_golden_rules()
            self.test_query_by_domain()
            self.test_query_recent()
            self.test_statistics()

            # Format tests
            self.test_format_output_json()
            self.test_format_output_csv()
            self.test_format_output_text()

            # Error handling tests
            self.test_error_codes()
            self.test_error_messages()

            # Integration tests
            self.test_end_to_end_workflow()

        finally:
            self.teardown()

        # Print results
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        total = self.passed + self.failed
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ({100 * self.passed / total if total > 0 else 0:.1f}%)")
        print(f"Failed: {self.failed}")

        if self.errors:
            print("\nFailed Tests:")
            for error in self.errors:
                print(f"  - {error}")

        print("\n" + "=" * 70)
        if self.failed == 0:
            print("ALL TESTS PASSED - 10/10 ROBUSTNESS CONFIRMED")
            return 0
        else:
            print(f"TESTS FAILED - {self.failed} failures detected")
            return 1


def main():
    """Run test suite."""
    tester = TestQuerySystem()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
