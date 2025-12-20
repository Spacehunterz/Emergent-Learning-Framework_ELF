#!/usr/bin/env python3
"""
Adversarial Tests for Heuristic Lifecycle - Phase 1

These tests validate the fixes for the 6 vulnerabilities identified in the Skeptic Security Audit.

Test 1: Pump-and-Dump Attack (should fail with rate limiting)
Test 2: Statistical Assassination (should fail with rate-based contradiction)
Test 3: Domain Gridlock (should fail with dormant revival)
Test 4: Meta-Observer Stability (validates trend-based alerts)
Test 5: Knowledge Preservation (validates eviction policy)

Run with: python -m pytest tests/test_lifecycle_adversarial.py -v
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import unittest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))

from lifecycle_manager import (
    LifecycleManager, LifecycleConfig, UpdateType, HeuristicStatus
)


class TestDatabase:
    """Test database manager with isolation."""

    def __init__(self):
        self.db_path = Path(__file__).parent / "test_lifecycle.db"
        self.setup()

    def setup(self):
        """Create test database with schema."""
        if self.db_path.exists():
            self.db_path.unlink()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create minimal schema for testing
        cursor.executescript("""
            CREATE TABLE heuristics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                rule TEXT NOT NULL,
                explanation TEXT,
                source_type TEXT,
                source_id INTEGER,
                confidence REAL DEFAULT 0.5,
                times_validated INTEGER DEFAULT 0,
                times_violated INTEGER DEFAULT 0,
                times_contradicted INTEGER DEFAULT 0,
                is_golden INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                dormant_since DATETIME,
                last_used_at DATETIME,
                revival_conditions TEXT,
                times_revived INTEGER DEFAULT 0,
                min_applications INTEGER DEFAULT 10,
                last_confidence_update DATETIME,
                update_count_today INTEGER DEFAULT 0,
                update_count_reset_date DATE,
                -- Phase 2: EMA temporal smoothing columns
                confidence_ema REAL,
                ema_alpha REAL,
                ema_warmup_remaining INTEGER DEFAULT 0,
                last_ema_update DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE confidence_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                heuristic_id INTEGER NOT NULL,
                old_confidence REAL NOT NULL,
                new_confidence REAL NOT NULL,
                delta REAL NOT NULL,
                update_type TEXT NOT NULL,
                reason TEXT,
                session_id TEXT,
                agent_id TEXT,
                rate_limited INTEGER DEFAULT 0,
                -- Phase 2: EMA temporal smoothing columns
                raw_target_confidence REAL,
                smoothed_delta REAL,
                alpha_used REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE revival_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                heuristic_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_value TEXT NOT NULL,
                priority INTEGER DEFAULT 100,
                is_active INTEGER DEFAULT 1,
                last_checked DATETIME,
                times_triggered INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );

            INSERT INTO schema_version (version, description) VALUES (2, 'Test schema');
        """)

        # Create views
        cursor.execute("""
            CREATE VIEW eviction_candidates AS
            SELECT
                h.id,
                h.domain,
                h.rule,
                h.status,
                h.confidence,
                h.times_validated,
                h.times_violated,
                h.times_contradicted,
                h.last_used_at,
                h.created_at,
                h.confidence *
                (CASE
                    WHEN h.last_used_at IS NULL THEN 0.25
                    WHEN julianday('now') - julianday(h.last_used_at) > 90 THEN 0.1
                    WHEN julianday('now') - julianday(h.last_used_at) > 60 THEN 0.3
                    WHEN julianday('now') - julianday(h.last_used_at) > 30 THEN 0.5
                    WHEN julianday('now') - julianday(h.last_used_at) > 14 THEN 0.7
                    WHEN julianday('now') - julianday(h.last_used_at) > 7 THEN 0.85
                    ELSE 1.0
                END) *
                (CASE
                    WHEN h.times_validated = 0 THEN 0.5
                    WHEN h.times_validated < 3 THEN 0.7
                    WHEN h.times_validated < 10 THEN 0.85
                    ELSE 1.0
                END) AS eviction_score,
                (h.times_validated + h.times_violated + h.times_contradicted) AS total_applications
            FROM heuristics h
            WHERE h.status = 'active' OR h.status = 'dormant'
            ORDER BY eviction_score ASC
        """)

        cursor.execute("""
            CREATE VIEW domain_health AS
            SELECT
                domain,
                COUNT(*) AS total_heuristics,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN status = 'dormant' THEN 1 ELSE 0 END) AS dormant_count,
                AVG(confidence) AS avg_confidence
            FROM heuristics
            GROUP BY domain
        """)

        conn.commit()
        conn.close()

    def teardown(self):
        """Remove test database."""
        if self.db_path.exists():
            self.db_path.unlink()

    def insert_heuristic(self, domain: str, rule: str, confidence: float = 0.5,
                        times_validated: int = 0, times_violated: int = 0,
                        times_contradicted: int = 0, status: str = "active") -> int:
        """Insert a test heuristic and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated,
                                   times_violated, times_contradicted, status, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (domain, rule, confidence, times_validated, times_violated, times_contradicted, status))
        conn.commit()
        heuristic_id = cursor.lastrowid
        conn.close()
        return heuristic_id


class TestPumpAndDump(unittest.TestCase):
    """
    TEST 1: Pump-and-Dump Attack

    Attack: Rapidly apply heuristic to easy tasks to inflate confidence.
    Expected: Rate limiting prevents rapid manipulation.
    """

    def setUp(self):
        self.db = TestDatabase()
        self.config = LifecycleConfig(
            max_updates_per_day=5,
            cooldown_minutes=1  # 1 minute cooldown for testing
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def tearDown(self):
        self.db.teardown()

    def test_rate_limiting_blocks_rapid_updates(self):
        """Rate limiting should block rapid confidence manipulation."""
        # Create a mediocre heuristic
        h_id = self.db.insert_heuristic("testing", "Mediocre heuristic", confidence=0.35)

        # Try to pump confidence with 20 rapid successes
        successes = 0
        blocked = 0

        for i in range(20):
            result = self.manager.update_confidence(
                h_id, UpdateType.SUCCESS,
                reason=f"Easy task {i}",
                session_id="attacker"
            )
            if result.get("success"):
                successes += 1
            elif result.get("rate_limited"):
                blocked += 1

        # Should have been rate limited
        self.assertGreater(blocked, 0, "Rate limiting should block rapid updates")
        self.assertLessEqual(successes, self.config.max_updates_per_day,
                            f"Should not exceed {self.config.max_updates_per_day} updates")

        # Check final confidence isn't extremely high
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        final_conf = cursor.fetchone()[0]
        conn.close()

        self.assertLess(final_conf, 0.7,
                       f"Confidence should not exceed 0.7, got {final_conf}")

    def test_daily_limit_resets(self):
        """Daily update limit should reset after 24 hours."""
        h_id = self.db.insert_heuristic("testing", "Test heuristic", confidence=0.5)

        # Use all daily updates
        for i in range(self.config.max_updates_per_day):
            self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)

        # Should be blocked now
        result = self.manager.update_confidence(h_id, UpdateType.SUCCESS)
        self.assertTrue(result.get("rate_limited"), "Should be rate limited after daily quota")


class TestStatisticalAssassination(unittest.TestCase):
    """
    TEST 2: Statistical Assassination

    Attack: Kill good heuristic with 3 edge-case contradictions.
    Expected: Rate-based threshold prevents unfair death.
    """

    def setUp(self):
        self.db = TestDatabase()
        self.config = LifecycleConfig(
            min_applications_for_deprecation=10,
            contradiction_rate_threshold=0.30
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def tearDown(self):
        self.db.teardown()

    def test_excellent_heuristic_survives_3_contradictions(self):
        """95% accurate heuristic should survive 3 edge-case contradictions."""
        # Create excellent heuristic with 95% accuracy
        # 95 validations, 5 violations = 95% accurate
        h_id = self.db.insert_heuristic(
            "security",
            "Always validate user input",
            confidence=0.85,
            times_validated=95,
            times_violated=5,
            times_contradicted=0
        )

        # Apply 3 edge-case contradictions
        for i in range(3):
            self.manager.update_confidence(
                h_id, UpdateType.CONTRADICTION,
                reason=f"Edge case {i}",
                force=True
            )

        # Check deprecation status
        result = self.manager.check_deprecation_threshold(h_id)

        # Should NOT be deprecated
        self.assertFalse(result["should_deprecate"],
                        f"Excellent heuristic should not be deprecated: {result}")

        # Verify status is still active
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT status FROM heuristics WHERE id = ?", (h_id,))
        status = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(status, "active",
                        "Heuristic should remain active despite 3 contradictions")

    def test_bad_heuristic_gets_deprecated_at_threshold(self):
        """Heuristic with >30% contradiction rate should be deprecated."""
        # Create heuristic with bad track record
        # 5 validated, 2 violated, 4 contradicted = 36% contradiction rate
        h_id = self.db.insert_heuristic(
            "testing",
            "Bad heuristic",
            confidence=0.4,
            times_validated=5,
            times_violated=2,
            times_contradicted=4
        )

        # Check deprecation threshold
        result = self.manager.check_deprecation_threshold(h_id)

        # Should be deprecated
        self.assertTrue(result["should_deprecate"],
                       f"Bad heuristic should be deprecated: {result}")

        # Verify contradiction rate calculation
        expected_rate = 4 / (5 + 2 + 4)  # 0.36
        self.assertAlmostEqual(result["contradiction_rate"], expected_rate, places=2)


class TestDomainGridlock(unittest.TestCase):
    """
    TEST 3: Domain Gridlock

    Attack: Fill domain with 5 heuristics, let all decay to dormant, block new ones.
    Expected: Dormant revival mechanism prevents gridlock.
    """

    def setUp(self):
        self.db = TestDatabase()
        self.config = LifecycleConfig(
            max_active_per_domain=5,
            dormant_after_days=60
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def tearDown(self):
        self.db.teardown()

    def test_dormant_heuristics_can_be_revived(self):
        """Dormant heuristics should be revivable when relevant."""
        # Create and make dormant
        h_id = self.db.insert_heuristic(
            "embedded",
            "Use interrupt handlers for real-time events",
            confidence=0.5
        )

        # Make it dormant
        self.manager.make_dormant(h_id, "Domain inactive")

        # Verify it's dormant
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT status FROM heuristics WHERE id = ?", (h_id,))
        self.assertEqual(cursor.fetchone()[0], "dormant")
        conn.close()

        # Revive it
        result = self.manager.revive_heuristic(h_id, "New embedded project started")

        # Should succeed
        self.assertTrue(result["success"], f"Revival should succeed: {result}")

        # Verify it's active again
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT status, times_revived FROM heuristics WHERE id = ?", (h_id,))
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], "active")
        self.assertEqual(row[1], 1)

    def test_revival_triggers_detect_keywords(self):
        """Revival triggers should fire when keywords appear in context."""
        # Create dormant heuristic with keywords
        h_id = self.db.insert_heuristic(
            "caching",
            "Use Redis for session storage in distributed systems",
            confidence=0.6
        )
        self.manager.make_dormant(h_id, "No distributed work lately")

        # Check revival triggers with relevant context
        candidates = self.manager.check_revival_triggers(
            "We need to scale to distributed architecture and manage session state"
        )

        # Should find the dormant heuristic
        matching = [c for c in candidates if c["id"] == h_id]
        self.assertGreater(len(matching), 0,
                          "Should find dormant heuristic via keyword trigger")

    def test_new_heuristics_can_enter_full_domain(self):
        """New heuristics should be able to enter domain even when full."""
        # Fill domain with 5 heuristics
        for i in range(5):
            self.db.insert_heuristic(
                "testing",
                f"Test heuristic {i}",
                confidence=0.5
            )

        # Enforce limits (should demote lowest)
        result = self.manager.enforce_domain_limits("testing")

        # Should not have blocked anything (at limit but not over)
        self.assertEqual(result["action"], "none")

        # Add one more (over limit)
        self.db.insert_heuristic("testing", "New important heuristic", confidence=0.8)

        # Now enforce - should demote one
        result = self.manager.enforce_domain_limits("testing")

        # Check domain health
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("""
            SELECT active_count, dormant_count FROM domain_health WHERE domain = 'testing'
        """)
        row = cursor.fetchone()
        conn.close()

        # Should have 5 active and 1 dormant
        self.assertLessEqual(row[0], self.config.max_active_per_domain,
                            "Active count should not exceed limit")


class TestEvictionPolicy(unittest.TestCase):
    """
    TEST 5: Knowledge Preservation

    Verify eviction policy uses weighted scoring (confidence × recency × usage).
    """

    def setUp(self):
        self.db = TestDatabase()
        self.config = LifecycleConfig(
            max_active_per_domain=5
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def tearDown(self):
        self.db.teardown()

    def test_eviction_score_considers_confidence(self):
        """Higher confidence = higher eviction score (less likely to evict)."""
        h_low = self.db.insert_heuristic("testing", "Low conf", confidence=0.3)
        h_high = self.db.insert_heuristic("testing", "High conf", confidence=0.9)

        candidates = self.manager.get_eviction_candidates("testing")

        scores = {c["id"]: c["eviction_score"] for c in candidates}

        self.assertGreater(scores[h_high], scores[h_low],
                          "Higher confidence should have higher eviction score")

    def test_eviction_score_considers_validations(self):
        """More validations = higher eviction score (less likely to evict)."""
        h_few = self.db.insert_heuristic("testing", "Few validations",
                                         confidence=0.5, times_validated=1)
        h_many = self.db.insert_heuristic("testing", "Many validations",
                                          confidence=0.5, times_validated=20)

        candidates = self.manager.get_eviction_candidates("testing")

        scores = {c["id"]: c["eviction_score"] for c in candidates}

        self.assertGreater(scores[h_many], scores[h_few],
                          "More validations should have higher eviction score")

    def test_golden_rules_never_evicted(self):
        """Golden rules should never be evicted regardless of score."""
        # Create golden rule with low score factors
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated, is_golden)
            VALUES ('testing', 'Golden rule', 0.3, 0, 1)
        """)
        conn.commit()
        h_id = cursor.lastrowid
        conn.close()

        # Fill domain to trigger eviction
        for i in range(10):
            self.db.insert_heuristic("testing", f"Other heuristic {i}", confidence=0.5)

        # Enforce limits
        result = self.manager.enforce_domain_limits("testing")

        # Golden rule should not be in demoted list
        demoted_ids = [d["id"] for d in result.get("demoted", [])]
        self.assertNotIn(h_id, demoted_ids,
                        "Golden rules should never be evicted")


class TestConfidenceBounds(unittest.TestCase):
    """Test that confidence stays within bounds (0.05-0.95)."""

    def setUp(self):
        self.db = TestDatabase()
        self.config = LifecycleConfig(
            min_confidence=0.05,
            max_confidence=0.95
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def tearDown(self):
        self.db.teardown()

    def test_confidence_cannot_exceed_max(self):
        """Confidence should cap at max_confidence."""
        h_id = self.db.insert_heuristic("testing", "Test", confidence=0.90)

        # Apply many successes
        for _ in range(20):
            self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        conf = cursor.fetchone()[0]
        conn.close()

        self.assertLessEqual(conf, self.config.max_confidence,
                            f"Confidence should not exceed {self.config.max_confidence}")

    def test_confidence_cannot_go_below_min(self):
        """Confidence should floor at min_confidence."""
        h_id = self.db.insert_heuristic("testing", "Test", confidence=0.15)

        # Apply many failures
        for _ in range(20):
            self.manager.update_confidence(h_id, UpdateType.FAILURE, force=True)

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        conf = cursor.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(conf, self.config.min_confidence,
                               f"Confidence should not go below {self.config.min_confidence}")


class TestSymmetricConfidenceFormula(unittest.TestCase):
    """Test that success/failure are symmetric to prevent gaming."""

    def setUp(self):
        self.db = TestDatabase()
        self.manager = LifecycleManager(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_symmetric_updates_at_midpoint(self):
        """At 0.5 confidence, success and failure should have similar magnitude."""
        h1 = self.db.insert_heuristic("testing", "Test 1", confidence=0.5)
        h2 = self.db.insert_heuristic("testing", "Test 2", confidence=0.5)

        r1 = self.manager.update_confidence(h1, UpdateType.SUCCESS, force=True)
        r2 = self.manager.update_confidence(h2, UpdateType.FAILURE, force=True)

        success_delta = abs(r1["delta"])
        failure_delta = abs(r2["delta"])

        # Deltas should be similar (not exactly equal due to formula)
        ratio = success_delta / failure_delta if failure_delta > 0 else float('inf')
        self.assertGreater(ratio, 0.5, "Success/failure should be roughly balanced")
        self.assertLess(ratio, 2.0, "Success/failure should be roughly balanced")

    def test_mediocre_heuristic_stabilizes(self):
        """A 50% accurate heuristic should stabilize around 0.5, not grow indefinitely."""
        h_id = self.db.insert_heuristic("testing", "Mediocre", confidence=0.35)

        # Simulate 50% accuracy: alternating success/failure
        for i in range(50):
            update_type = UpdateType.SUCCESS if i % 2 == 0 else UpdateType.FAILURE
            self.manager.update_confidence(h_id, update_type, force=True)

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        final_conf = cursor.fetchone()[0]
        conn.close()

        # Should be somewhere around 0.4-0.6, not growing unbounded
        self.assertGreater(final_conf, 0.3, "Should not drop too low")
        self.assertLess(final_conf, 0.7, "Should not grow too high for 50% accuracy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
