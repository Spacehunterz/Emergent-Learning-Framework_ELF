#!/usr/bin/env python3
"""
Test script for the diff endpoint logic
"""
import sqlite3
from pathlib import Path

# Simulate the diff endpoint logic
DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

def test_diff_endpoint(run_id: int):
    """Test the diff endpoint logic"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify run exists
    cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
    run = cursor.fetchone()

    if not run:
        print(f"Run {run_id} not found")
        return None

    print(f"Found run: {dict(run)['workflow_name']}")

    # Get trails (file locations touched) for this run
    cursor.execute("""
        SELECT DISTINCT location, scent, message
        FROM trails
        WHERE run_id = ? AND location_type = 'file'
        ORDER BY location
    """, (run_id,))
    trails = cursor.fetchall()

    print(f"Found {len(trails)} file trails")

    # Generate mock diffs based on trails
    diffs = []
    for trail in trails:
        location = trail["location"]
        scent = trail["scent"]
        message = trail["message"] or "Modified file"

        print(f"  - {location} ({scent}): {message}")

        # Create a realistic-looking mock diff
        if scent == "blocker":
            changes = [
                {"type": "context", "lineNumber": 1, "oldLineNumber": 10, "newLineNumber": 10, "content": "def process_data(data):"},
                {"type": "remove", "lineNumber": 3, "oldLineNumber": 12, "content": "        raise ValueError('Data is empty')"},
                {"type": "add", "lineNumber": 4, "newLineNumber": 12, "content": "        logger.warning('Empty data received, using defaults')"},
            ]
            diffs.append({
                "path": location,
                "changes": changes,
                "additions": 2,
                "deletions": 1
            })

    conn.close()

    result = {
        "run_id": run_id,
        "diffs": diffs,
        "note": "This is mock data. Future versions will track actual file changes."
    }

    return result

if __name__ == "__main__":
    import json
    result = test_diff_endpoint(45)
    if result:
        print("\nResult:")
        print(json.dumps(result, indent=2))
