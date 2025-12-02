#!/usr/bin/env python3
"""Quick fix for migration - handle missing updated_at column."""
import sqlite3
from pathlib import Path

home = Path.home()
db_path = home / ".claude" / "emergent-learning" / "memory" / "index.db"

conn = sqlite3.connect(str(db_path))

# Check current schema
cursor = conn.execute("PRAGMA table_info(learnings)")
columns = {row[1]: row for row in cursor.fetchall()}

print("Current columns:", list(columns.keys()))

# Check if updated_at exists
if 'updated_at' not in columns:
    print("Adding updated_at column...")
    conn.execute("ALTER TABLE learnings ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    conn.commit()
    print("Column added!")
else:
    print("updated_at column already exists")

conn.close()
