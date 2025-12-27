#!/usr/bin/env python3
"""
Test suite for Domain Elasticity (Phase 2B)

Tests the two-tier capacity system with expansion/contraction logic.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from query.lifecycle_manager import LifecycleManager, LifecycleConfig


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(path)

    # Use the actual database schema from the production database
    # This matches the current schema in ~/.claude/emergent-learning/memory/index.db
    conn.executescript("""
        -- Core heuristics table with all current columns
        CREATE TABLE heuristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            rule TEXT NOT NULL,
            explanation TEXT,
            source_type TEXT,
            confidence REAL DEFAULT 0.0,
            times_validated INTEGER DEFAULT 0,
            is_golden INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_id INTEGER,
            times_violated INTEGER DEFAULT 0,
            updated_at DATETIME,
            status TEXT DEFAULT 'active',
            dormant_since DATETIME,
            revival_conditions TEXT,
            times_revived INTEGER DEFAULT 0,
            times_contradicted INTEGER DEFAULT 0,
            min_applications INTEGER DEFAULT 10,
            last_confidence_update DATETIME,
            update_count_today INTEGER DEFAULT 0,
            update_count_reset_date DATE,
            last_used_at DATETIME,
            confidence_ema REAL,
            ema_alpha REAL,
            ema_warmup_remaining INTEGER DEFAULT 0,
            last_ema_update DATETIME,
            fraud_flags INTEGER DEFAULT 0,
            is_quarantined INTEGER DEFAULT 0,
            last_fraud_check DATETIME,
            project_path TEXT DEFAULT NULL
        );

        -- Eviction candidates view
        CREATE VIEW eviction_candidates AS
        SELECT
            h.id,
            h.domain,
            h.rule,
            COALESCE(h.status, 'active') as status,
            h.confidence,
            h.times_validated,
            h.times_violated,
            COALESCE(h.times_contradicted, 0) as times_contradicted,
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
            CASE
                WHEN (h.times_validated + h.times_violated + COALESCE(h.times_contradicted, 0)) < 10 THEN NULL
                ELSE CAST(COALESCE(h.times_contradicted, 0) AS REAL) /
                     (h.times_validated + h.times_violated + COALESCE(h.times_contradicted, 0))
            END AS contradiction_rate,
            (h.times_validated + h.times_violated + COALESCE(h.times_contradicted, 0)) AS total_applications,
            CAST(julianday('now') - julianday(COALESCE(h.last_used_at, h.created_at)) AS INTEGER) AS days_since_use
        FROM heuristics h
        WHERE COALESCE(h.status, 'active') = 'active' OR COALESCE(h.status, 'active') = 'dormant'
        ORDER BY eviction_score ASC;

        -- Domain metadata table for elasticity
        CREATE TABLE domain_metadata (
            domain TEXT PRIMARY KEY,
            soft_limit INTEGER NOT NULL DEFAULT 5,
            hard_limit INTEGER NOT NULL DEFAULT 10,
            ceo_override_limit INTEGER,
            current_count INTEGER NOT NULL DEFAULT 0,
            state TEXT NOT NULL DEFAULT 'normal' CHECK(state IN ('normal', 'overflow', 'critical')),
            overflow_entered_at DATETIME,
            expansion_min_confidence REAL DEFAULT 0.70,
            expansion_min_validations INTEGER DEFAULT 3,
            expansion_min_novelty REAL DEFAULT 0.60,
            grace_period_days INTEGER DEFAULT 7,
            max_overflow_days INTEGER DEFAULT 28,
            avg_confidence REAL,
            health_score REAL,
            last_health_check DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CHECK(soft_limit > 0),
            CHECK(hard_limit >= soft_limit),
            CHECK(expansion_min_confidence >= 0.0 AND expansion_min_confidence <= 1.0),
            CHECK(expansion_min_novelty >= 0.0 AND expansion_min_novelty <= 1.0),
            CHECK(ceo_override_limit IS NULL OR ceo_override_limit >= hard_limit)
        );

        -- Heuristic merges table
        CREATE TABLE heuristic_merges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_ids TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            merge_reason TEXT,
            merge_strategy TEXT,
            similarity_score REAL,
            merged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (target_id) REFERENCES heuristics(id) ON DELETE CASCADE
        );

        -- Expansion events table
        CREATE TABLE expansion_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            heuristic_id INTEGER,
            event_type TEXT NOT NULL CHECK(event_type IN ('expansion', 'contraction', 'merge')),
            count_before INTEGER NOT NULL,
            count_after INTEGER NOT NULL,
            quality_score REAL,
            novelty_score REAL,
            health_score REAL,
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE SET NULL
        );

        -- Revival triggers table
        CREATE TABLE revival_triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            heuristic_id INTEGER NOT NULL,
            trigger_type TEXT NOT NULL,
            trigger_value TEXT NOT NULL,
            priority INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 1,
            last_checked DATETIME,
            times_triggered INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_revival_heuristic ON revival_triggers(heuristic_id);
        CREATE INDEX idx_revival_type ON revival_triggers(trigger_type);
        CREATE INDEX idx_revival_active ON revival_triggers(is_active);

        -- Triggers to sync domain counts and state
        CREATE TRIGGER sync_domain_counts_on_insert
        AFTER INSERT ON heuristics
        FOR EACH ROW
        BEGIN
            INSERT OR IGNORE INTO domain_metadata(domain) VALUES (NEW.domain);
            UPDATE domain_metadata
            SET
                current_count = (
                    SELECT COUNT(*) FROM heuristics
                    WHERE domain = NEW.domain AND status = 'active'
                ),
                state = CASE
                    WHEN (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') > hard_limit THEN 'critical'
                    WHEN (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') > soft_limit THEN 'overflow'
                    ELSE 'normal'
                END,
                overflow_entered_at = CASE
                    WHEN state = 'normal' AND (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') > soft_limit
                        THEN datetime('now')
                    WHEN state != 'normal' AND (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') <= soft_limit
                        THEN NULL
                    ELSE overflow_entered_at
                END,
                updated_at = datetime('now')
            WHERE domain = NEW.domain;
        END;

        CREATE TRIGGER sync_domain_counts_on_update
        AFTER UPDATE ON heuristics
        FOR EACH ROW
        BEGIN
            INSERT OR IGNORE INTO domain_metadata(domain) VALUES (NEW.domain);
            UPDATE domain_metadata
            SET
                current_count = (
                    SELECT COUNT(*) FROM heuristics
                    WHERE domain = NEW.domain AND status = 'active'
                ),
                state = CASE
                    WHEN (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') > hard_limit THEN 'critical'
                    WHEN (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') > soft_limit THEN 'overflow'
                    ELSE 'normal'
                END,
                overflow_entered_at = CASE
                    WHEN state = 'normal' AND (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') > soft_limit
                        THEN datetime('now')
                    WHEN state != 'normal' AND (SELECT COUNT(*) FROM heuristics WHERE domain = NEW.domain AND status = 'active') <= soft_limit
                        THEN NULL
                    ELSE overflow_entered_at
                END,
                updated_at = datetime('now')
            WHERE domain = NEW.domain;
        END;

        CREATE TRIGGER sync_domain_counts_on_delete
        AFTER DELETE ON heuristics
        FOR EACH ROW
        BEGIN
            UPDATE domain_metadata
            SET
                current_count = (
                    SELECT COUNT(*) FROM heuristics
                    WHERE domain = OLD.domain AND status = 'active'
                ),
                state = CASE
                    WHEN (SELECT COUNT(*) FROM heuristics WHERE domain = OLD.domain AND status = 'active') > hard_limit THEN 'critical'
                    WHEN (SELECT COUNT(*) FROM heuristics WHERE domain = OLD.domain AND status = 'active') > soft_limit THEN 'overflow'
                    ELSE 'normal'
                END,
                overflow_entered_at = CASE
                    WHEN state = 'normal' AND (SELECT COUNT(*) FROM heuristics WHERE domain = OLD.domain AND status = 'active') > soft_limit
                        THEN datetime('now')
                    WHEN state != 'normal' AND (SELECT COUNT(*) FROM heuristics WHERE domain = OLD.domain AND status = 'active') <= soft_limit
                        THEN NULL
                    ELSE overflow_entered_at
                END,
                updated_at = datetime('now')
            WHERE domain = OLD.domain;
        END;
    """)
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def manager(temp_db):
    """Create a LifecycleManager instance with temp database."""
    return LifecycleManager(db_path=Path(temp_db))


# ==============================================================
# Test 1: Normal Operation (Under Soft Limit)
# ==============================================================

def test_normal_operation(manager):
    """Domain operates normally under soft limit."""
    domain = "test-normal"

    # Add 5 heuristics (at soft limit)
    heuristic_ids = []
    for i in range(5):
        conn = manager._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Test rule {i}", 0.60, 2))
            heuristic_ids.append(cursor.lastrowid)
            conn.commit()
        finally:
            conn.close()

    # Check state
    state = manager.get_domain_state(domain)
    assert state['current_count'] == 5, f"Expected 5, got {state['current_count']}"
    assert state['state'] == 'normal', f"Expected normal, got {state['state']}"
    assert state['overflow_entered_at'] is None

    # Verify can_add_heuristic allows adding (not at hard limit yet)
    can_add, reason = manager.can_add_heuristic(domain)
    assert can_add == True, f"Should be able to add: {reason}"


# ==============================================================
# Test 2: Expansion Trigger (Quality 6th Heuristic)
# ==============================================================

def test_expansion_trigger(manager):
    """Domain expands when exceptional heuristic arrives."""
    domain = "test-expansion"

    # Add 5 normal heuristics
    for i in range(5):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.60, 3))
            conn.commit()
        finally:
            conn.close()

    # Check eligibility for exceptional 6th heuristic
    heuristic_data = {
        "rule": "Exceptional rule with unique keywords xyz",
        "confidence": 0.80,
        "times_validated": 5
    }

    eligibility = manager.check_expansion_eligibility(heuristic_data, domain)

    # Should be eligible for expansion
    assert eligibility['eligible'] == True, f"Should be eligible: {eligibility['reason']}"
    assert eligibility['quality_gate_passed'] == True
    assert eligibility['scores']['confidence'] == 0.80
    assert eligibility['scores']['validations'] == 5
    assert eligibility['scores']['novelty'] > 0.60  # Novel keywords

    # Actually add the 6th heuristic
    conn = manager._get_connection()
    try:
        conn.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (domain, heuristic_data['rule'], heuristic_data['confidence'],
              heuristic_data['times_validated']))
        conn.commit()
    finally:
        conn.close()

    # Verify expansion
    state = manager.get_domain_state(domain)
    assert state['current_count'] == 6, f"Expected 6, got {state['current_count']}"
    assert state['state'] == 'overflow', f"Expected overflow, got {state['state']}"
    assert state['overflow_entered_at'] is not None


# ==============================================================
# Test 3: Hard Limit Enforcement
# ==============================================================

def test_hard_limit_enforcement(manager):
    """Hard limit cannot be exceeded."""
    domain = "test-hard-limit"

    # Add 10 heuristics (at hard limit)
    for i in range(10):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.70 + (i * 0.02), 5))
            conn.commit()
        finally:
            conn.close()

    state = manager.get_domain_state(domain)
    assert state['current_count'] == 10, f"Expected 10, got {state['current_count']}"
    assert state['state'] in ['overflow', 'critical']

    # Try to add 11th heuristic
    can_add, reason = manager.can_add_heuristic(domain)
    assert can_add == False, "Should not be able to add at hard limit"
    assert "Hard limit" in reason


# ==============================================================
# Test 4: Novelty Detection
# ==============================================================

def test_novelty_detection(manager):
    """Duplicate heuristics are detected via novelty score."""
    domain = "test-novelty"

    # Add original heuristic
    conn = manager._get_connection()
    try:
        conn.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (domain, "Use refs for callbacks to prevent useEffect loops", 0.75, 5))
        conn.commit()
    finally:
        conn.close()

    # Calculate novelty for very similar heuristic
    similar_rule = "Store callbacks in refs to avoid useEffect dependencies"
    novelty = manager.calculate_novelty_score(similar_rule, domain)

    # Should have moderate novelty (some overlap but different wording)
    # Note: Jaccard on keywords gives ~0.62 novelty due to different words
    assert novelty < 0.80, f"Expected moderate-low novelty (<0.80), got {novelty:.2f}"
    assert novelty > 0.30, f"Should have some similarity (>0.30 novelty), got {novelty:.2f}"

    # Calculate novelty for different heuristic
    different_rule = "Always validate database schema migrations before deployment"
    novelty_different = manager.calculate_novelty_score(different_rule, domain)

    # Should have high novelty
    assert novelty_different > 0.60, f"Expected high novelty (>0.60), got {novelty_different:.2f}"


# ==============================================================
# Test 5: Merge Candidate Detection
# ==============================================================

def test_merge_candidates(manager):
    """Similar heuristics are identified for merging."""
    domain = "test-merge"

    # Add 2 similar heuristics
    conn = manager._get_connection()
    try:
        conn.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (domain, "Always use refs for callbacks", 0.70, 5))

        conn.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (domain, "Use useRef for callback storage", 0.65, 3))

        # Add some dissimilar ones
        for i in range(3):
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Completely different rule about topic {i}", 0.60, 2))

        conn.commit()
    finally:
        conn.close()

    # Find merge candidates
    result = manager.find_merge_candidates(domain)

    assert len(result['candidates']) > 0, "Should find merge candidates"

    # Check that similar heuristics are identified
    top_candidate = result['candidates'][0]
    assert top_candidate['similarity'] >= 0.40, f"Expected similarity >= 0.40, got {top_candidate['similarity']}"


# ==============================================================
# Test 6: Merge Execution
# ==============================================================

def test_merge_execution(manager):
    """Heuristics can be successfully merged."""
    domain = "test-merge-exec"

    # Add 2 heuristics to merge
    conn = manager._get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO heuristics (domain, rule, explanation, confidence, times_validated,
                                   times_violated, times_contradicted, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (domain, "Rule A", "Explanation A", 0.75, 10, 2, 0))
        id1 = cursor.lastrowid

        cursor = conn.execute("""
            INSERT INTO heuristics (domain, rule, explanation, confidence, times_validated,
                                   times_violated, times_contradicted, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (domain, "Rule B", "Explanation B", 0.65, 5, 1, 0))
        id2 = cursor.lastrowid

        conn.commit()
    finally:
        conn.close()

    # Perform merge
    result = manager.merge_heuristics([id1, id2], "Combined rules A and B")

    assert result['success'] == True, f"Merge failed: {result.get('reason')}"
    assert result['space_saved'] == 1, "Should save 1 space (2->1)"
    assert result['total_validations'] == 15, "Should sum validations (10+5)"
    assert result['total_violations'] == 3, "Should sum violations (2+1)"

    # Verify source heuristics are archived
    conn = manager._get_connection()
    try:
        cursor = conn.execute("SELECT status FROM heuristics WHERE id IN (?, ?)", (id1, id2))
        statuses = [row['status'] for row in cursor.fetchall()]
        assert all(s == 'archived' for s in statuses), "Source heuristics should be archived"

        # Verify merged heuristic exists
        cursor = conn.execute("SELECT * FROM heuristics WHERE id = ?", (result['target_id'],))
        merged = cursor.fetchone()
        assert merged is not None, "Merged heuristic should exist"
        assert merged['status'] == 'active', "Merged heuristic should be active"
        assert "[MERGED]" in merged['rule'], "Merged rule should be marked"
    finally:
        conn.close()


# ==============================================================
# Test 7: Grace Period
# ==============================================================

def test_grace_period(manager):
    """Contraction does not occur during grace period."""
    domain = "test-grace"

    # Add 7 heuristics (in overflow)
    for i in range(7):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.60, 2))
            conn.commit()
        finally:
            conn.close()

    # Manually set overflow_entered_at to 3 days ago (within grace period)
    conn = manager._get_connection()
    try:
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        conn.execute("""
            UPDATE domain_metadata
            SET overflow_entered_at = ?
            WHERE domain = ?
        """, (three_days_ago, domain))
        conn.commit()
    finally:
        conn.close()

    # Try to trigger contraction
    result = manager.trigger_contraction(domain)

    # Should fail due to grace period
    assert result['success'] == False, "Should not contract during grace period"
    assert result.get('grace_period') == True, "Should indicate grace period"

    # Verify count unchanged
    state = manager.get_domain_state(domain)
    assert state['current_count'] == 7, "Count should be unchanged"


# ==============================================================
# Test 8: Contraction After Grace Period
# ==============================================================

def test_contraction_after_grace(manager):
    """Domain contracts after grace period ends."""
    domain = "test-contraction"

    # Add 8 heuristics with varying quality
    for i in range(8):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.50 + (i * 0.05), 2 + i))
            conn.commit()
        finally:
            conn.close()

    # Set overflow_entered_at to 14 days ago (past grace period of 7 days, 1 week into contraction)
    # Formula: weeks_past_grace * 2 = reduction target
    # 14 days = 7 grace + 7 past grace = 1 week past grace = target_reduction of 2
    conn = manager._get_connection()
    try:
        fourteen_days_ago = (datetime.now() - timedelta(days=14)).isoformat()
        conn.execute("""
            UPDATE domain_metadata
            SET overflow_entered_at = ?
            WHERE domain = ?
        """, (fourteen_days_ago, domain))
        conn.commit()
    finally:
        conn.close()

    # Trigger contraction
    result = manager.trigger_contraction(domain)

    # Should succeed
    assert result['success'] == True, f"Contraction failed: {result.get('reason')}"
    assert result['total_reduced'] > 0, "Should have reduced some heuristics"

    # Verify count reduced
    state = manager.get_domain_state(domain)
    assert state['current_count'] < 8, f"Count should be reduced from 8, got {state['current_count']}"


# ==============================================================
# Test 9: Expansion Eligibility Checks
# ==============================================================

def test_expansion_eligibility_below_soft_limit(manager):
    """Heuristics below soft limit don't need quality gate."""
    domain = "test-elig-below"

    # Add 3 heuristics (below soft limit of 5)
    for i in range(3):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.60, 2))
            conn.commit()
        finally:
            conn.close()

    # Check eligibility for low-quality heuristic
    heuristic_data = {
        "rule": "Low quality rule",
        "confidence": 0.40,
        "times_validated": 1
    }

    eligibility = manager.check_expansion_eligibility(heuristic_data, domain)

    # Should be eligible because below soft limit (no quality gate)
    assert eligibility['eligible'] == True, "Should be eligible below soft limit"
    assert eligibility['below_soft_limit'] == True
    assert eligibility['quality_gate_passed'] == False


def test_expansion_eligibility_quality_gate(manager):
    """Quality gate blocks low-quality heuristics above soft limit."""
    domain = "test-elig-gate"

    # Add 5 heuristics (at soft limit)
    for i in range(5):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.60, 3))
            conn.commit()
        finally:
            conn.close()

    # Check eligibility for low-quality heuristic
    heuristic_data = {
        "rule": "Low quality rule",
        "confidence": 0.40,  # Below threshold
        "times_validated": 1
    }

    eligibility = manager.check_expansion_eligibility(heuristic_data, domain)

    # Should NOT be eligible (quality gate)
    assert eligibility['eligible'] == False, "Low quality should be blocked"
    assert eligibility['below_soft_limit'] == False
    assert "confidence" in eligibility['reason'].lower()


# ==============================================================
# Test 10: CEO Override Limit
# ==============================================================

def test_ceo_override_limit(manager):
    """CEO can override hard limit for specific domain."""
    domain = "test-ceo-override"

    # Add 10 heuristics (at normal hard limit)
    for i in range(10):
        conn = manager._get_connection()
        try:
            conn.execute("""
                INSERT INTO heuristics (domain, rule, confidence, times_validated, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (domain, f"Rule {i}", 0.70, 5))
            conn.commit()
        finally:
            conn.close()

    # Verify at hard limit
    can_add, _ = manager.can_add_heuristic(domain)
    assert can_add == False, "Should be at hard limit"

    # CEO sets override to 15
    conn = manager._get_connection()
    try:
        conn.execute("""
            UPDATE domain_metadata
            SET ceo_override_limit = 15
            WHERE domain = ?
        """, (domain,))
        conn.commit()
    finally:
        conn.close()

    # Now should be able to add
    can_add, reason = manager.can_add_heuristic(domain)
    assert can_add == True, f"Should be able to add with CEO override: {reason}"

    # Verify state reflects CEO override
    state = manager.get_domain_state(domain)
    assert state['ceo_override_limit'] == 15


# ==============================================================
# Run tests
# ==============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
