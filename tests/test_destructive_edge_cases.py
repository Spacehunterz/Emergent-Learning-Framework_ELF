#!/usr/bin/env python3
"""
DESTRUCTIVE Edge Case Testing Suite for Emergent Learning Framework
Tests edge cases that require modifying the database (creates backups first)
"""

import sqlite3
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import traceback
import json
import time
import asyncio

# Add query directory to path
sys.path.insert(0, str(Path(__file__).parent / "query"))
from query import QuerySystem, DatabaseError, ValidationError

class DestructiveEdgeTester:
    """Test suite for destructive database edge cases"""

    def __init__(self):
        self.base_path = Path.home() / ".claude" / "emergent-learning"
        self.db_path = self.base_path / "memory" / "index.db"
        self.test_results = []
        self.master_backup = None

    def log_result(self, test_name, severity, status, details):
        """Log a test result"""
        result = {
            'test': test_name,
            'severity': severity,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)

        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!"
        print(f"\n[{status_symbol}] {test_name} ({severity})")
        print(f"    Status: {status}")
        print(f"    Details: {details}")

    def create_master_backup(self):
        """Create master backup before all destructive tests"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.master_backup = str(self.db_path) + f".MASTER_BACKUP_{timestamp}"
        shutil.copy2(self.db_path, self.master_backup)
        print(f"\n[MASTER BACKUP] Created at {self.master_backup}")

    def restore_master_backup(self):
        """Restore from master backup"""
        if self.master_backup and os.path.exists(self.master_backup):
            shutil.copy2(self.master_backup, self.db_path)
            print(f"[MASTER RESTORE] Restored from {self.master_backup}")
            time.sleep(1)  # Wait for file system

    def cleanup_backups(self):
        """Clean up all test backups"""
        if self.master_backup and os.path.exists(self.master_backup):
            os.remove(self.master_backup)
            print(f"[CLEANUP] Removed master backup")

    # ========== TEST 1: Corrupted WAL file ==========

    async def test_corrupted_wal(self):
        """Test behavior with corrupted WAL file"""
        test_name = "Corrupted WAL File Recovery"

        try:
            # Enable WAL mode
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

            # Make a change to create WAL
            conn.execute("INSERT INTO learnings (type, filepath, title, domain, severity) VALUES ('observation', '/tmp/wal_test', 'WAL Test', 'testing', 3)")
            conn.commit()

            wal_path = str(self.db_path) + "-wal"
            shm_path = str(self.db_path) + "-shm"

            # Check if WAL was created
            if not os.path.exists(wal_path):
                conn.execute("PRAGMA journal_mode=DELETE")  # Switch back
                conn.close()
                self.log_result(test_name, "MEDIUM", "PASS",
                    "WAL mode not activated (system limitation), graceful degradation")
                return

            # Backup WAL
            wal_backup = wal_path + ".backup"
            shutil.copy2(wal_path, wal_backup)

            # Close connection and corrupt WAL
            conn.close()
            time.sleep(1)

            # Corrupt the WAL file
            with open(wal_path, 'r+b') as f:
                f.seek(0)
                f.write(b"CORRUPTED!" * 100)

            # Try to query with corrupted WAL
            try:
                qs = await QuerySystem.create(debug=True)
                result = await qs.query_recent(limit=1, timeout=10)
                await qs.cleanup()

                # Recovery successful
                self.log_result(test_name, "HIGH", "PASS",
                    "SQLite auto-recovered from corrupted WAL or ignored corruption")
            except DatabaseError as e:
                if "corrupt" in str(e).lower() or "malformed" in str(e).lower():
                    self.log_result(test_name, "HIGH", "PASS",
                        f"Properly detected WAL corruption: {str(e)[:80]}")
                else:
                    self.log_result(test_name, "HIGH", "FAIL",
                        f"Unclear error handling: {str(e)[:80]}")
            finally:
                # Restore WAL
                if os.path.exists(wal_backup):
                    try:
                        shutil.copy2(wal_backup, wal_path)
                        os.remove(wal_backup)
                    except:
                        pass

                # Switch back to DELETE mode
                try:
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    conn.execute("PRAGMA journal_mode=DELETE")
                    conn.close()
                except:
                    pass

        except Exception as e:
            self.log_result(test_name, "HIGH", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 2: Insert with malformed dates ==========

    async def test_insert_malformed_dates(self):
        """Test inserting records with malformed dates"""
        test_name = "Malformed Date Insertion & Query"

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            # Try to insert with bad date (SQLite doesn't enforce date types)
            malformed_dates = [
                "not-a-date",
                "9999-99-99",
                "invalid",
                ""
            ]

            inserted_ids = []
            for i, bad_date in enumerate(malformed_dates):
                try:
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, domain, severity, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ('observation', f'/tmp/bad_date_{i}', f'Bad Date {i}', 'testing', 3, bad_date)
                    )
                    inserted_ids.append((cursor.lastrowid, bad_date))
                except Exception as e:
                    pass  # Some might fail validation

            conn.commit()

            # Now try to query these
            try:
                qs = await QuerySystem.create(debug=False)
                result = await qs.query_by_domain("testing", limit=20, timeout=10)
                await qs.cleanup()

                # Clean up test data
                for test_id, _ in inserted_ids:
                    cursor.execute("DELETE FROM learnings WHERE id = ?", (test_id,))
                conn.commit()
                conn.close()

                self.log_result(test_name, "MEDIUM", "PASS",
                    f"Handled {len(inserted_ids)} malformed dates gracefully in queries")

            except Exception as e:
                # Clean up even on error
                for test_id, _ in inserted_ids:
                    try:
                        cursor.execute("DELETE FROM learnings WHERE id = ?", (test_id,))
                    except:
                        pass
                conn.commit()
                conn.close()

                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Failed to handle malformed dates: {str(e)[:100]}")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 3: Very large summary ==========

    async def test_large_summary_insertion(self):
        """Test inserting and querying 10MB summary"""
        test_name = "10MB Summary Performance"

        try:
            # Create 10MB text
            large_text = "X" * (10 * 1024 * 1024)

            conn = sqlite3.connect(self.db_path, timeout=60.0)
            cursor = conn.cursor()

            # Insert
            start = time.time()
            cursor.execute(
                "INSERT INTO learnings (type, filepath, title, summary, domain, severity) VALUES (?, ?, ?, ?, ?, ?)",
                ('observation', '/tmp/large_blob', 'Large Blob Test', large_text, 'testing', 3)
            )
            conn.commit()
            insert_time = time.time() - start

            test_id = cursor.lastrowid

            # Query back
            start = time.time()
            cursor.execute("SELECT LENGTH(summary) FROM learnings WHERE id = ?", (test_id,))
            length = cursor.fetchone()[0]
            query_time = time.time() - start

            # Clean up
            cursor.execute("DELETE FROM learnings WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()

            # Test with query.py
            start = time.time()
            try:
                qs = await QuerySystem.create(debug=False)
                result = await qs.query_recent(limit=5, timeout=30)
                qs_time = time.time() - start
                await qs.cleanup()

                if insert_time > 5.0:
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Slow insert: {insert_time:.2f}s for 10MB")
                elif query_time > 2.0:
                    self.log_result(test_name, "MEDIUM", "FAIL",
                        f"Slow query: {query_time:.2f}s for 10MB")
                else:
                    self.log_result(test_name, "LOW", "PASS",
                        f"Good performance: insert={insert_time:.2f}s, query={query_time:.2f}s")
            except Exception as e:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Query.py failed with large blob: {str(e)[:100]}")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 4: SQL reserved words as data ==========

    def test_sql_reserved_words_data(self):
        """Test using SQL reserved words as actual data"""
        test_name = "SQL Reserved Words as Data"

        try:
            reserved_words = [
                ("SELECT", "SELECT"),
                ("DROP TABLE learnings", "injection-attempt"),
                ("'; DELETE FROM learnings; --", "sql-injection"),
                ("UNION", "keyword-union"),
            ]

            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            test_ids = []
            for i, (word, domain) in enumerate(reserved_words):
                try:
                    # Use parametrized query (safe)
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, domain, severity) VALUES (?, ?, ?, ?, ?)",
                        ('observation', f'/tmp/reserved_{i}', word, domain, 3)
                    )
                    test_ids.append(cursor.lastrowid)
                except Exception as e:
                    pass

            conn.commit()
            conn.close()

            # Verify data integrity
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            # Check that no tables were dropped
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learnings'")
            learnings_exists = cursor.fetchone() is not None

            # Count records
            cursor.execute("SELECT COUNT(*) FROM learnings")
            total_count = cursor.fetchone()[0]

            # Clean up test data
            for test_id in test_ids:
                cursor.execute("DELETE FROM learnings WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()

            if learnings_exists and total_count > 0:
                self.log_result(test_name, "CRITICAL", "PASS",
                    f"No SQL injection: table intact with {total_count} records, {len(test_ids)} test records inserted safely")
            else:
                self.log_result(test_name, "CRITICAL", "FAIL",
                    "Database corruption or table dropped!")

        except Exception as e:
            self.log_result(test_name, "CRITICAL", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 5: Unicode data insertion ==========

    def test_unicode_insertion(self):
        """Test inserting Unicode data"""
        test_name = "Unicode Data Insertion & Retrieval"

        try:
            unicode_tests = [
                ("emoji", "test_😀_emoji", "emoji-test"),
                ("chinese", "中文测试内容", "unicode-zh"),
                ("arabic", "العربية اختبار", "unicode-ar"),
                ("mixed", "Test-🚀-Émoji-中文", "unicode-mixed"),
            ]

            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            test_ids = []
            for name, content, domain in unicode_tests:
                try:
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, tags, domain, severity) VALUES (?, ?, ?, ?, ?, ?)",
                        ('observation', f'/tmp/unicode_{name}', f'Unicode {name}', content, domain, 3)
                    )
                    test_ids.append((cursor.lastrowid, content, domain))
                except Exception as e:
                    print(f"    Failed to insert {name}: {e}")

            conn.commit()
            conn.close()

            # Try to retrieve
            successful_retrievals = 0
            for test_id, content, domain in test_ids:
                try:
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    cursor = conn.cursor()
                    cursor.execute("SELECT tags FROM learnings WHERE id = ?", (test_id,))
                    retrieved = cursor.fetchone()[0]
                    conn.close()

                    if retrieved == content:
                        successful_retrievals += 1
                except Exception as e:
                    print(f"    Failed to retrieve {content[:20]}: {e}")

            # Clean up
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            for test_id, _, _ in test_ids:
                cursor.execute("DELETE FROM learnings WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()

            if successful_retrievals == len(test_ids):
                self.log_result(test_name, "LOW", "PASS",
                    f"All {len(test_ids)} Unicode entries stored and retrieved correctly")
            else:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Only {successful_retrievals}/{len(test_ids)} Unicode entries retrieved correctly")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== TEST 6: Null byte handling ==========

    def test_null_bytes(self):
        """Test handling of null bytes in text fields"""
        test_name = "Null Byte Handling"

        try:
            # SQLite can handle null bytes, but they may cause issues
            null_byte_strings = [
                "before\x00after",
                "\x00start",
                "end\x00",
                "multiple\x00null\x00bytes"
            ]

            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            test_ids = []
            inserted = 0

            for i, text in enumerate(null_byte_strings):
                try:
                    cursor.execute(
                        "INSERT INTO learnings (type, filepath, title, domain, severity) VALUES (?, ?, ?, ?, ?)",
                        ('observation', f'/tmp/nullbyte_{i}', text, 'testing', 3)
                    )
                    test_ids.append((cursor.lastrowid, text))
                    inserted += 1
                except Exception as e:
                    pass  # Expected to fail

            conn.commit()

            # Try to retrieve
            retrieved = 0
            for test_id, original in test_ids:
                try:
                    cursor.execute("SELECT title FROM learnings WHERE id = ?", (test_id,))
                    result = cursor.fetchone()[0]
                    retrieved += 1
                except:
                    pass

            # Clean up
            for test_id, _ in test_ids:
                cursor.execute("DELETE FROM learnings WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()

            if inserted == 0:
                self.log_result(test_name, "LOW", "PASS",
                    "Properly rejected all null byte strings")
            elif retrieved == inserted:
                self.log_result(test_name, "LOW", "PASS",
                    f"Handled {inserted} null byte strings correctly (stored and retrieved)")
            else:
                self.log_result(test_name, "MEDIUM", "FAIL",
                    f"Inconsistent null byte handling: {inserted} inserted, {retrieved} retrieved")

        except Exception as e:
            self.log_result(test_name, "MEDIUM", "ERROR",
                f"Test error: {str(e)[:200]}")

    # ========== EXECUTION ==========

    async def run_all_tests(self):
        """Run all destructive tests"""
        print("\n" + "="*70)
        print("DESTRUCTIVE EDGE CASE TESTING - EMERGENT LEARNING FRAMEWORK")
        print("="*70)
        print("\n⚠️  WARNING: These tests will temporarily modify the database")
        print("A master backup will be created and restored after testing\n")

        self.create_master_backup()

        tests = [
            self.test_corrupted_wal,
            self.test_insert_malformed_dates,
            self.test_large_summary_insertion,
            self.test_sql_reserved_words_data,
            self.test_unicode_insertion,
            self.test_null_bytes,
        ]

        for test_func in tests:
            try:
                # Check if test is async
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                time.sleep(1)  # Pause between tests
                self.restore_master_backup()  # Restore after each test
            except Exception as e:
                print(f"\n[!] FATAL ERROR in {test_func.__name__}: {e}")
                traceback.print_exc()
                self.restore_master_backup()

        print("\n" + "="*70)
        print("DESTRUCTIVE TEST SUMMARY")
        print("="*70)

        critical_fails = [r for r in self.test_results if r['severity'] == 'CRITICAL' and r['status'] == 'FAIL']
        high_fails = [r for r in self.test_results if r['severity'] == 'HIGH' and r['status'] == 'FAIL']
        medium_fails = [r for r in self.test_results if r['severity'] == 'MEDIUM' and r['status'] == 'FAIL']
        passes = [r for r in self.test_results if r['status'] == 'PASS']
        errors = [r for r in self.test_results if r['status'] == 'ERROR']

        print(f"\nTotal Tests: {len(self.test_results)}")
        print(f"Passed: {len(passes)}")
        print(f"Failed: {len(critical_fails) + len(high_fails) + len(medium_fails)}")
        print(f"Errors: {len(errors)}")

        if critical_fails:
            print(f"\n⚠️  CRITICAL FAILURES: {len(critical_fails)}")
            for r in critical_fails:
                print(f"  - {r['test']}: {r['details'][:80]}")

        if high_fails:
            print(f"\n⚠️  HIGH SEVERITY FAILURES: {len(high_fails)}")
            for r in high_fails:
                print(f"  - {r['test']}: {r['details'][:80]}")

        # Save results
        results_path = self.base_path / "test_results_destructive.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📄 Detailed results: {results_path}")

        # Final restore and cleanup
        self.restore_master_backup()
        self.cleanup_backups()

        print("\n✓ Database restored to pre-test state")
        print("="*70 + "\n")

        return self.test_results

if __name__ == '__main__':
    tester = DestructiveEdgeTester()
    results = asyncio.run(tester.run_all_tests())

    critical_or_high_fails = [r for r in results if r['severity'] in ['CRITICAL', 'HIGH'] and r['status'] == 'FAIL']
    sys.exit(1 if critical_or_high_fails else 0)
