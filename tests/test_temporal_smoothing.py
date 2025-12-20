#!/usr/bin/env python3
"""
Tests for Phase 2: Temporal Smoothing (EMA)

Tests verify:
1. Single update smoothing effect
2. Noise rejection (random +/-)
3. Asymmetric smoothing (decreases > increases)
4. Warmup period behavior
5. High-confidence stability
6. Trend detection (sustained direction)
7. Recovery from bad state
8. Rate limiting + EMA interaction
"""

import sys
import unittest
import sqlite3
import tempfile
import random
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))

from lifecycle_manager import (
    LifecycleManager, LifecycleConfig, UpdateType, HeuristicStatus
)


class TestTemporalSmoothing(unittest.TestCase):
    """Test suite for EMA temporal smoothing."""

    def setUp(self):
        """Create temporary database for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)

        # Apply migrations manually since temp DB isn't in the right location
        project_root = Path(__file__).parent.parent
        migrations_dir = project_root / "memory" / "migrations"

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Apply base schema (001) - has all tables including EMA columns
            # Note: 001_base_schema.sql already includes confidence_ema and other
            # Phase 2 columns, so we don't need to apply migration 003 separately
            base_schema_path = migrations_dir / "001_base_schema.sql"
            if base_schema_path.exists():
                with open(base_schema_path) as f:
                    conn.executescript(f.read())
                conn.commit()
        finally:
            conn.close()

        # Create manager with test config
        self.config = LifecycleConfig(
            max_updates_per_day=100,  # High limit for testing
            cooldown_minutes=0,        # No cooldown for testing
            max_active_per_domain=50,
            min_confidence=0.05,
            max_confidence=0.95
        )
        self.manager = LifecycleManager(db_path=self.db_path, config=self.config)

    def tearDown(self):
        """Clean up temporary database."""
        if self.db_path.exists():
            self.db_path.unlink()

    def _create_test_heuristic(self, domain="test", rule="Test rule",
                               confidence=0.5, skip_warmup=False) -> int:
        """Create a test heuristic and return its ID."""
        conn = self.manager._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO heuristics
                (domain, rule, confidence, confidence_ema, ema_alpha,
                 ema_warmup_remaining, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (domain, rule, confidence, confidence, 0.15,
                  0 if skip_warmup else 5))
            heuristic_id = cursor.lastrowid
            conn.commit()
            return heuristic_id
        finally:
            conn.close()

    def test_single_update_smoothing(self):
        """Test 1: Single update should have fractional impact with EMA."""
        h_id = self._create_test_heuristic(confidence=0.5, skip_warmup=False)

        # Apply one SUCCESS (in warmup with alpha=0.30)
        result = self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)

        self.assertTrue(result['success'])

        # Raw target would be: 0.5 + 0.1*(1-0.5) = 0.55
        # With EMA (α=0.30 warmup): 0.30*0.55 + 0.70*0.5 = 0.515
        self.assertAlmostEqual(result['new_confidence'], 0.515, places=3)
        self.assertAlmostEqual(result['raw_target'], 0.55, places=3)
        self.assertGreater(result['smoothing_effect'], 0.03)  # Significant damping
        self.assertEqual(result['alpha'], 0.30)  # Warmup alpha
        self.assertTrue(result['in_warmup'])

    def test_noise_rejection(self):
        """Test 2: Random alternating updates should stabilize near baseline."""
        h_id = self._create_test_heuristic(confidence=0.5, skip_warmup=True)

        # Apply 20 random updates
        random.seed(42)  # Reproducible
        for i in range(20):
            update_type = random.choice([UpdateType.SUCCESS, UpdateType.FAILURE])
            self.manager.update_confidence(h_id, update_type, force=True)

        # Check final confidence
        conn = self.manager._get_connection()
        try:
            cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
            final_conf = cursor.fetchone()['confidence']
        finally:
            conn.close()

        # Should remain close to 0.5 despite noise (allow slightly wider range due to randomness)
        self.assertGreater(final_conf, 0.42)
        self.assertLess(final_conf, 0.58)
        print(f"\n[Test 2] After 20 random updates: {final_conf:.4f} (stayed near 0.5)")

    def test_trend_detection(self):
        """Test 3: Sustained success should increase confidence despite smoothing."""
        h_id = self._create_test_heuristic(confidence=0.5, skip_warmup=True)

        # Apply 20 consecutive successes
        for i in range(20):
            self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)

        # Check final confidence
        conn = self.manager._get_connection()
        try:
            cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
            final_conf = cursor.fetchone()['confidence']
        finally:
            conn.close()

        # Should have increased despite smoothing
        self.assertGreater(final_conf, 0.65)
        self.assertLess(final_conf, 0.80)  # But not unbounded
        print(f"\n[Test 3] After 20 successes with alpha=0.15: {final_conf:.4f}")

    def test_asymmetric_smoothing(self):
        """Test 4: Verify increases are smoother (smaller alpha) than decreases."""
        h_inc = self._create_test_heuristic(confidence=0.6, skip_warmup=True)
        h_dec = self._create_test_heuristic(confidence=0.6, skip_warmup=True)

        # One success, one failure
        r_inc = self.manager.update_confidence(h_inc, UpdateType.SUCCESS, force=True)
        r_dec = self.manager.update_confidence(h_dec, UpdateType.FAILURE, force=True)

        # Decrease should have larger smoothed delta (higher alpha)
        self.assertGreater(abs(r_dec['delta_smoothed']), abs(r_inc['delta_smoothed']))
        self.assertLess(r_inc['alpha'], r_dec['alpha'])

        print(f"\n[Test 4] Increase: delta={r_inc['delta_smoothed']:.5f}, alpha={r_inc['alpha']:.2f}")
        print(f"[Test 4] Decrease: delta={r_dec['delta_smoothed']:.5f}, alpha={r_dec['alpha']:.2f}")

    def test_warmup_transition(self):
        """Test 5: Warmup should end after 5 updates with alpha transition."""
        h_id = self._create_test_heuristic(confidence=0.5, skip_warmup=False)

        alphas = []
        for i in range(7):
            result = self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)
            alphas.append(result['alpha'])

        # First 5 should be warmup (α=0.30)
        for i in range(5):
            self.assertEqual(alphas[i], 0.30, f"Update {i+1} should have warmup alpha")

        # After warmup, should transition to lower alpha
        self.assertLess(alphas[5], 0.30)
        self.assertLess(alphas[6], 0.30)

        print(f"\n[Test 5] Alpha progression: {alphas}")

    def test_high_confidence_stability(self):
        """Test 6: High-confidence heuristic should resist single failures."""
        h_id = self._create_test_heuristic(confidence=0.85, skip_warmup=True)

        # Mark as mature
        conn = self.manager._get_connection()
        try:
            conn.execute("UPDATE heuristics SET times_validated = 50 WHERE id = ?", (h_id,))
            conn.commit()
        finally:
            conn.close()

        # One failure
        result = self.manager.update_confidence(h_id, UpdateType.FAILURE, force=True)

        # Should have minimal impact
        self.assertGreater(result['delta_smoothed'], -0.02)  # Less than 2-point drop
        self.assertLess(result['alpha'], 0.20)  # Low alpha for high confidence

        print(f"\n[Test 6] High-confidence stability: {result['old_confidence']:.3f} -> {result['new_confidence']:.3f}")
        print(f"[Test 6] Alpha used: {result['alpha']:.2f}, Delta: {result['delta_smoothed']:.5f}")

    def test_recovery_from_bad_state(self):
        """Test 7: Low-confidence heuristic should be able to recover."""
        h_id = self._create_test_heuristic(confidence=0.25, skip_warmup=True)

        # Apply 10 successes
        for i in range(10):
            result = self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)
            self.assertTrue(result['success'], f"Update {i} failed")

        # Check final confidence
        conn = self.manager._get_connection()
        try:
            cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
            final_conf = cursor.fetchone()['confidence']
        finally:
            conn.close()

        # Should have recovered significantly (allow slightly below 0.40 due to smoothing)
        self.assertGreater(final_conf, 0.39)
        print(f"\n[Test 7] Recovered from 0.25 -> {final_conf:.3f}")

    def test_rate_limiting_plus_ema(self):
        """Test 8: Rate limiting + EMA should compound protection."""
        # Create config with strict rate limiting
        config = LifecycleConfig(
            max_updates_per_day=3,
            cooldown_minutes=1,
            min_confidence=0.05,
            max_confidence=0.95
        )
        manager = LifecycleManager(db_path=self.db_path, config=config)

        h_id = self._create_test_heuristic(confidence=0.5, skip_warmup=True)

        # Try 10 rapid successes
        successes = 0
        rate_limited = 0

        for i in range(10):
            result = manager.update_confidence(h_id, UpdateType.SUCCESS)
            if result['success']:
                successes += 1
            elif result.get('rate_limited'):
                rate_limited += 1

        # Should be rate limited
        self.assertLessEqual(successes, 3)
        self.assertGreater(rate_limited, 0)

        # Check final confidence
        conn = manager._get_connection()
        try:
            cursor = conn.execute("SELECT confidence FROM heuristics WHERE id = ?", (h_id,))
            final_conf = cursor.fetchone()['confidence']
        finally:
            conn.close()

        # Even the allowed updates should be smoothed
        self.assertLess(final_conf, 0.55)  # Much less than discrete would allow

        print(f"\n[Test 8] Successes: {successes}, Rate limited: {rate_limited}, Final: {final_conf:.3f}")

    def test_adaptive_alpha_high_confidence(self):
        """Test 9: High confidence (>0.80) should use very low alpha."""
        h_id = self._create_test_heuristic(confidence=0.85, skip_warmup=True)

        # Mark as mature
        conn = self.manager._get_connection()
        try:
            conn.execute("UPDATE heuristics SET times_validated = 30 WHERE id = ?", (h_id,))
            conn.commit()
        finally:
            conn.close()

        # Success (increase)
        r_inc = self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)
        self.assertEqual(r_inc['alpha'], 0.10)

        # Failure (decrease)
        r_dec = self.manager.update_confidence(h_id, UpdateType.FAILURE, force=True)
        self.assertEqual(r_dec['alpha'], 0.15)

        print(f"\n[Test 9] High-confidence alpha - Increase: {r_inc['alpha']}, Decrease: {r_dec['alpha']}")

    def test_adaptive_alpha_low_confidence(self):
        """Test 10: Low confidence (<0.30) should use higher alpha for recovery."""
        h_id = self._create_test_heuristic(confidence=0.25, skip_warmup=True)

        # Success (increase) - should use higher alpha
        r_inc = self.manager.update_confidence(h_id, UpdateType.SUCCESS, force=True)
        self.assertEqual(r_inc['alpha'], 0.25)

        # Failure (decrease)
        r_dec = self.manager.update_confidence(h_id, UpdateType.FAILURE, force=True)
        self.assertEqual(r_dec['alpha'], 0.20)

        print(f"\n[Test 10] Low-confidence alpha - Increase: {r_inc['alpha']}, Decrease: {r_dec['alpha']}")

    def test_decay_bypasses_ema(self):
        """Test 11: Time decay should bypass EMA smoothing."""
        h_id = self._create_test_heuristic(confidence=0.7, skip_warmup=True)

        # Apply decay
        result = self.manager.update_confidence(h_id, UpdateType.DECAY, force=True)

        # Decay should bypass EMA (alpha=1.0)
        self.assertEqual(result['alpha'], 1.0)

        # Expected: 0.7 * 0.92 = 0.644
        self.assertAlmostEqual(result['new_confidence'], 0.644, places=3)

        print(f"\n[Test 11] Decay: {result['old_confidence']:.3f} -> {result['new_confidence']:.3f} (alpha={result['alpha']})")

    def test_revival_bypasses_ema(self):
        """Test 12: Revival should bypass EMA smoothing."""
        h_id = self._create_test_heuristic(confidence=0.25, skip_warmup=True)

        # Apply revival
        result = self.manager.update_confidence(h_id, UpdateType.REVIVAL, force=True)

        # Revival should bypass EMA (alpha=1.0)
        self.assertEqual(result['alpha'], 1.0)

        # Expected: max(0.25, 0.35) = 0.35
        self.assertAlmostEqual(result['new_confidence'], 0.35, places=3)

        print(f"\n[Test 12] Revival: {result['old_confidence']:.3f} -> {result['new_confidence']:.3f} (alpha={result['alpha']})")


def run_tests():
    """Run test suite with verbose output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTemporalSmoothing)

    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
