-- Migration: Cleanup test domains
-- Description: Remove test and invalid domain entries from heuristics table
-- Bug: #80 - Corrupted domain names in database

-- Begin transaction
BEGIN;

-- Delete test entries (these were created during testing and are not valid domains)
-- The 'test' and 'testing' domains are NOT valid domain names in the system
DELETE FROM heuristics
WHERE domain IN ('test', 'testing', 'fake', 'dummy', 'example');

-- Delete any heuristics with empty or NULL domains (if any exist)
DELETE FROM heuristics
WHERE domain IS NULL OR domain = '' OR domain = ' ';

-- Commit transaction
COMMIT;

-- Verification query (run after migration):
-- SELECT DISTINCT domain FROM heuristics ORDER BY domain;
