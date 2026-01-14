CREATE TABLE IF NOT EXISTS players (
    github_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    avatar_url TEXT,
    score INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_players_score ON players(score DESC);
