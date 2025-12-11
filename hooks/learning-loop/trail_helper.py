"""Helper module for laying trails in the emergent learning database."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


def extract_file_paths(content):
    """Extract file paths mentioned in task output."""
    import sys

    sys.stderr.write(f"[TRAIL_DEBUG] extract_file_paths: content length = {len(content)}\n")
    file_paths = set()

    # Patterns for various file path formats
    # Order matters: more specific patterns first
    patterns = [
        # Backtick-quoted paths (highest priority - explicit)
        (r'`([^\s`]+\.\w{1,10})`', 'backtick'),
        # Explicit file references with quotes
        (r'["\']([^"\']+\.\w{1,10})["\']', 'quoted'),
        # file_path parameter
        (r'file_path["\']?\s*[:=]\s*[`"\']?([^\s`"\']+\.\w{1,10})[`"\']?', 'file_path_param'),
        # Windows absolute paths (capture full relative path from common dirs)
        (r'[A-Za-z]:\\(?:[^\\]+\\)*?\.claude\\emergent-learning\\([^\s`"\'\\]+(?:\\[^\s`"\'\\]+)*\.\w{1,10})', 'win_emergent'),
        (r'[A-Za-z]:\\(?:[^\\]+\\)*?(dashboard-app[^\s`"\'\\]+(?:\\[^\s`"\'\\]+)*\.\w{1,10})', 'win_dashboard'),
        (r'[A-Za-z]:\\(?:[^\\]+\\)*?((?:src|lib|app|components|hooks|memory|frontend|backend)[^\s`"\'\\]+(?:\\[^\s`"\'\\]+)*\.\w{1,10})', 'win_common'),
        # Unix absolute paths (capture relative path from common dirs)
        (r'/(?:[^/]+/)*?\.claude/emergent-learning/([^\s`"\'/]+(?:/[^\s`"\'/]+)*\.\w{1,10})', 'unix_emergent'),
        (r'/(?:[^/]+/)*?(dashboard-app[^\s`"\'/]+(?:/[^\s`"\'/]+)*\.\w{1,10})', 'unix_dashboard'),
        (r'/(?:[^/]+/)*?((?:src|lib|app|components|hooks|memory|frontend|backend)[^\s`"\'/]+(?:/[^\s`"\'/]+)*\.\w{1,10})', 'unix_common'),
        # Relative paths with common prefixes (capture full path)
        (r'\b((?:src|lib|app|components|dashboard-app|hooks|memory|frontend|backend)/[^\s`"\']+\.\w{1,10})\b', 'relative'),
        # Action-based patterns (last resort - can be noisy)
        (r'(?:created|modified|edited|wrote|updated|reading|writing|editing)\s+(?:the\s+)?(?:file\s+)?[`"\']?([^\s`"\']+\.\w{1,10})[`"\']?', 'action'),
        # File: prefix
        (r'File:\s*[`"\']?([^\s`"\']+\.\w{1,10})[`"\']?', 'file_prefix'),
    ]

    for i, (pattern, pattern_name) in enumerate(patterns):
        try:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                sys.stderr.write(f"[TRAIL_DEBUG] Pattern {i} ({pattern_name}) matched {len(matches)} paths\n")
            for match in matches:
                path = match.strip('`"\'')
                # Clean up Windows paths
                path = path.replace('\\', '/')
                if len(path) > 3 and not path.startswith('http'):
                    # Check if this is a substring of an already-found path or vice versa
                    # Keep the longer one
                    is_duplicate = False
                    to_remove = set()
                    for existing_path in file_paths:
                        if path in existing_path:
                            # Current path is substring of existing - skip it
                            is_duplicate = True
                            break
                        elif existing_path in path:
                            # Existing path is substring of current - replace it
                            to_remove.add(existing_path)

                    # Remove shorter paths
                    file_paths -= to_remove

                    if not is_duplicate:
                        file_paths.add(path)
                        sys.stderr.write(f"[TRAIL_DEBUG] Added path: {path}\n")
                    else:
                        sys.stderr.write(f"[TRAIL_DEBUG] Skipped duplicate substring: {path}\n")
        except Exception as e:
            sys.stderr.write(f"[TRAIL_DEBUG] Pattern {i} ({pattern_name}) failed: {e}\n")

    sys.stderr.write(f"[TRAIL_DEBUG] extract_file_paths: returning {len(file_paths)} paths\n")
    return list(file_paths)


def lay_trails(file_paths, outcome, agent_id=None, description=None):
    """Record trails for files touched by the task."""
    import sys

    # Debug: Log entry
    sys.stderr.write(f"[TRAIL_DEBUG] lay_trails called with {len(file_paths) if file_paths else 0} paths\n")

    if not file_paths:
        sys.stderr.write("[TRAIL_DEBUG] No file paths provided, skipping trail laying\n")
        return 0

    if not DB_PATH.exists():
        sys.stderr.write(f"[TRAIL_DEBUG] Database not found at {DB_PATH}\n")
        return 0

    try:
        sys.stderr.write(f"[TRAIL_DEBUG] Connecting to database: {DB_PATH}\n")
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        cursor = conn.cursor()

        scent = "discovery" if outcome == "success" else "warning" if outcome == "failure" else "hot"
        strength = 1.0 if outcome == "success" else 0.8

        sys.stderr.write(f"[TRAIL_DEBUG] Outcome={outcome}, scent={scent}, strength={strength}\n")

        for file_path in file_paths:
            message = (description[:50] if description else "Touched by Task agent")
            sys.stderr.write(f"[TRAIL_DEBUG] Recording trail: {file_path}\n")
            cursor.execute(
                "INSERT INTO trails (run_id, location, scent, strength, agent_id, message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (None, file_path, scent, strength, agent_id, message, datetime.now().isoformat())
            )

        conn.commit()
        conn.close()
        sys.stderr.write(f"[TRAIL_DEBUG] Successfully recorded {len(file_paths)} trails\n")
        return len(file_paths)
    except Exception as e:
        sys.stderr.write(f"[TRAIL_ERROR] Failed to lay trails: {type(e).__name__}: {e}\n")
        import traceback
        sys.stderr.write(f"[TRAIL_ERROR] Traceback: {traceback.format_exc()}\n")
        return 0
