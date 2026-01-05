#!/usr/bin/env python3
"""
Session Index - Fast indexing and retrieval of Claude session history.

Scans ~/.claude/projects/*/jsonl files and extracts metadata WITHOUT
loading full content for performance. Provides lazy loading for full sessions.
"""

import json
import logging
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import re

logger = logging.getLogger(__name__)


@dataclass
class SessionMetadata:
    """Lightweight metadata for a session."""
    session_id: str
    project: str
    project_path: str
    first_timestamp: str
    last_timestamp: str
    prompt_count: int
    first_prompt_preview: str
    git_branch: str
    is_agent: bool
    file_path: str
    file_size: int
    is_partial: bool = False
    corruption_count: int = 0


@dataclass
class SessionMessage:
    """Individual message in a session."""
    uuid: str
    type: str  # 'user' or 'assistant'
    timestamp: str
    content: str
    is_command: bool = False
    tool_use: Optional[List[Dict[str, Any]]] = None
    thinking: Optional[str] = None


class SessionIndex:
    """
    Fast session indexer that scans JSONL files and extracts metadata.

    Features:
    - Scans ~/.claude/projects/*/jsonl
    - Parses metadata without loading full content
    - Handles edge cases (agent files, sidechains, encrypted thinking)
    - Provides lazy loading for full sessions
    """

    def __init__(self, projects_dir: Optional[Path] = None):
        # Default projects dir: check ELF_BASE_PATH/../../projects or ~/.claude/projects
        if projects_dir:
            self.projects_dir = projects_dir
        else:
            try:
                from utils.database import get_base_path
                self.base_path = get_base_path()
            except ImportError:
                # Fallback if utils.database is not available
                self.base_path = Path.home() / ".claude" / "emergent-learning"

            # If base path is inside .claude/emergent-learning, projects is likely ../../projects
            candidate = self.base_path.parent / "projects"
            if candidate.exists():
                self.projects_dir = candidate
            else:
                self.projects_dir = Path.home() / ".claude" / "projects"
        
        self._index: Dict[str, SessionMetadata] = {}
        self._last_scan: Optional[datetime] = None
        self._lock = threading.RLock()

        try:
            from utils.database import get_base_path
            self._db_path = get_base_path() / "memory" / "index.db"
        except ImportError:
            self._db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

    # Tools that commonly have large inputs (file contents)
    LARGE_INPUT_TOOLS = {"Read", "Write", "Edit", "NotebookEdit"}

    # Max chars for tool input display
    MAX_INPUT_CHARS = 500

    def _truncate_tool_input(self, tool_name: str, raw_input: Any, depth: int = 0) -> Any:
        """
        Truncate tool input to prevent context flooding.

        For file-based tools, shows path and truncation indicator.
        For other tools, truncates long string values.
        Includes depth limit to prevent memory leaks from deeply nested structures.
        """
        if depth > 3:
            return "[nested object truncated]"

        if not isinstance(raw_input, dict):
            if isinstance(raw_input, str) and len(raw_input) > self.MAX_INPUT_CHARS:
                return raw_input[:self.MAX_INPUT_CHARS] + "... [truncated]"
            return raw_input

        truncated = {}
        for key, value in raw_input.items():
            if key in ("file_path", "path", "filepath", "notebook_path"):
                truncated[key] = value
            elif key in ("content", "new_source", "old_string", "new_string"):
                if isinstance(value, str):
                    if len(value) > 100:
                        truncated[key] = value[:100] + f"... [{len(value)} chars truncated]"
                    else:
                        truncated[key] = value
                else:
                    truncated[key] = value
            elif isinstance(value, dict):
                truncated[key] = self._truncate_tool_input(tool_name, value, depth + 1)
            elif isinstance(value, list):
                truncated[key] = [self._truncate_tool_input(tool_name, item, depth + 1) for item in value[:10]]
                if len(value) > 10:
                    truncated[key].append(f"[{len(value) - 10} more items truncated]")
            elif isinstance(value, str) and len(value) > self.MAX_INPUT_CHARS:
                truncated[key] = value[:self.MAX_INPUT_CHARS] + "... [truncated]"
            else:
                truncated[key] = value

        if tool_name in self.LARGE_INPUT_TOOLS:
            truncated["_truncated"] = True

        return truncated

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get haiku-generated summary for a session from database.

        Returns:
            Summary dict or None if not summarized yet
        """
        try:
            import sqlite3
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tool_summary, content_summary, conversation_summary,
                       files_touched, tool_counts, message_count,
                       summarized_at, summarizer_model, is_stale
                FROM session_summaries
                WHERE session_id = ?
            """, (session_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                "tool_summary": row["tool_summary"],
                "content_summary": row["content_summary"],
                "conversation_summary": row["conversation_summary"],
                "files_touched": json.loads(row["files_touched"]) if row["files_touched"] else [],
                "tool_counts": json.loads(row["tool_counts"]) if row["tool_counts"] else {},
                "message_count": row["message_count"],
                "summarized_at": row["summarized_at"],
                "summarizer_model": row["summarizer_model"],
                "is_stale": bool(row["is_stale"])
            }

        except Exception as e:
            logger.error(f"Error fetching session summary: {e}")
            return None

    def scan(self) -> int:
        """
        Scan all projects for session files and build index.

        Returns:
            Number of sessions indexed
        """
        logger.info(f"Scanning projects directory: {self.projects_dir}")

        if not self.projects_dir.exists():
            logger.warning(f"Projects directory does not exist: {self.projects_dir}")
            return 0

        new_index: Dict[str, SessionMetadata] = {}
        session_count = 0

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name

            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    metadata = self._extract_metadata(jsonl_file, project_name)
                    if metadata:
                        new_index[metadata.session_id] = metadata
                        session_count += 1
                except Exception as e:
                    logger.error(f"Error indexing {jsonl_file}: {e}", exc_info=True)
                    continue

        with self._lock:
            self._index = new_index
            self._last_scan = datetime.now()

        logger.info(f"Indexed {session_count} sessions from {len(list(self.projects_dir.iterdir()))} projects")
        return session_count

    def _extract_metadata(self, file_path: Path, project_name: str) -> Optional[SessionMetadata]:
        """
        Extract metadata from a session file without loading full content.

        Args:
            file_path: Path to JSONL file
            project_name: Name of the project

        Returns:
            SessionMetadata or None if file should be skipped
        """
        filename = file_path.name

        # Check if this is an agent file
        is_agent = filename.startswith("agent-")

        # Extract session ID from filename (UUID before .jsonl)
        session_id = filename.replace(".jsonl", "")

        try:
            file_size = file_path.stat().st_size

            # If file is empty or too small, skip
            if file_size < 10:
                return None

            first_timestamp = None
            last_timestamp = None
            prompt_count = 0
            first_prompt_preview = ""
            git_branch = ""
            corruption_count = 0

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as e:
                        corruption_count += 1
                        if corruption_count <= 3:
                            logger.warning(f"JSON parse error in {file_path}: {e}")
                        continue

                    # Skip sidechains
                    if data.get("isSidechain"):
                        continue

                    # Skip file-history-snapshot entries
                    if data.get("type") == "file-history-snapshot":
                        continue

                    # Extract timestamp
                    timestamp = data.get("timestamp")
                    if timestamp:
                        if not first_timestamp:
                            first_timestamp = timestamp
                        last_timestamp = timestamp

                    # Extract git branch (from first occurrence)
                    if not git_branch and "gitBranch" in data:
                        git_branch = data["gitBranch"]

                    # Count user prompts and get first preview
                    if data.get("type") == "user":
                        prompt_count += 1

                        # Get first prompt preview
                        if not first_prompt_preview:
                            message = data.get("message", {})
                            content = message.get("content", "")

                            # Handle string content
                            if isinstance(content, str):
                                first_prompt_preview = content
                            # Handle list content (tool results, etc.)
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") != "tool_result":
                                        first_prompt_preview = str(item.get("text", ""))
                                        break
                                    elif isinstance(item, str):
                                        first_prompt_preview = item
                                        break

                            # Truncate preview to 200 chars
                            if first_prompt_preview:
                                first_prompt_preview = first_prompt_preview[:200]
                                if len(first_prompt_preview) == 200:
                                    first_prompt_preview += "..."

            # If we didn't find any valid data, skip
            if not first_timestamp:
                return None

            return SessionMetadata(
                session_id=session_id,
                project=project_name,
                project_path=str(file_path.parent),
                first_timestamp=first_timestamp,
                last_timestamp=last_timestamp or first_timestamp,
                prompt_count=prompt_count,
                first_prompt_preview=first_prompt_preview or "(No preview available)",
                git_branch=git_branch,
                is_agent=is_agent,
                file_path=str(file_path),
                file_size=file_size,
                is_partial=corruption_count > 0,
                corruption_count=corruption_count
            )

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}", exc_info=True)
            return None

    def list_sessions(
        self,
        offset: int = 0,
        limit: int = 50,
        days: Optional[int] = None,
        project: Optional[str] = None,
        search: Optional[str] = None,
        include_agent: bool = False
    ) -> tuple[List[SessionMetadata], int]:
        """
        List sessions with filtering and pagination.

        Args:
            offset: Number of sessions to skip
            limit: Maximum number of sessions to return
            days: Only include sessions from last N days
            project: Filter by project name
            search: Search in first prompt preview
            include_agent: Include agent sessions (default: False)

        Returns:
            Tuple of (sessions, total_count)
        """
        with self._lock:
            sessions = list(self._index.values())

        # Filter by agent files
        if not include_agent:
            sessions = [s for s in sessions if not s.is_agent]

        # Filter by days
        if days is not None:
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            sessions = [
                s for s in sessions
                if datetime.fromisoformat(s.last_timestamp.replace('Z', '+00:00')).timestamp() > cutoff
            ]

        # Filter by project
        if project:
            sessions = [s for s in sessions if s.project == project]

        # Filter by search
        if search:
            search_lower = search.lower()
            sessions = [
                s for s in sessions
                if search_lower in s.first_prompt_preview.lower()
                or search_lower in s.project.lower()
            ]

        # Sort by last timestamp (most recent first)
        sessions.sort(key=lambda s: s.last_timestamp, reverse=True)

        total_count = len(sessions)

        # Apply pagination
        paginated_sessions = sessions[offset:offset + limit]

        return paginated_sessions, total_count

    def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Get metadata for a specific session."""
        with self._lock:
            return self._index.get(session_id)

    def load_full_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Lazy-load full session content on demand.

        Args:
            session_id: Session ID to load

        Returns:
            Dictionary with session metadata and full message list
        """
        metadata = self._index.get(session_id)
        if not metadata:
            logger.warning(f"Session not found: {session_id}")
            return None

        try:
            messages = []
            file_path = Path(metadata.file_path)

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Skip sidechains and snapshots
                    if data.get("isSidechain") or data.get("type") == "file-history-snapshot":
                        continue

                    msg_type = data.get("type")
                    if msg_type not in ["user", "assistant"]:
                        continue

                    uuid = data.get("uuid", "")
                    timestamp = data.get("timestamp", "")

                    # Extract content
                    message_data = data.get("message", {})
                    content = ""
                    tool_use = []
                    thinking = None
                    is_command = False

                    if msg_type == "user":
                        # User message
                        msg_content = message_data.get("content", "")
                        if isinstance(msg_content, str):
                            content = msg_content
                        elif isinstance(msg_content, list):
                            # Handle tool results
                            for item in msg_content:
                                if isinstance(item, dict):
                                    if item.get("type") == "tool_result":
                                        # This is a tool result, skip or summarize
                                        continue
                                    elif "text" in item:
                                        content = item["text"]
                                        break
                                elif isinstance(item, str):
                                    content = item
                                    break

                        # Check if it's a command (single word or starts with /)
                        if content and (not " " in content.strip() or content.strip().startswith("/")):
                            is_command = True

                    elif msg_type == "assistant":
                        # Assistant message
                        msg_content = message_data.get("content", [])

                        # Extract text and tool uses
                        text_parts = []
                        for item in msg_content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                                elif item.get("type") == "tool_use":
                                    tool_name = item.get("name", "")
                                    raw_input = item.get("input", {})

                                    # Truncate tool inputs to prevent context flooding
                                    truncated_input = self._truncate_tool_input(tool_name, raw_input)

                                    tool_use.append({
                                        "id": item.get("id", ""),
                                        "name": tool_name,
                                        "input": truncated_input
                                    })
                                elif item.get("type") == "thinking":
                                    # Check if thinking is encrypted (has signature)
                                    if "signature" in item:
                                        thinking = "[Encrypted thinking]"
                                    else:
                                        thinking = item.get("thinking", "")

                        content = "\n".join(text_parts)

                    messages.append(SessionMessage(
                        uuid=uuid,
                        type=msg_type,
                        timestamp=timestamp,
                        content=content,
                        is_command=is_command,
                        tool_use=tool_use if tool_use else None,
                        thinking=thinking
                    ))

            # Try to get summary from database
            summary = self.get_session_summary(session_id)

            result = {
                "session_id": metadata.session_id,
                "project": metadata.project,
                "project_path": metadata.project_path,
                "first_timestamp": metadata.first_timestamp,
                "last_timestamp": metadata.last_timestamp,
                "prompt_count": metadata.prompt_count,
                "git_branch": metadata.git_branch,
                "is_agent": metadata.is_agent,
                "messages": [asdict(m) for m in messages],
                "has_summary": summary is not None
            }

            # Include summary if available
            if summary:
                result["summary"] = summary

            return result

        except Exception as e:
            logger.error(f"Error loading full session {session_id}: {e}", exc_info=True)
            return None

    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of unique projects with session counts.

        Returns:
            List of projects with metadata
        """
        projects = {}

        with self._lock:
            index_values = list(self._index.values())

        for metadata in index_values:
            project_name = metadata.project

            if project_name not in projects:
                projects[project_name] = {
                    "name": project_name,
                    "session_count": 0,
                    "last_activity": metadata.last_timestamp
                }

            projects[project_name]["session_count"] += 1

            # Update last activity if this session is more recent
            if metadata.last_timestamp > projects[project_name]["last_activity"]:
                projects[project_name]["last_activity"] = metadata.last_timestamp

        # Convert to list and sort by last activity
        project_list = list(projects.values())
        project_list.sort(key=lambda p: p["last_activity"], reverse=True)

        return project_list

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed sessions."""
        with self._lock:
            index_values = list(self._index.values())
            last_scan = self._last_scan

        total_sessions = len(index_values)
        agent_sessions = sum(1 for m in index_values if m.is_agent)
        total_prompts = sum(m.prompt_count for m in index_values)

        return {
            "total_sessions": total_sessions,
            "agent_sessions": agent_sessions,
            "user_sessions": total_sessions - agent_sessions,
            "total_prompts": total_prompts,
            "last_scan": last_scan.isoformat() if last_scan else None,
            "projects_count": len(set(m.project for m in index_values))
        }
