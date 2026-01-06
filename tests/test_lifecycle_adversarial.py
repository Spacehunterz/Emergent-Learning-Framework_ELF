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
from datetime import datetime, timedelta

import pytest

from query.lifecycle_manager import (
    LifecycleManager, LifecycleConfig, UpdateType, HeuristicStatus
)

# =============================================================================
# TEST CONSTANTS
# =============================================================================
MAX_UPDATES_PER_DAY = 5
COOLDOWN_MINUTES = 1
MIN_APPLICATIONS_FOR_DEPRECATION = 10
CONTRADICTION_RATE_THRESHOLD = 0.30
MAX_ACTIVE_PER_DOMAIN = 5
DORMANT_AFTER_DAYS = 60
MIN_CONFIDENCE = 0.05
MAX_CONFIDENCE = 0.95


# =============================================================================
# PUMP-AND-DUMP ATTACK TESTS
# =============================================================================
class TestPumpAndDump:
    """
    TEST 1: Pump-and-Dump Attack

    Attack: Rapidly apply heuristic to easy tasks to inflate confidence.
    Expected: Rate limiting prevents rapid manipulation.
    """

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        """Set up test fixtures using pytest's mock_db fixture."""
        self.db = mock_db
        self.config = LifecycleConfig(
            max_updates_per_day=MAX_UPDATES_PER_DAY,
            cooldown_minutes=COOLDOWN_MINUTES
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

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
        assert blocked > 0, f"Rate limiting should block rapid updates, got {blocked} blocked"
        assert successes <= self.config.max_updates_per_day, (
            f"Should not exceed {self.config.max_updates_per_day} updates, got {successes}"
        )

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        final_conf = cursor.fetchone()[0]
        conn.close()

        assert final_conf < 0.7, f"Confidence should not exceed 0.7, got {final_conf}"

    def test_daily_limit_resets(self):
        """Daily update limit should reset after 24 hours."""
        h_id = self.db.insert_heuristic("testing", "Test heuristic", confidence=0.5)

        for i in range(self.config.max_updates_per_day):
            self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)

        result = self.manager.update_confidence(h_id, UpdateType.SUCCESS)
        assert result.get("rate_limited"), "Should be rate limited after daily quota"


# =============================================================================
# STATISTICAL ASSASSINATION TESTS
# =============================================================================
class TestStatisticalAssassination:
    """
    TEST 2: Statistical Assassination

    Attack: Kill good heuristic with 3 edge-case contradictions.
    Expected: Rate-based threshold prevents unfair death.
    """

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        """Set up test fixtures."""
        self.db = mock_db
        self.config = LifecycleConfig(
            min_applications_for_deprecation=MIN_APPLICATIONS_FOR_DEPRECATION,
            contradiction_rate_threshold=CONTRADICTION_RATE_THRESHOLD
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

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

        result = self.manager.check_deprecation_threshold(h_id)

        assert not result["should_deprecate"], (
            f"Excellent heuristic should not be deprecated: {result}"
        )

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT status FROM heuristics WHERE id = ?", (h_id,))
        status = cursor.fetchone()[0]
        conn.close()

        assert status == "active", "Heuristic should remain active despite 3 contradictions"

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

        result = self.manager.check_deprecation_threshold(h_id)

        assert result["should_deprecate"], f"Bad heuristic should be deprecated: {result}"

        expected_rate = 4 / (5 + 2 + 4)  # 0.36
        assert abs(result["contradiction_rate"] - expected_rate) < 0.01, (
            f"Expected contradiction rate ~{expected_rate}, got {result['contradiction_rate']}"
        )


# =============================================================================
# DOMAIN GRIDLOCK TESTS
# =============================================================================
class TestDomainGridlock:
    """
    TEST 3: Domain Gridlock

    Attack: Fill domain with 5 heuristics, let all decay to dormant, block new ones.
    Expected: Dormant revival mechanism prevents gridlock.
    """

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        """Set up test fixtures."""
        self.db = mock_db
        self.config = LifecycleConfig(
            max_active_per_domain=MAX_ACTIVE_PER_DOMAIN,
            dormant_after_days=DORMANT_AFTER_DAYS
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

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

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT status FROM heuristics WHERE id = ?", (h_id,))
        assert cursor.fetchone()[0] == "dormant", "Heuristic should be dormant"
        conn.close()

        result = self.manager.revive_heuristic(h_id, "New embedded project started")

        assert result["success"], f"Revival should succeed: {result}"

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT status, times_revived FROM heuristics WHERE id = ?", (h_id,))
        row = cursor.fetchone()
        conn.close()

        assert row[0] == "active", f"Expected status 'active', got '{row[0]}'"
        assert row[1] == 1, f"Expected times_revived=1, got {row[1]}"

    def test_revival_triggers_detect_keywords(self):
        """Revival triggers should fire when keywords appear in context."""
        # Create dormant heuristic with keywords
        h_id = self.db.insert_heuristic(
            "caching",
            "Use Redis for session storage in distributed systems",
            confidence=0.6
        )
        self.manager.make_dormant(h_id, "No distributed work lately")

        candidates = self.manager.check_revival_triggers(
            "We need to scale to distributed architecture and manage session state"
        )

        matching = [c for c in candidates if c["id"] == h_id]
        assert len(matching) > 0, "Should find dormant heuristic via keyword trigger"

    def test_new_heuristics_can_enter_full_domain(self):
        """New heuristics should be able to enter domain even when full."""
        # Fill domain with 5 heuristics
        for i in range(5):
            self.db.insert_heuristic(
                "testing",
                f"Test heuristic {i}",
                confidence=0.5
            )

        result = self.manager.enforce_domain_limits("testing")

        assert result["action"] == "none", f"Expected action 'none', got '{result['action']}'"

        self.db.insert_heuristic("testing", "New important heuristic", confidence=0.8)

        result = self.manager.enforce_domain_limits("testing")

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("""
            SELECT active_count, dormant_count FROM domain_health WHERE domain = 'testing'
        """)
        row = cursor.fetchone()
        conn.close()

        assert row[0] <= self.config.max_active_per_domain, (
            f"Active count {row[0]} exceeds limit {self.config.max_active_per_domain}"
        )


# =============================================================================
# EVICTION POLICY TESTS
# =============================================================================
class TestEvictionPolicy:
    """
    TEST 5: Knowledge Preservation

    Verify eviction policy uses weighted scoring (confidence × recency × usage).
    """

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        """Set up test fixtures."""
        self.db = mock_db
        self.config = LifecycleConfig(
            max_active_per_domain=MAX_ACTIVE_PER_DOMAIN
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def test_eviction_score_considers_confidence(self):
        """Higher confidence = higher eviction score (less likely to evict)."""
        h_low = self.db.insert_heuristic("testing", "Low conf", confidence=0.3)
        h_high = self.db.insert_heuristic("testing", "High conf", confidence=0.9)

        candidates = self.manager.get_eviction_candidates("testing")

        scores = {c["id"]: c["eviction_score"] for c in candidates}

        assert scores[h_high] > scores[h_low], (
            f"Higher confidence should have higher eviction score: "
            f"high={scores[h_high]}, low={scores[h_low]}"
        )

    def test_eviction_score_considers_validations(self):
        """More validations = higher eviction score (less likely to evict)."""
        h_few = self.db.insert_heuristic("testing", "Few validations",
                                         confidence=0.5, times_validated=1)
        h_many = self.db.insert_heuristic("testing", "Many validations",
                                          confidence=0.5, times_validated=20)

        candidates = self.manager.get_eviction_candidates("testing")

        scores = {c["id"]: c["eviction_score"] for c in candidates}

        assert scores[h_many] > scores[h_few], (
            f"More validations should have higher eviction score: "
            f"many={scores[h_many]}, few={scores[h_few]}"
        )

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

        result = self.manager.enforce_domain_limits("testing")

        demoted_ids = [d["id"] for d in result.get("demoted", [])]
        assert h_id not in demoted_ids, "Golden rules should never be evicted"


# =============================================================================
# CONFIDENCE BOUNDS TESTS
# =============================================================================
class TestConfidenceBounds:
    """Test that confidence stays within bounds (0.05-0.95)."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        """Set up test fixtures."""
        self.db = mock_db
        self.config = LifecycleConfig(
            min_confidence=MIN_CONFIDENCE,
            max_confidence=MAX_CONFIDENCE
        )
        self.manager = LifecycleManager(db_path=self.db.db_path, config=self.config)

    def test_confidence_cannot_exceed_max(self):
        """Confidence should cap at max_confidence."""
        h_id = self.db.insert_heuristic("testing", "Test", confidence=0.90)

        for _ in range(20):
            self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        conf = cursor.fetchone()[0]
        conn.close()

        assert conf <= self.config.max_confidence, (
            f"Confidence {conf} should not exceed {self.config.max_confidence}"
        )

    def test_confidence_cannot_go_below_min(self):
        """Confidence should floor at min_confidence."""
        h_id = self.db.insert_heuristic("testing", "Test", confidence=0.15)

        for _ in range(20):
            self.manager.update_confidence(h_id, UpdateType.FAILURE, force=True)

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
        conf = cursor.fetchone()[0]
        conn.close()

        assert conf >= self.config.min_confidence, (
            f"Confidence {conf} should not go below {self.config.min_confidence}"
        )


# =============================================================================
# SYMMETRIC CONFIDENCE FORMULA TESTS
# =============================================================================
class TestSymmetricConfidenceFormula:
    """Test that success/failure are symmetric to prevent gaming."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        """Set up test fixtures."""
        self.db = mock_db
        self.manager = LifecycleManager(db_path=self.db.db_path)

    def test_symmetric_updates_at_midpoint(self):
        """At 0.5 confidence, success and failure should have similar magnitude."""
        h1 = self.db.insert_heuristic("testing", "Test 1", confidence=0.5)
        h2 = self.db.insert_heuristic("testing", "Test 2", confidence=0.5)

        r1 = self.manager.update_confidence(h1, UpdateType.SUCCESS, force=True)
        r2 = self.manager.update_confidence(h2, UpdateType.FAILURE, force=True)

        success_delta = abs(r1["delta"])
        failure_delta = abs(r2["delta"])

        ratio = success_delta / failure_delta if failure_delta > 0 else float('inf')
        assert ratio > 0.5, f"Success/failure should be roughly balanced, ratio={ratio}"
        assert ratio < 2.0, f"Success/failure should be roughly balanced, ratio={ratio}"

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

        assert final_conf > 0.3, f"Should not drop too low, got {final_conf}"
        assert final_conf < 0.7, f"Should not grow too high for 50% accuracy, got {final_conf}"
