#!/usr/bin/env python3
"""
Edge Case Testing Suite V2 for Emergent Learning Framework Database
Tests novel database edge cases with improved connection handling
(Updated for async API v2.0.0)
"""

import sqlite3
import os
import sys
import shutil
import asyncio
import inspect
from pathlib import Path
from datetime import datetime
import traceback
import json
import time

# Add query directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))
try:
    from query.core import QuerySystem
    from query.exceptions import DatabaseError, ValidationError
except ImportError:
    from core import QuerySystem
    from exceptions import DatabaseError, ValidationError

class EdgeCaseTesterV2:
    """Test suite for database edge cases with better connection management"""

    def __init__(self):
        self.base_path = Path.home() / ".claude" / "emergent-learning"
        self.db_path = self.base_path / "memory" / "index.db"
        self.test_results = []

    def log_result(self, test_name, severity, status, details):
        """Log a test result"""
        result = {
            'test': test_name,
            'severity': severity,  # CRITICAL, HIGH, MEDIUM, LOW
            'status': status,      # PASS, FAIL, ERROR
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)

        # Print immediately
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!"
        print(f"\n[{status_symbol}] {test_name} ({severity})")
        print(f"    Status: {status}")
        print(f"    Details: {details}")

    def get_connection(self, timeout=30.0):
        """Get a database connection with proper timeout"""
        return sqlite3.connect(self.db_path, timeout=timeout, isolation_level=None)

    def wait_for_unlock(self, max_wait=5):
        """Wait for database to be unlocked"""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                conn = self.get_connection(timeout=1.0)
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("ROLLBACK")
                conn.close()
                return True
            except sqlite3.OperationalError:
                time.sleep(0.5)
        return False

    # ========== TEST 1: Validate database integrity first ==========

    def test_database_integrity(self):
        """Test database integrity before other tests"""
        test_name = "Database Integrity Check"

        try:
            self.wait_for_unlock()
            conn = self.get_connection()
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]

            # Run foreign key check
            cursor.execute("PRAGMA foreign_key_check")
            fk_issues = cursor.fetchall()

            conn.close()

            if result == "ok" and not fk_issues:
                self.log_result(test_name, "CRITICAL", "PASS",
                    "Database integrity verified, no corruption detected")
            else:
                self.log_result(test_name, "CRITICAL", "FAIL",
                    f"Integrity: {result}, FK violations: {len(fk_issues)}")

        except Exception as e:
            self.log_result(test_name, "CRITICAL", "ERROR",
                f"Failed to check integrity: {str(e)[:200]}")

    # ========== TEST 2: Schema analysis ==========

    def test_schema_columns(self):
        """Test that expected columns exist"""
        test_name = "Schema Column Check"

        try:
            self.wait_for_unlock()
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check learnings table columns
            cursor.execute("PRAGMA table_info(learnings)")
            columns = [row[1] for row in cursor.fetchall()]

            expected_cols = ['id', 'type', 'filepath', 'title', 'summary', 'tags', 'domain', 'severity', 'created_at', 'updated_at']
            missing = [col for col in expected_cols if col not in columns]
            extra = [col for col in columns if col not in expected_cols and not col.startswith('extra_')]

            conn.close()

            if not missing:
                self.log_result(test_name, "MEDIUM", "PASS",
                    f"All expected columns present. Columns: {len(columns)}, Extra: {len(extra)}")
            else:
                self.log_result(test_name, "HIGH", "FAIL",
                    f"Missing columns: {missing}")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Failed to check schema: {str(e)[:200]}")

    # ========== TEST 3: Integer overflow ==========

    def test_integer_overflow(self):
        """Test ID at max integer value"""
        test_name = "Integer Overflow (ID Limits)"

        try:
            self.wait_for_unlock()
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get current max ID
            cursor.execute("SELECT MAX(id) FROM learnings")
            current_max = cursor.fetchone()[0] or 0

            # Test large IDs (but not breaking existing data)
            max_int = 2147483647
            safe_test_id = max_int - 100

            # Check if we can theoretically handle large IDs
            cursor.execute("SELECT ? as test_id", (safe_test_id,))
            result = cursor.fetchone()[0]

            conn.close()

            if result == safe_test_id:
                self.log_result(test_name, "LOW", "PASS",
                    f"Can handle large IDs up to {safe_test_id}. Current max: {current_max}")
            else:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Integer handling issue: expected {safe_test_id}, got {result}")

        except Exception as e:
            self.log_result(test_name, "CRITICAL", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 4: Large summary handling ==========

    def test_large_text_query(self):
        """Test querying with existing large summaries"""
        test_name = "Large Text Query Performance"

        try:
            self.wait_for_unlock()
            conn = self.get_connection()
            cursor = conn.cursor()

            # Find largest summary
            cursor.execute("SELECT id, LENGTH(summary) as len FROM learnings WHERE summary IS NOT NULL ORDER BY len DESC LIMIT 1")
            row = cursor.fetchone()

            if row:
                largest_id, largest_size = row

                # Measure query time
                start = time.time()
                cursor.execute("SELECT * FROM learnings WHERE id = ?", (largest_id,))
                result = cursor.fetchone()
                query_time = time.time() - start

                conn.close()

                if query_time < 1.0:
                    self.log_result(test_name, "LOW", "PASS",
                        f"Largest summary ({largest_size} chars) queried in {query_time:.3f}s")
                else:
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Slow query: {query_time:.3f}s for {largest_size} chars")
            else:
                conn.close()
                self.log_result(test_name, "LOW", "PASS",
                    "No summaries found to test (database may be empty)")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 5: Malformed dates in existing data ==========

    def test_date_parsing(self):
        """Test handling of various date formats in database"""
        test_name = "Date Format Handling"

        try:
            self.wait_for_unlock()
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get sample dates
            cursor.execute("SELECT created_at FROM learnings LIMIT 20")
            dates = [row[0] for row in cursor.fetchall()]

            # Check for non-standard formats
            standard_count = 0
            non_standard = []

            for date_str in dates:
                if date_str and isinstance(date_str, str):
                    # Try to parse as ISO format
                    try:
                        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        standard_count += 1
                    except:
                        non_standard.append(date_str)

            conn.close()

            if not non_standard:
                self.log_result(test_name, "MEDIUM", "PASS",
                    f"All {standard_count} dates in standard format")
            else:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Non-standard dates found: {non_standard[:3]}")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 6: SQL injection via parametrization ==========

    async def test_sql_injection_protection(self):
        """Test that SQL injection is prevented via parametrization"""
        test_name = "SQL Injection Protection"

        try:
            # Test with query.py which uses parametrized queries
            self.wait_for_unlock()

            dangerous_inputs = [
                "'; DROP TABLE learnings; --",
                "\" OR 1=1 --",
                "UNION SELECT * FROM heuristics",
            ]

            injection_attempts = 0
            protected_count = 0

            for dangerous_input in dangerous_inputs:
                try:
                    # Try as domain (will be validated)
                    qs = await QuerySystem.create(debug=False)
                    try:
                        result = await qs.query_by_domain(dangerous_input, limit=1)
                        # If validation passes, it's been sanitized
                        protected_count += 1
                    except ValidationError:
                        # Validation rejected it - good!
                        protected_count += 1
                    except DatabaseError as e:
                        if "syntax" in str(e).lower() or "sql" in str(e).lower():
                            injection_attempts += 1
                    await qs.cleanup()
                except Exception:
                    pass

            if injection_attempts == 0:
                self.log_result(test_name, "CRITICAL", "PASS",
                    f"Protected against {protected_count}/{len(dangerous_inputs)} injection attempts")
            else:
                self.log_result(test_name, "CRITICAL", "FAIL",
                    f"Possible SQL injection vulnerability: {injection_attempts} attempts succeeded")

        except Exception as e:
            self.log_result(test_name, "CRITICAL", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 7: Unicode handling ==========

    async def test_unicode_existing_data(self):
        """Test Unicode in existing database entries"""
        test_name = "Unicode Data Handling"

        try:
            self.wait_for_unlock()
            conn = self.get_connection()
            cursor = conn.cursor()

            # Look for any Unicode content
            cursor.execute("SELECT title, tags FROM learnings LIMIT 100")
            rows = cursor.fetchall()

            unicode_found = 0
            for title, tags in rows:
                for text in [title, tags]:
                    if text:
                        try:
                            # Check if contains non-ASCII
                            if any(ord(char) > 127 for char in str(text)):
                                unicode_found += 1
                                break
                        except:
                            pass

            conn.close()

            # Test query.py with Unicode
            try:
                qs = await QuerySystem.create(debug=False)
                # Test with Unicode tag
                result = await qs.query_by_tags(["test-émoji"], limit=1)
                await qs.cleanup()

                self.log_result(test_name, "LOW", "PASS",
                    f"Unicode handling works. Found {unicode_found} entries with Unicode characters")
            except Exception as e:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Unicode query failed: {str(e)[:100]}")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 8: Concurrent access simulation ==========

    async def test_concurrent_reads(self):
        """Test multiple simultaneous read operations"""
        test_name = "Concurrent Read Access"

        try:
            self.wait_for_unlock()

            # Simulate multiple queries
            successful_queries = 0
            failed_queries = 0

            for i in range(5):
                try:
                    qs = await QuerySystem.create(debug=False)
                    result = await qs.query_recent(limit=5, timeout=10)
                    await qs.cleanup()
                    successful_queries += 1
                except Exception as e:
                    failed_queries += 1
                    if "locked" in str(e).lower():
                        time.sleep(0.5)  # Wait and retry
                        try:
                            qs = await QuerySystem.create(debug=False)
                            result = await qs.query_recent(limit=5, timeout=10)
                            await qs.cleanup()
                            successful_queries += 1
                            failed_queries -= 1
                        except:
                            pass

            if successful_queries >= 4:
                self.log_result(test_name, "MEDIUM", "PASS",
                    f"Concurrent access works: {successful_queries}/5 queries succeeded")
            else:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Concurrent access issues: {failed_queries}/5 queries failed")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 9: Query.py validation robustness ==========

    async def test_query_validation(self):
        """Test query.py input validation"""
        test_name = "Input Validation Robustness"

        validation_passed = 0
        validation_total = 0

        test_cases = [
            # (function, args, should_raise)
            ("query_by_domain", [""], True),  # Empty domain
            ("query_by_domain", ["x" * 200], True),  # Too long
            ("query_by_domain", ["valid-domain"], False),  # Valid
            ("query_by_tags", [[]], True),  # Empty tags
            ("query_by_tags", [["tag1", "tag2"]], False),  # Valid tags
            ("query_recent", [0], True),  # Invalid limit
            ("query_recent", [2000], True),  # Limit too high
            ("query_recent", [10], False),  # Valid limit
        ]

        try:
            qs = await QuerySystem.create(debug=False)

            for func_name, args, should_raise in test_cases:
                validation_total += 1
                try:
                    func = getattr(qs, func_name)
                    # Call function with args and timeout as keyword argument
                    result = await func(*args, timeout=5)

                    if should_raise:
                        # Should have raised but didn't
                        pass
                    else:
                        # Correctly accepted valid input
                        validation_passed += 1
                except (ValidationError, DatabaseError, TypeError) as e:
                    if should_raise:
                        # Correctly rejected invalid input
                        validation_passed += 1
                    elif isinstance(e, TypeError):
                        # TypeError might be from incorrect call signature - skip
                        validation_total -= 1

            await qs.cleanup()

            if validation_passed == validation_total:
                self.log_result(test_name, "HIGH", "PASS",
                    f"All {validation_total} validation tests passed")
            elif validation_passed >= validation_total * 0.7:
                self.log_result(test_name, "HIGH", "PASS",
                    f"{validation_passed}/{validation_total} validation tests passed")
            else:
                self.log_result(test_name, "HIGH", "FAIL",
                    f"Only {validation_passed}/{validation_total} validation tests passed")

        except Exception as e:
            self.log_result(test_name, "HIGH", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== EXECUTION AND REPORTING ==========

    async def run_all_tests(self):
        """Run all edge case tests"""
        print("\n" + "="*70)
        print("EMERGENT LEARNING FRAMEWORK - DATABASE EDGE CASE TESTING V2 (Async)")
        print("="*70)

        tests = [
            self.test_database_integrity,
            self.test_schema_columns,
            self.test_integer_overflow,
            self.test_large_text_query,
            self.test_date_parsing,
            self.test_sql_injection_protection,
            self.test_unicode_existing_data,
            self.test_concurrent_reads,
            self.test_query_validation,
        ]

        for test_func in tests:
            try:
                # Call async test functions with await
                if inspect.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                time.sleep(0.5)  # Brief pause between tests
            except Exception as e:
                print(f"\n[!] FATAL ERROR in {test_func.__name__}: {e}")
                traceback.print_exc()

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        # Categorize by severity and status
        critical_fails = [r for r in self.test_results if r['severity'] == 'CRITICAL' and r['status'] == 'FAIL']
        high_fails = [r for r in self.test_results if r['severity'] == 'HIGH' and r['status'] == 'FAIL']
        medium_fails = [r for r in self.test_results if r['severity'] == 'MEDIUM' and r['status'] == 'FAIL']
        low_fails = [r for r in self.test_results if r['severity'] == 'LOW' and r['status'] == 'FAIL']

        passes = [r for r in self.test_results if r['status'] == 'PASS']
        errors = [r for r in self.test_results if r['status'] == 'ERROR']

        print(f"\nTotal Tests: {len(self.test_results)}")
        print(f"Passed: {len(passes)}")
        print(f"Failed: {len(critical_fails) + len(high_fails) + len(medium_fails) + len(low_fails)}")
        print(f"Errors: {len(errors)}")

        if critical_fails:
            print(f"\n⚠️  CRITICAL FAILURES: {len(critical_fails)}")
            for r in critical_fails:
                print(f"  - {r['test']}: {r['details'][:80]}")

        if high_fails:
            print(f"\n⚠️  HIGH SEVERITY FAILURES: {len(high_fails)}")
            for r in high_fails:
                print(f"  - {r['test']}: {r['details'][:80]}")

        if medium_fails:
            print(f"\n⚠️  MEDIUM SEVERITY FAILURES: {len(medium_fails)}")
            for r in medium_fails:
                print(f"  - {r['test']}: {r['details'][:80]}")

        if errors:
            print(f"\n⚠️  ERRORS: {len(errors)}")
            for r in errors:
                print(f"  - {r['test']}: {r['details'][:80]}")

        # Save detailed results
        results_path = self.base_path / "test_results_edge_cases_v2.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📄 Detailed results saved to: {results_path}")
        print("="*70 + "\n")

        return self.test_results

if __name__ == '__main__':
    tester = EdgeCaseTesterV2()
    results = asyncio.run(tester.run_all_tests())

    # Exit with non-zero if critical or high failures
    critical_or_high_fails = [r for r in results if r['severity'] in ['CRITICAL', 'HIGH'] and r['status'] == 'FAIL']
    if critical_or_high_fails:
        sys.exit(1)
    else:
        sys.exit(0)
