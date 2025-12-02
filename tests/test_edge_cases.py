#!/usr/bin/env python3
"""
Edge Case Testing Suite for query.py
Tests 10 novel edge cases to find breaking points.
"""

import sys
import os
import sqlite3
import shutil
import subprocess
import json
import time
import tempfile
from pathlib import Path
from threading import Thread
from queue import Queue
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))
from query import QuerySystem, QuerySystemError, DatabaseError, ValidationError, TimeoutError as QueryTimeoutError

class EdgeCaseTestRunner:
    """Test runner for edge cases."""

    def __init__(self):
        self.results = []
        self.test_base = Path(tempfile.mkdtemp(prefix="test_query_"))
        self.test_memory = self.test_base / "memory"
        self.test_db = self.test_memory / "index.db"

    def setup(self):
        """Set up test environment."""
        self.test_memory.mkdir(parents=True, exist_ok=True)

    def cleanup(self):
        """Clean up test environment."""
        if self.test_base.exists():
            shutil.rmtree(self.test_base)

    def log_result(self, test_name, severity, status, details, error=None):
        """Log a test result."""
        result = {
            'test': test_name,
            'severity': severity,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        if error:
            result['error'] = str(error)
        self.results.append(result)

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("EDGE CASE TEST RESULTS")
        print("="*80 + "\n")

        critical_failures = 0
        high_failures = 0
        medium_failures = 0
        low_failures = 0
        passes = 0

        for result in self.results:
            status_symbol = "✓" if result['status'] == 'PASS' else "✗"
            print(f"{status_symbol} [{result['severity']}] {result['test']}: {result['status']}")
            print(f"   Details: {result['details']}")
            if 'error' in result:
                print(f"   Error: {result['error']}")
            print()

            if result['status'] == 'PASS':
                passes += 1
            elif result['severity'] == 'CRITICAL':
                critical_failures += 1
            elif result['severity'] == 'HIGH':
                high_failures += 1
            elif result['severity'] == 'MEDIUM':
                medium_failures += 1
            else:
                low_failures += 1

        print("="*80)
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passes}")
        print(f"Failed: {len(self.results) - passes}")
        print(f"  Critical: {critical_failures}")
        print(f"  High: {high_failures}")
        print(f"  Medium: {medium_failures}")
        print(f"  Low: {low_failures}")
        print("="*80)

        return critical_failures, high_failures, medium_failures, low_failures

    # ========== TEST 1: Empty Database ==========
    def test_1_empty_database(self):
        """Test behavior with 0 rows in learnings table."""
        print("\n[TEST 1] Testing empty database...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Query empty database
            results = qs.query_recent(limit=10)

            if results == []:
                self.log_result(
                    "Empty Database",
                    "LOW",
                    "PASS",
                    "Returns empty list for empty database"
                )
            else:
                self.log_result(
                    "Empty Database",
                    "MEDIUM",
                    "FAIL",
                    f"Expected empty list, got {results}"
                )

            # Test domain query on empty DB
            domain_results = qs.query_by_domain("test", limit=10)
            if domain_results['learnings'] == [] and domain_results['heuristics'] == []:
                self.log_result(
                    "Empty Database - Domain Query",
                    "LOW",
                    "PASS",
                    "Domain query returns empty results gracefully"
                )
            else:
                self.log_result(
                    "Empty Database - Domain Query",
                    "MEDIUM",
                    "FAIL",
                    f"Expected empty results, got {domain_results}"
                )

            # Test stats on empty DB
            stats = qs.get_statistics()
            if stats['total_learnings'] == 0:
                self.log_result(
                    "Empty Database - Statistics",
                    "LOW",
                    "PASS",
                    "Statistics correctly show 0 learnings"
                )
            else:
                self.log_result(
                    "Empty Database - Statistics",
                    "MEDIUM",
                    "FAIL",
                    f"Expected 0 learnings, got {stats['total_learnings']}"
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Empty Database",
                "HIGH",
                "FAIL",
                "Exception raised on empty database",
                error=e
            )

    # ========== TEST 2: Missing Tables ==========
    def test_2_missing_tables(self):
        """Test behavior when learnings table is dropped."""
        print("\n[TEST 2] Testing missing tables...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Drop learnings table
            with qs._get_connection() as conn:
                conn.execute("DROP TABLE IF EXISTS learnings")
                conn.commit()

            # Try to query
            try:
                results = qs.query_recent(limit=10)
                self.log_result(
                    "Missing Tables",
                    "HIGH",
                    "FAIL",
                    f"No error raised when table missing. Got: {results}"
                )
            except DatabaseError as e:
                if "QS002" in str(e):
                    self.log_result(
                        "Missing Tables",
                        "HIGH",
                        "PASS",
                        f"Proper DatabaseError raised: {e}"
                    )
                else:
                    self.log_result(
                        "Missing Tables",
                        "MEDIUM",
                        "PASS",
                        f"Error raised but missing error code: {e}"
                    )
            except Exception as e:
                self.log_result(
                    "Missing Tables",
                    "MEDIUM",
                    "FAIL",
                    f"Wrong exception type: {type(e).__name__}",
                    error=e
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Missing Tables",
                "CRITICAL",
                "FAIL",
                "Test setup failed",
                error=e
            )

    # ========== TEST 3: Orphaned Files ==========
    def test_3_orphaned_files(self):
        """Test markdown file exists but no DB record."""
        print("\n[TEST 3] Testing orphaned files...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Create orphaned markdown file
            orphan_dir = self.test_memory / "failures"
            orphan_dir.mkdir(parents=True, exist_ok=True)
            orphan_file = orphan_dir / "orphan_failure.md"

            with open(orphan_file, 'w', encoding='utf-8') as f:
                f.write("# Orphaned Failure\n\nThis has no DB record.")

            # Query - should not crash
            results = qs.query_recent(limit=10)

            self.log_result(
                "Orphaned Files",
                "MEDIUM",
                "PASS",
                f"System handles orphaned files gracefully. Found {len(results)} records."
            )

            # Check validation
            validation = qs.validate_database()
            if validation['valid']:
                self.log_result(
                    "Orphaned Files - Validation",
                    "LOW",
                    "PASS",
                    "Database validation still passes with orphaned files"
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Orphaned Files",
                "MEDIUM",
                "FAIL",
                "Exception with orphaned files",
                error=e
            )

    # ========== TEST 4: Orphaned Records ==========
    def test_4_orphaned_records(self):
        """Test DB record exists but no markdown file."""
        print("\n[TEST 4] Testing orphaned records...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Insert record pointing to non-existent file
            with qs._get_connection() as conn:
                conn.execute("""
                    INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'failure',
                    str(self.test_memory / "nonexistent" / "fake.md"),
                    'Orphaned Record',
                    'This file does not exist',
                    'orphan,test',
                    'testing'
                ))
                conn.commit()

            # Query - should return the record
            results = qs.query_recent(limit=10)

            if len(results) > 0 and results[0]['title'] == 'Orphaned Record':
                self.log_result(
                    "Orphaned Records",
                    "MEDIUM",
                    "PASS",
                    f"System returns orphaned records without crashing. Record: {results[0]['filepath']}"
                )
            else:
                self.log_result(
                    "Orphaned Records",
                    "LOW",
                    "FAIL",
                    f"Expected orphaned record in results. Got: {results}"
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Orphaned Records",
                "HIGH",
                "FAIL",
                "Exception with orphaned records",
                error=e
            )

    # ========== TEST 5: Circular References ==========
    def test_5_circular_references(self):
        """Test learning that references itself."""
        print("\n[TEST 5] Testing circular references...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Insert self-referencing record
            with qs._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'failure',
                    str(self.test_memory / "circular.md"),
                    'Circular Reference',
                    'Related to learning ID 1',
                    'circular,self-reference',
                    'testing'
                ))
                learning_id = cursor.lastrowid

                # Update to reference itself in summary
                conn.execute("""
                    UPDATE learnings
                    SET summary = ?
                    WHERE id = ?
                """, (f"Related to learning ID {learning_id}", learning_id))
                conn.commit()

            # Query - should handle gracefully
            results = qs.query_recent(limit=10)

            if len(results) > 0:
                self.log_result(
                    "Circular References",
                    "LOW",
                    "PASS",
                    f"System handles circular references. Retrieved {len(results)} records."
                )
            else:
                self.log_result(
                    "Circular References",
                    "MEDIUM",
                    "FAIL",
                    "No results returned for circular reference query"
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Circular References",
                "MEDIUM",
                "FAIL",
                "Exception with circular references",
                error=e
            )

    # ========== TEST 6: Very Deep Nesting ==========
    def test_6_deep_nesting(self):
        """Test 100 chained related learnings."""
        print("\n[TEST 6] Testing very deep nesting (100 records)...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Insert 100 chained records
            start_time = time.time()
            with qs._get_connection() as conn:
                for i in range(100):
                    conn.execute("""
                        INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        'failure',
                        str(self.test_memory / f"chain_{i}.md"),
                        f'Chain Link {i}',
                        f'Related to chain link {i-1}' if i > 0 else 'Root',
                        f'chain,link-{i}',
                        'testing'
                    ))
                conn.commit()
            insert_time = time.time() - start_time

            # Query all
            start_time = time.time()
            results = qs.query_recent(limit=100)
            query_time = time.time() - start_time

            if len(results) == 100:
                self.log_result(
                    "Deep Nesting",
                    "MEDIUM",
                    "PASS",
                    f"Successfully handled 100 chained records. Insert: {insert_time:.3f}s, Query: {query_time:.3f}s"
                )
            else:
                self.log_result(
                    "Deep Nesting",
                    "HIGH",
                    "FAIL",
                    f"Expected 100 records, got {len(results)}. Query time: {query_time:.3f}s"
                )

            # Test with higher limit
            try:
                big_results = qs.query_recent(limit=1000)
                self.log_result(
                    "Deep Nesting - Max Limit",
                    "LOW",
                    "PASS",
                    f"Max limit (1000) query succeeded. Retrieved {len(big_results)} records."
                )
            except Exception as e:
                self.log_result(
                    "Deep Nesting - Max Limit",
                    "MEDIUM",
                    "FAIL",
                    "Failed with max limit",
                    error=e
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Deep Nesting",
                "HIGH",
                "FAIL",
                "Exception during deep nesting test",
                error=e
            )

    # ========== TEST 7: Concurrent Reads ==========
    def test_7_concurrent_reads(self):
        """Test 10 parallel query.py threads."""
        print("\n[TEST 7] Testing concurrent reads (10 parallel threads)...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Populate database
            with qs._get_connection() as conn:
                for i in range(20):
                    conn.execute("""
                        INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        'success',
                        str(self.test_memory / f"test_{i}.md"),
                        f'Test Record {i}',
                        f'Test summary {i}',
                        'concurrent,test',
                        'testing'
                    ))
                conn.commit()

            qs.cleanup()

            # Run concurrent queries using threads
            results = []

            def run_query(idx):
                try:
                    qs_thread = QuerySystem(base_path=str(self.test_base), debug=False)
                    query_results = qs_thread.query_recent(limit=10)
                    qs_thread.cleanup()
                    results.append({'id': idx, 'success': True, 'count': len(query_results)})
                except Exception as e:
                    results.append({'id': idx, 'success': False, 'error': str(e)})

            threads = []

            start_time = time.time()
            for i in range(10):
                t = Thread(target=run_query, args=(i,))
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=30)

            duration = time.time() - start_time

            successes = sum(1 for r in results if r.get('success', False))
            failures = len(results) - successes

            if successes == 10:
                self.log_result(
                    "Concurrent Reads",
                    "HIGH",
                    "PASS",
                    f"All 10 concurrent threads succeeded in {duration:.3f}s. No deadlocks."
                )
            elif successes > 5:
                self.log_result(
                    "Concurrent Reads",
                    "MEDIUM",
                    "PARTIAL",
                    f"{successes}/10 threads succeeded in {duration:.3f}s. {failures} failures."
                )
            else:
                self.log_result(
                    "Concurrent Reads",
                    "CRITICAL",
                    "FAIL",
                    f"Only {successes}/10 threads succeeded. {failures} failures.",
                    error=f"Failed threads: {[r for r in results if not r.get('success')]}"
                )

        except Exception as e:
            self.log_result(
                "Concurrent Reads",
                "CRITICAL",
                "FAIL",
                "Exception during concurrency test",
                error=e
            )

    # ========== TEST 8: Memory Limits ==========
    def test_8_memory_limits(self):
        """Test query returning 10000 results."""
        print("\n[TEST 8] Testing memory limits (attempting 10000 records)...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Try to query 10000 records (should hit validation limit)
            try:
                results = qs.query_recent(limit=10000)
                self.log_result(
                    "Memory Limits",
                    "HIGH",
                    "FAIL",
                    f"Validation should reject limit=10000. Got {len(results)} results."
                )
            except ValidationError as e:
                if "QS001" in str(e) and "1000" in str(e):
                    self.log_result(
                        "Memory Limits - Validation",
                        "HIGH",
                        "PASS",
                        f"Properly rejected limit=10000 with ValidationError: {e}"
                    )
                else:
                    self.log_result(
                        "Memory Limits - Validation",
                        "MEDIUM",
                        "PARTIAL",
                        f"ValidationError raised but message unclear: {e}"
                    )

            # Test max allowed limit (1000)
            with qs._get_connection() as conn:
                for i in range(50):
                    conn.execute("""
                        INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        'test',
                        str(self.test_memory / f"large_{i}.md"),
                        f'Large Dataset {i}',
                        'A' * 1000,  # 1KB summary
                        'large,memory',
                        'testing'
                    ))
                conn.commit()

            start_time = time.time()
            results = qs.query_recent(limit=1000)
            query_time = time.time() - start_time

            if len(results) <= 1000:
                self.log_result(
                    "Memory Limits - Max Allowed",
                    "MEDIUM",
                    "PASS",
                    f"Max limit (1000) handled correctly. Retrieved {len(results)} in {query_time:.3f}s"
                )
            else:
                self.log_result(
                    "Memory Limits - Max Allowed",
                    "HIGH",
                    "FAIL",
                    f"Retrieved more than limit: {len(results)} records"
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Memory Limits",
                "HIGH",
                "FAIL",
                "Exception during memory limit test",
                error=e
            )

    # ========== TEST 9: Timeout Behavior ==========
    def test_9_timeout(self):
        """Test if --timeout actually works."""
        print("\n[TEST 9] Testing timeout behavior...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Insert many records to make query slower
            with qs._get_connection() as conn:
                for i in range(500):
                    conn.execute("""
                        INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        'test',
                        str(self.test_memory / f"timeout_{i}.md"),
                        f'Timeout Test {i}',
                        'X' * 5000,  # 5KB summary
                        'timeout,test',
                        'testing'
                    ))
                conn.commit()

            # Test with very short timeout (Windows doesn't support signal-based timeout)
            if sys.platform != 'win32':
                try:
                    start_time = time.time()
                    results = qs.query_recent(limit=1000, timeout=1)
                    duration = time.time() - start_time

                    if duration > 5:
                        self.log_result(
                            "Timeout Behavior",
                            "HIGH",
                            "FAIL",
                            f"Query took {duration:.3f}s, timeout=1 not enforced"
                        )
                    else:
                        self.log_result(
                            "Timeout Behavior",
                            "LOW",
                            "PASS",
                            f"Query completed in {duration:.3f}s (fast enough that timeout wasn't needed)"
                        )
                except QueryTimeoutError as e:
                    if "QS003" in str(e):
                        self.log_result(
                            "Timeout Behavior",
                            "HIGH",
                            "PASS",
                            f"Timeout properly enforced with TimeoutError: {e}"
                        )
                    else:
                        self.log_result(
                            "Timeout Behavior",
                            "MEDIUM",
                            "PARTIAL",
                            f"Timeout error raised but missing code: {e}"
                        )
            else:
                self.log_result(
                    "Timeout Behavior",
                    "LOW",
                    "SKIP",
                    "Windows doesn't support signal-based timeouts. Would need threading implementation."
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Timeout Behavior",
                "MEDIUM",
                "FAIL",
                "Exception during timeout test",
                error=e
            )

    # ========== TEST 10: Invalid JSON in Tags ==========
    def test_10_invalid_json_tags(self):
        """Test malformed JSON in tags column."""
        print("\n[TEST 10] Testing invalid JSON in tags column...")

        try:
            qs = QuerySystem(base_path=str(self.test_base), debug=True)

            # Insert records with various malformed tags
            malformed_tags = [
                '{"unclosed": "quote',
                '[invalid,json]',
                'not json at all',
                '{"key": undefined}',
                '\\x00\\x01\\x02',
                '',
                None
            ]

            with qs._get_connection() as conn:
                for i, bad_tag in enumerate(malformed_tags):
                    conn.execute("""
                        INSERT INTO learnings (type, filepath, title, summary, tags, domain)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        'test',
                        str(self.test_memory / f"bad_tags_{i}.md"),
                        f'Bad Tags {i}',
                        'Testing malformed tags',
                        bad_tag,
                        'testing'
                    ))
                conn.commit()

            # Try to query - should handle gracefully
            try:
                results = qs.query_recent(limit=10)

                if len(results) > 0:
                    self.log_result(
                        "Invalid JSON Tags",
                        "MEDIUM",
                        "PASS",
                        f"System handles malformed tags gracefully. Retrieved {len(results)} records."
                    )

                    # Check if tags are returned as-is
                    for r in results:
                        if r.get('tags') in malformed_tags:
                            self.log_result(
                                "Invalid JSON Tags - Data Integrity",
                                "LOW",
                                "PASS",
                                f"Tags stored/retrieved as-is: '{r.get('tags')}'"
                            )
                            break
                else:
                    self.log_result(
                        "Invalid JSON Tags",
                        "LOW",
                        "FAIL",
                        "No results returned"
                    )

            except Exception as e:
                self.log_result(
                    "Invalid JSON Tags",
                    "HIGH",
                    "FAIL",
                    "Exception when querying records with bad tags",
                    error=e
                )

            # Try tag-based query
            try:
                tag_results = qs.query_by_tags(['test', 'malformed'], limit=10)
                self.log_result(
                    "Invalid JSON Tags - Tag Query",
                    "LOW",
                    "PASS",
                    f"Tag-based query handles malformed tags. Found {len(tag_results)} results."
                )
            except Exception as e:
                self.log_result(
                    "Invalid JSON Tags - Tag Query",
                    "MEDIUM",
                    "FAIL",
                    "Exception during tag-based query",
                    error=e
                )

            qs.cleanup()

        except Exception as e:
            self.log_result(
                "Invalid JSON Tags",
                "MEDIUM",
                "FAIL",
                "Exception during invalid JSON test",
                error=e
            )

    def run_all_tests(self):
        """Run all edge case tests."""
        print("="*80)
        print("STARTING EDGE CASE TEST SUITE")
        print("="*80)

        try:
            self.setup()

            self.test_1_empty_database()
            self.test_2_missing_tables()
            self.test_3_orphaned_files()
            self.test_4_orphaned_records()
            self.test_5_circular_references()
            self.test_6_deep_nesting()
            self.test_7_concurrent_reads()
            self.test_8_memory_limits()
            self.test_9_timeout()
            self.test_10_invalid_json_tags()

        finally:
            self.cleanup()

        return self.print_summary()


if __name__ == '__main__':
    runner = EdgeCaseTestRunner()
    critical, high, medium, low = runner.run_all_tests()

    # Exit with appropriate code
    if critical > 0:
        sys.exit(2)
    elif high > 0:
        sys.exit(1)
    else:
        sys.exit(0)
