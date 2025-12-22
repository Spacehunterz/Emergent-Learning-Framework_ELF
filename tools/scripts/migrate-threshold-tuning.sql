-- Database Migration: Adaptive Threshold Tuning
-- Phase 2D Enhancement - Agent 2
-- Date: 2025-12-13
--
-- Adds tables for threshold recommendations, history, and runtime overrides

-- ============================================
-- Threshold Recommendations (CEO Review Queue)
-- ============================================

CREATE TABLE IF NOT EXISTS threshold_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detector_name TEXT,  -- NULL for classification thresholds
    threshold_type TEXT NOT NULL CHECK(threshold_type IN ('detector', 'classification')),
    level TEXT,  -- 'suspicious', 'fraud_likely', 'fraud_confirmed' (for classification only)
    current_threshold REAL,
    recommended_threshold REAL,
    target_fpr REAL,
    achieved_fpr REAL,
    achieved_tpr REAL,
    sample_size INTEGER,
    tp_count INTEGER,
    fp_count INTEGER,
    confidence TEXT CHECK(confidence IN ('low', 'medium', 'high')),
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    reviewed_by TEXT,
    review_decision TEXT CHECK(review_decision IN
        ('approved', 'rejected', 'needs_more_data', NULL)),
    applied_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_threshold_recs_detector ON threshold_recommendations(detector_name);
CREATE INDEX IF NOT EXISTS idx_threshold_recs_pending ON threshold_recommendations(review_decision)
    WHERE review_decision IS NULL;
CREATE INDEX IF NOT EXISTS idx_threshold_recs_type ON threshold_recommendations(threshold_type);

-- ============================================
-- Threshold History (Rollback Capability)
-- ============================================

CREATE TABLE IF NOT EXISTS threshold_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detector_name TEXT,  -- NULL for classification thresholds
    threshold_type TEXT NOT NULL CHECK(threshold_type IN ('detector', 'classification')),
    level TEXT,  -- For classification: 'suspicious', 'fraud_likely', 'fraud_confirmed'
    old_threshold REAL,
    new_threshold REAL,
    changed_by TEXT,  -- 'system' or CEO username
    reason TEXT,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reverted_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_threshold_history_detector ON threshold_history(detector_name);
CREATE INDEX IF NOT EXISTS idx_threshold_history_applied ON threshold_history(applied_at DESC);
CREATE INDEX IF NOT EXISTS idx_threshold_history_level ON threshold_history(level);

-- ============================================
-- Per-Detector Threshold Overrides
-- ============================================

CREATE TABLE IF NOT EXISTS detector_thresholds (
    detector_name TEXT PRIMARY KEY,
    threshold REAL NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    reason TEXT
);

-- ============================================
-- Classification Threshold Overrides
-- ============================================

CREATE TABLE IF NOT EXISTS classification_thresholds (
    level TEXT PRIMARY KEY CHECK(level IN
        ('suspicious', 'fraud_likely', 'fraud_confirmed')),
    threshold REAL NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    reason TEXT
);

-- Initialize with current Phase 2D defaults
INSERT OR IGNORE INTO classification_thresholds (level, threshold, updated_by, reason) VALUES
    ('suspicious', 0.20, 'system', 'Initial Phase 2D defaults'),
    ('fraud_likely', 0.50, 'system', 'Initial Phase 2D defaults'),
    ('fraud_confirmed', 0.80, 'system', 'Initial Phase 2D defaults');

-- ============================================
-- Views
-- ============================================

-- Active thresholds summary
CREATE VIEW IF NOT EXISTS active_thresholds AS
SELECT
    'classification' as threshold_type,
    level as name,
    threshold,
    updated_by,
    last_updated
FROM classification_thresholds
UNION ALL
SELECT
    'detector' as threshold_type,
    detector_name as name,
    threshold,
    updated_by,
    last_updated
FROM detector_thresholds;

-- Pending recommendations summary
CREATE VIEW IF NOT EXISTS pending_threshold_recommendations AS
SELECT
    id,
    threshold_type,
    COALESCE(detector_name, level) as target,
    current_threshold,
    recommended_threshold,
    ABS(recommended_threshold - current_threshold) as change_magnitude,
    achieved_fpr,
    achieved_tpr,
    confidence,
    sample_size,
    created_at
FROM threshold_recommendations
WHERE review_decision IS NULL
ORDER BY created_at DESC;

-- Threshold change history summary
CREATE VIEW IF NOT EXISTS threshold_change_log AS
SELECT
    h.id,
    h.threshold_type,
    COALESCE(h.detector_name, h.level) as target,
    h.old_threshold,
    h.new_threshold,
    (h.new_threshold - h.old_threshold) as change_delta,
    h.changed_by,
    h.reason,
    h.applied_at,
    h.reverted_at,
    CASE WHEN h.reverted_at IS NOT NULL THEN 'reverted' ELSE 'active' END as status
FROM threshold_history h
ORDER BY h.applied_at DESC;
