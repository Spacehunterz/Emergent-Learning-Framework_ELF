-- Session Summaries Table
-- Stores haiku-generated summaries of Claude sessions to prevent context flooding

CREATE TABLE IF NOT EXISTS session_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,           -- UUID from .jsonl filename
    project TEXT NOT NULL,                      -- Project name

    -- Summary content (haiku-generated)
    tool_summary TEXT,                          -- "Read 5 files, edited 3, ran 12 bash commands"
    content_summary TEXT,                       -- "Modified auth module, added user tests"
    conversation_summary TEXT,                  -- "Fixed login bug: investigated, patched, tested"

    -- Extracted metadata
    files_touched TEXT DEFAULT '[]',            -- JSON array of file paths
    tool_counts TEXT DEFAULT '{}',              -- JSON: {"Read": 5, "Edit": 3, "Bash": 12}
    message_count INTEGER DEFAULT 0,

    -- Source info
    session_file_path TEXT,                     -- Full path to .jsonl
    session_file_size INTEGER,                  -- Size in bytes
    session_last_modified DATETIME,             -- Last modified time of .jsonl

    -- Summary metadata
    summarized_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    summarizer_model TEXT DEFAULT 'haiku',      -- Which model created summary
    summary_version INTEGER DEFAULT 1,          -- For future format changes

    -- Flags
    is_stale INTEGER DEFAULT 0,                 -- 1 if session modified after summary
    needs_resummarize INTEGER DEFAULT 0         -- 1 if should be re-summarized
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_session_summaries_session_id ON session_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_session_summaries_project ON session_summaries(project);
CREATE INDEX IF NOT EXISTS idx_session_summaries_summarized ON session_summaries(summarized_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_summaries_stale ON session_summaries(is_stale);

-- Track schema version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (3, 'Added session_summaries table for haiku-generated session summaries');

ANALYZE session_summaries;
