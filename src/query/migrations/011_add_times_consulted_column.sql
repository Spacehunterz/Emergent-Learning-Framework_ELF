-- Migration 011: Add times_consulted column to heuristics table
-- Purpose: Track how many times heuristics were consulted, even when outcome is unknown
-- Related: Discussion #86 - "Unknown" Outcome Not Validated
--
-- When task outcomes are "unknown" (e.g., background tasks, minimal output),
-- we still want to record that the heuristic was consulted, without adjusting
-- confidence. This provides better tracking and usage analytics.

-- Add times_consulted column with default value 0
ALTER TABLE heuristics ADD COLUMN times_consulted INTEGER DEFAULT 0;

-- Create index for performance on queries filtering by times_consulted
CREATE INDEX IF NOT EXISTS idx_heuristics_times_consulted ON heuristics(times_consulted);

-- Update any existing records to have times_consulted = times_validated + times_violated
-- This provides a baseline for existing data (consulted = validated + violated)
UPDATE heuristics
SET times_consulted = times_validated + times_violated
WHERE times_consulted = 0;

-- Log the migration
INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
VALUES ('migration', '011_add_times_consulted_column', 1, 'schema', 'Added times_consulted column to heuristics table');
