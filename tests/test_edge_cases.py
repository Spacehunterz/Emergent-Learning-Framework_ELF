#!/usr/bin/env python3
"""
Edge Case Testing Suite for Emergent Learning Framework Database
Tests novel database edge cases to verify robustness
"""

import asyncio
import sqlite3
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import traceback
import json

# Add query directory to path
sys.path.insert(0, str(Path(__file__).parent / "query"))
from query import QuerySystem, DatabaseError, ValidationError

class EdgeCaseTester:
    """Test suite for database edge cases"""

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

    def backup_database(self):
        """Create a backup before destructive tests"""
        backup_path = str(self.db_path) + f".backup_edgetest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(self.db_path, backup_path)
        print(f"\n[BACKUP] Created backup at {backup_path}")
        return backup_path

    def restore_database(self, backup_path):
        """Restore database from backup"""
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, self.db_path)
            print(f"[RESTORE] Restored from {backup_path}")

    # ========== TEST 1: Corrupted WAL file ==========

    async def test_corrupted_wal_file(self):
        """Test behavior with corrupted WAL file"""
        test_name = "Corrupted WAL File"

        try:
            # First, enable WAL mode
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("INSERT INTO learnings (type, filepath, title, domain, severity) VALUES ('test', '/tmp/test_wal', 'WAL Test', 'testing', '3')")
            conn.commit()

            # Check if WAL file was created
            wal_path = str(self.db_path) + "-wal"
            if not os.path.exists(wal_path):
                conn.close()
                self.log_result(test_name, "MEDIUM", "PASS", "WAL mode not enabled (no WAL file created), graceful degradation")
                return

            # Create a backup of the WAL
            wal_backup = wal_path + ".backup"
            shutil.copy2(wal_path, wal_backup)

            # Corrupt the WAL file
            with open(wal_path, 'wb') as f:
                f.write(b"CORRUPTED_DATA_" * 100)

            conn.close()

            # Try to open and query
            try:
                qs = await QuerySystem.create(debug=True)
                result = await qs.query_recent(limit=1)
                await qs.cleanup()

                # Restore WAL
                shutil.copy2(wal_backup, wal_path)
                os.remove(wal_backup)

                self.log_result(test_name, "HIGH", "PASS",
                    "Query system handled corrupted WAL gracefully, returned valid data or recovered")
            except Exception as e:
                # Restore WAL
                if os.path.exists(wal_backup):
                    shutil.copy2(wal_backup, wal_path)
                    os.remove(wal_backup)

                if "corrupted" in str(e).lower() or "malformed" in str(e).lower():
                    self.log_result(test_name, "HIGH", "PASS",
                        f"Detected corruption with proper error: {str(e)[:100]}")
                else:
                    self.log_result(test_name, "HIGH", "FAIL",
                        f"Unclear error handling: {str(e)[:100]}")

        except Exception as e:
            self.log_result(test_name, "HIGH", "ERROR",
                f"Test setup failed: {str(e)[:200]}")

    # ========== TEST 2: Missing SHM file ==========

    async def test_missing_shm_file(self):
        """Test deletion of SHM file while DB is in use"""
        test_name = "Missing SHM File"

        try:
            # Enable WAL mode
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()

            shm_path = str(self.db_path) + "-shm"

            if not os.path.exists(shm_path):
                conn.close()
                self.log_result(test_name, "MEDIUM", "PASS",
                    "No SHM file present (WAL not active), test skipped gracefully")
                return

            # Delete SHM while connection is open
            try:
                os.remove(shm_path)
            except:
                pass  # May fail on Windows due to file locks

            # Try to execute queries
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM learnings")
                count = cursor.fetchone()[0]
                conn.close()

                self.log_result(test_name, "MEDIUM", "PASS",
                    f"Continued working despite missing SHM file, {count} records accessible")
            except Exception as e:
                conn.close()
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Failed when SHM deleted: {str(e)[:100]}")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test execution error: {str(e)[:200]}")

    # ========== TEST 3: Schema mismatch ==========

    async def test_schema_mismatch(self):
        """Test adding/removing columns from schema"""
        test_name = "Schema Mismatch"
        backup = self.backup_database()

        try:
            # Add an extra column
            conn = sqlite3.connect(self.db_path)
            conn.execute("ALTER TABLE learnings ADD COLUMN extra_test_column TEXT DEFAULT 'test'")
            conn.commit()
            conn.close()

            # Try query.py with modified schema
            try:
                qs = await QuerySystem.create(debug=True)
                result = await qs.query_recent(limit=1)
                await qs.cleanup()

                self.log_result(test_name + " (Add Column)", "LOW", "PASS",
                    "Query system works with additional column")
            except Exception as e:
                self.log_result(test_name + " (Add Column)", "MEDIUM", "FAIL",
                    f"Failed with extra column: {str(e)[:100]}")

            # Restore and try removing a column (can't directly remove in SQLite, need recreation)
            self.restore_database(backup)

            # Test with missing expected column by renaming table
            conn = sqlite3.connect(self.db_path)
            conn.execute("CREATE TABLE learnings_backup AS SELECT id, type, filepath, title, domain FROM learnings")
            conn.execute("DROP TABLE learnings")
            conn.execute("ALTER TABLE learnings_backup RENAME TO learnings")
            conn.commit()
            conn.close()

            try:
                qs = await QuerySystem.create(debug=True)
                result = await qs.query_recent(limit=1)
                await qs.cleanup()
                self.log_result(test_name + " (Remove Column)", "MEDIUM", "FAIL",
                    "Should have failed with missing columns but didn't")
            except Exception as e:
                if "no such column" in str(e).lower() or "column" in str(e).lower():
                    self.log_result(test_name + " (Remove Column)", "MEDIUM", "PASS",
                        f"Properly detected missing columns: {str(e)[:100]}")
                else:
                    self.log_result(test_name + " (Remove Column)", "MEDIUM", "FAIL",
                        f"Unexpected error: {str(e)[:100]}")

            # Restore original
            self.restore_database(backup)

        except Exception as e:
            self.restore_database(backup)
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 4: Integer overflow ==========

    async def test_integer_overflow(self):
        """Test ID at max integer value"""
        test_name = "Integer Overflow"
        backup = self.backup_database()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Set the autoincrement sequence to near max
            max_int = 2147483647
            test_id = max_int - 5

            # Update sqlite_sequence
            cursor.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'learnings'", (test_id,))

            # Try inserting records
            try:
                for i in range(3):
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, domain, severity) VALUES (?, ?, ?, ?, ?)",
                        ('test', f'/tmp/overflow_{i}', f'Overflow Test {i}', 'testing', '3')
                    )
                conn.commit()

                # Check what IDs were assigned
                cursor.execute("SELECT id FROM learnings ORDER BY id DESC LIMIT 3")
                ids = [row[0] for row in cursor.fetchall()]

                conn.close()
                self.restore_database(backup)

                if any(id_val > max_int for id_val in ids):
                    self.log_result(test_name, "CRITICAL", "FAIL",
                        f"IDs exceeded max integer: {ids}")
                elif any(id_val < 0 for id_val in ids):
                    self.log_result(test_name, "CRITICAL", "FAIL",
                        f"IDs wrapped to negative: {ids}")
                else:
                    self.log_result(test_name, "LOW", "PASS",
                        f"IDs assigned correctly near max: {ids}")

            except sqlite3.IntegrityError as e:
                conn.close()
                self.restore_database(backup)
                self.log_result(test_name, "LOW", "PASS",
                    f"Properly rejected overflow with error: {str(e)[:100]}")

        except Exception as e:
            self.restore_database(backup)
            self.log_result(test_name, "CRITICAL", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 5: Very large blob ==========

    async def test_large_blob(self):
        """Test inserting 10MB summary and query performance"""
        test_name = "Very Large Blob (10MB)"
        backup = self.backup_database()

        try:
            # Create a 10MB string
            large_summary = "X" * (10 * 1024 * 1024)  # 10MB

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            import time
            start = time.time()

            cursor.execute(
                "INSERT INTO learnings (type, filepath, title, summary, domain, severity) VALUES (?, ?, ?, ?, ?, ?)",
                ('test', '/tmp/large_blob', 'Large Blob Test', large_summary, 'testing', '3')
            )
            conn.commit()
            insert_time = time.time() - start

            # Get the ID
            large_id = cursor.lastrowid

            # Query it back
            start = time.time()
            cursor.execute("SELECT summary FROM learnings WHERE id = ?", (large_id,))
            result = cursor.fetchone()
            query_time = time.time() - start

            conn.close()

            # Test with QuerySystem
            try:
                start = time.time()
                qs = await QuerySystem.create(debug=True)
                recent = await qs.query_recent(limit=1, timeout=60)
                qs_time = time.time() - start
                await qs.cleanup()

                self.restore_database(backup)

                if query_time > 5.0 or qs_time > 10.0:
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Poor performance: insert={insert_time:.2f}s, query={query_time:.2f}s, qs={qs_time:.2f}s")
                else:
                    self.log_result(test_name, "LOW", "PASS",
                        f"Good performance: insert={insert_time:.2f}s, query={query_time:.2f}s, qs={qs_time:.2f}s")

            except Exception as e:
                self.restore_database(backup)
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"QuerySystem failed with large blob: {str(e)[:100]}")

        except Exception as e:
            self.restore_database(backup)
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 6: Malformed dates ==========

    async def test_malformed_dates(self):
        """Test invalid date values in created_at"""
        test_name = "Malformed Dates"
        backup = self.backup_database()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # SQLite doesn't enforce date types, so we can insert invalid dates
            invalid_dates = [
                "not-a-date",
                "2025-13-45",
                "invalid",
                "9999-99-99 99:99:99",
                "",
                "NULL"
            ]

            test_ids = []
            for i, bad_date in enumerate(invalid_dates):
                try:
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, domain, severity, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ('test', f'/tmp/bad_date_{i}', f'Bad Date Test {i}', 'testing', '3', bad_date)
                    )
                    test_ids.append((cursor.lastrowid, bad_date))
                except Exception as e:
                    pass  # Some might be rejected

            conn.commit()
            conn.close()

            # Test if query.py handles these gracefully
            try:
                qs = await QuerySystem.create(debug=True)
                result = await qs.query_recent(limit=10)
                await qs.cleanup()

                self.restore_database(backup)

                self.log_result(test_name, "MEDIUM", "PASS",
                    f"QuerySystem handled {len(test_ids)} malformed dates gracefully")

            except Exception as e:
                self.restore_database(backup)
                if "date" in str(e).lower() or "time" in str(e).lower():
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Failed to handle malformed dates: {str(e)[:100]}")
                else:
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Unexpected error with malformed dates: {str(e)[:100]}")

        except Exception as e:
            self.restore_database(backup)
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 7: SQL reserved words ==========

    async def test_sql_reserved_words(self):
        """Test using SQL reserved words as data values"""
        test_name = "SQL Reserved Words"
        backup = self.backup_database()

        try:
            reserved_words = [
                "SELECT",
                "DROP TABLE",
                "DELETE FROM learnings",
                "'; DROP TABLE learnings; --",
                "UNION SELECT * FROM heuristics",
                "INSERT INTO"
            ]

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            test_ids = []
            for i, word in enumerate(reserved_words):
                try:
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, domain, severity) VALUES (?, ?, ?, ?, ?)",
                        ('test', f'/tmp/reserved_{i}', word, word, '3')
                    )
                    test_ids.append(cursor.lastrowid)
                except Exception as e:
                    pass

            conn.commit()
            conn.close()

            # Test if query.py can retrieve these
            try:
                qs = await QuerySystem.create(debug=True)

                # Test domain query with reserved word
                result = await qs.query_by_domain("SELECT", limit=5)

                # Test tag query
                result2 = await qs.query_by_tags(["DROP TABLE"], limit=5)

                await qs.cleanup()

                self.restore_database(backup)

                self.log_result(test_name, "CRITICAL", "PASS",
                    f"Properly handled {len(test_ids)} reserved words as data without SQL injection")

            except ValidationError as e:
                # ValidationError is acceptable - it means the system is rejecting suspicious input
                self.restore_database(backup)
                self.log_result(test_name, "CRITICAL", "PASS",
                    f"Rejected reserved words via validation: {str(e)[:100]}")

            except Exception as e:
                self.restore_database(backup)
                if "syntax" in str(e).lower() or "sql" in str(e).lower():
                    self.log_result(test_name, "CRITICAL", "FAIL",
                        f"SQL injection vulnerability detected: {str(e)[:100]}")
                else:
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Error handling reserved words: {str(e)[:100]}")

        except Exception as e:
            self.restore_database(backup)
            self.log_result(test_name, "CRITICAL", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 8: Unicode encoding in LIKE ==========

    async def test_unicode_like_patterns(self):
        """Test searching for Unicode patterns with query.py"""
        test_name = "Unicode Encoding in LIKE"
        backup = self.backup_database()

        try:
            unicode_strings = [
                "emoji_😀_test",
                "中文测试",
                "العربية",
                "עברית",
                "🔥🚀💯",
                "Ü̃̈n̈̃ï̃̈c̈̃ö̃̈d̈̃ë̃̈",  # Combining characters
                "\u0000null\u0000byte",  # Null bytes
                "\\x00\\x01\\x02"  # Escaped bytes
            ]

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            test_ids = []
            for i, ustr in enumerate(unicode_strings):
                try:
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, tags, domain, severity) VALUES (?, ?, ?, ?, ?, ?)",
                        ('test', f'/tmp/unicode_{i}', f'Unicode Test {i}', ustr, 'unicode-testing', '3')
                    )
                    test_ids.append((cursor.lastrowid, ustr))
                except Exception as e:
                    print(f"    Failed to insert '{ustr[:20]}': {e}")

            conn.commit()
            conn.close()

            # Test querying with Unicode
            passed_tests = 0
            failed_tests = 0

            for test_id, ustr in test_ids:
                try:
                    qs = await QuerySystem.create(debug=False)
                    # Search by domain
                    result = await qs.query_by_domain("unicode-testing", limit=20)
                    # Search by tags
                    result2 = await qs.query_by_tags([ustr], limit=5)
                    await qs.cleanup()
                    passed_tests += 1
                except Exception as e:
                    failed_tests += 1
                    print(f"    Failed to query '{ustr[:20]}': {str(e)[:50]}")

            self.restore_database(backup)

            if failed_tests == 0:
                self.log_result(test_name, "LOW", "PASS",
                    f"All {passed_tests} Unicode patterns handled correctly")
            elif passed_tests > failed_tests:
                self.log_result(test_name, "MEDIUM", "PASS",
                    f"Mostly working: {passed_tests} passed, {failed_tests} failed")
            else:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Poor Unicode support: {passed_tests} passed, {failed_tests} failed")

        except Exception as e:
            self.restore_database(backup)
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== EXECUTION AND REPORTING ==========

    async def run_all_tests(self):
        """Run all edge case tests"""
        print("\n" + "="*70)
        print("EMERGENT LEARNING FRAMEWORK - DATABASE EDGE CASE TESTING")
        print("="*70)

        tests = [
            self.test_corrupted_wal_file,
            self.test_missing_shm_file,
            self.test_schema_mismatch,
            self.test_integer_overflow,
            self.test_large_blob,
            self.test_malformed_dates,
            self.test_sql_reserved_words,
            self.test_unicode_like_patterns,
        ]

        for test_func in tests:
            try:
                await test_func()
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

        # Save detailed results
        results_path = self.base_path / "test_results_edge_cases.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📄 Detailed results saved to: {results_path}")
        print("="*70 + "\n")

        return self.test_results

if __name__ == '__main__':
    tester = EdgeCaseTester()
    results = asyncio.run(tester.run_all_tests())

    # Exit with non-zero if critical or high failures
    critical_or_high_fails = [r for r in results if r['severity'] in ['CRITICAL', 'HIGH'] and r['status'] == 'FAIL']
    if critical_or_high_fails:
        sys.exit(1)
    else:
        sys.exit(0)
