"""Helper module for laying trails in the emergent learning database."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


def extract_file_paths(content):
    """Extract file paths mentioned in task output."""
    file_paths = set()

    # Patterns for various file path formats
    patterns = [
        # Action-based patterns
        r'(?:created|modified|edited|wrote|updated|read|reading|writing|editing)\s+[`"\']?([^\s`"\']+\.\w{1,10})[`"\']?',
        # Explicit file references
        r'File:\s*[`"\']?([^\s`"\']+\.\w{1,10})[`"\']?',
        r'file_path["\']?\s*[:=]\s*[`"\']?([^\s`"\']+\.\w{1,10})[`"\']?',
        # Unix-style relative paths
        r'(src/[^\s`"\']+\.\w{1,10})',
        r'(lib/[^\s`"\']+\.\w{1,10})',
        r'(app/[^\s`"\']+\.\w{1,10})',
        r'(components/[^\s`"\']+\.\w{1,10})',
        r'(dashboard-app/[^\s`"\']+\.\w{1,10})',
        r'(hooks/[^\s`"\']+\.\w{1,10})',
        r'(memory/[^\s`"\']+\.\w{1,10})',
        r'(frontend/[^\s`"\']+\.\w{1,10})',
        r'(backend/[^\s`"\']+\.\w{1,10})',
        # Windows absolute paths (normalize to relative)
        r'[A-Za-z]:\\[^\s`"\']+\\([^\s`"\'\\]+\.\w{1,10})',
        # Unix absolute paths (normalize to relative)
        r'/[^\s`"\']+/([^\s`"\'/]+\.\w{1,10})',
        # Backtick-quoted paths
        r'`([^\s`]+\.\w{1,10})`',
    ]

    for pattern in patterns:
        try:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                path = match.strip('`"\'')
                # Clean up Windows paths
                path = path.replace('\\', '/')
                if len(path) > 3 and not path.startswith('http'):
                    file_paths.add(path)
        except Exception:
            pass

    return list(file_paths)


def lay_trails(file_paths, outcome, agent_id=None, description=None):
    """Record trails for files touched by the task."""
    if not file_paths or not DB_PATH.exists():
        return
    
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        cursor = conn.cursor()
        
        scent = "discovery" if outcome == "success" else "warning" if outcome == "failure" else "hot"
        strength = 1.0 if outcome == "success" else 0.8
        
        for file_path in file_paths:
            message = (description[:50] if description else "Touched by Task agent")
            cursor.execute(
                "INSERT INTO trails (run_id, location, scent, strength, agent_id, message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (None, file_path, scent, strength, agent_id, message, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        return len(file_paths)
    except Exception as e:
        return 0
