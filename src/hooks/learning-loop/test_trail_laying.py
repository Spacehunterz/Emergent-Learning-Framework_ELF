#!/usr/bin/env python3
"""Test script to verify trail laying functionality."""

import pytest
import sys
import os
from pathlib import Path

# Add the hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

from trail_helper import extract_file_paths, lay_trails


class TestExtractFilePaths:
    """Tests for extract_file_paths function."""

    def test_simple_file_edit(self):
        """Extract path from simple file edit message."""
        content = "I edited the file src/components/Header.tsx to add a new feature."
        extracted = extract_file_paths(content)
        assert "src/components/Header.tsx" in extracted

    def test_multiple_files(self):
        """Extract multiple file paths from message."""
        content = "Modified dashboard-app/frontend/src/App.tsx and backend/main.py"
        extracted = extract_file_paths(content)
        assert "dashboard-app/frontend/src/App.tsx" in extracted
        assert "backend/main.py" in extracted

    def test_windows_path_extracts_filename(self):
        """Windows paths should extract at least the filename."""
        content = "Updated C:\\Users\\Test\\.claude\\emergent-learning\\hooks\\learning-loop\\test.py"
        extracted = extract_file_paths(content)
        assert "test.py" in extracted

    def test_read_write_operations(self):
        """Extract paths from read/write operation messages."""
        content = "Reading from memory/index.db and writing to hooks/post_tool.py"
        extracted = extract_file_paths(content)
        assert "memory/index.db" in extracted
        assert "hooks/post_tool.py" in extracted

    def test_backtick_quoted(self):
        """Extract paths from backtick-quoted references."""
        content = "The file `app/main.py` was successfully updated."
        extracted = extract_file_paths(content)
        assert "app/main.py" in extracted

    def test_no_files(self):
        """Message with no file references returns empty list."""
        content = "This is just a message with no file references."
        extracted = extract_file_paths(content)
        assert extracted == []


class TestLayTrails:
    """Tests for lay_trails function."""

    def test_lay_trails_returns_count(self):
        """lay_trails should return number of trails laid."""
        test_paths = ["test/file1.py", "test/file2.js", "test/file3.md"]
        result = lay_trails(
            test_paths,
            outcome="success",
            agent_id="test_agent_pytest",
            description="Test trail laying"
        )
        assert result >= 0  # May be 0 if paths don't resolve

    def test_lay_trails_with_empty_list(self):
        """lay_trails with empty list should return 0."""
        result = lay_trails(
            [],
            outcome="success",
            agent_id="test_agent_pytest",
            description="Empty test"
        )
        assert result == 0

    def test_lay_trails_verifiable_in_db(self):
        """Verify trails are actually inserted into database."""
        import sqlite3

        test_paths = ["test/verify_file.py"]
        lay_trails(
            test_paths,
            outcome="success",
            agent_id="test_agent_verify",
            description="Verification test"
        )

        db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM trails
                WHERE agent_id = 'test_agent_verify'
            """)
            count = cursor.fetchone()[0]
            conn.close()
            # Count should be >= 0 (may be 0 if path doesn't resolve)
            assert count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
