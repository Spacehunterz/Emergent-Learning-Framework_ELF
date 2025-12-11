#!/usr/bin/env python3
"""Test script to verify trail laying functionality."""

import json
import sys
import os
from pathlib import Path

# Force UTF-8 encoding for output on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add the hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

from trail_helper import extract_file_paths, lay_trails

# Test cases with different output formats
test_cases = [
    {
        "name": "Simple file edit",
        "content": "I edited the file src/components/Header.tsx to add a new feature.",
        "expected_paths": ["src/components/Header.tsx"]
    },
    {
        "name": "Multiple files",
        "content": "Modified dashboard-app/frontend/src/App.tsx and backend/main.py",
        "expected_paths": ["dashboard-app/frontend/src/App.tsx", "backend/main.py"]
    },
    {
        "name": "Windows path",
        "content": "Updated C:\\Users\\Test\\.claude\\emergent-learning\\hooks\\learning-loop\\test.py",
        "expected_paths": ["test.py"]
    },
    {
        "name": "Read/Write operations",
        "content": "Reading from memory/index.db and writing to hooks/post_tool.py",
        "expected_paths": ["memory/index.db", "hooks/post_tool.py"]
    },
    {
        "name": "Backtick quoted",
        "content": "The file `app/main.py` was successfully updated.",
        "expected_paths": ["app/main.py"]
    },
    {
        "name": "No files",
        "content": "This is just a message with no file references.",
        "expected_paths": []
    }
]

print("=" * 60)
print("TRAIL LAYING TEST SUITE")
print("=" * 60)

total_tests = len(test_cases)
passed_tests = 0

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}/{total_tests}: {test['name']}")
    print(f"Content: {test['content'][:60]}...")

    extracted = extract_file_paths(test['content'])
    expected = test['expected_paths']

    print(f"Expected: {expected}")
    print(f"Extracted: {extracted}")

    # Check if all expected paths were found
    success = set(extracted) >= set(expected)

    if success:
        print("✓ PASS")
        passed_tests += 1
    else:
        print("✗ FAIL")
        missing = set(expected) - set(extracted)
        if missing:
            print(f"  Missing: {missing}")

print("\n" + "=" * 60)
print(f"EXTRACTION TESTS: {passed_tests}/{total_tests} passed")
print("=" * 60)

# Now test actual trail laying
print("\n" + "=" * 60)
print("TESTING DATABASE INSERTION")
print("=" * 60)

test_paths = ["test/file1.py", "test/file2.js", "test/file3.md"]
print(f"\nAttempting to lay trails for: {test_paths}")

result = lay_trails(test_paths, outcome="success", agent_id="test_agent", description="Test trail laying")

if result > 0:
    print(f"✓ Successfully laid {result} trails")

    # Query the database to verify
    import sqlite3
    from pathlib import Path

    db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT location, scent, strength, agent_id, message
        FROM trails
        WHERE agent_id = 'test_agent'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    rows = cursor.fetchall()
    conn.close()

    print(f"\nVerification: Found {len(rows)} trails in database")
    for row in rows:
        print(f"  - {row[0]} ({row[1]}, strength={row[2]}, agent={row[3]})")
else:
    print("✗ Failed to lay trails (check stderr for errors)")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
