"""
Project context mixin for merging global + project learnings.

DEPRECATION NOTICE (2025-12-20):
This module implements the dual-database approach which is being deprecated.
The new approach uses a single database with a 'project_path' column for
location awareness. See query.py QuerySystem.__init__ current_location parameter.

This module provides:
- Project-aware context building (DEPRECATED)
- Merged heuristic queries (project + global) (DEPRECATED)
- Project-specific learning queries (DEPRECATED)
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from query.project import detect_project_context, ProjectContext, format_project_status
    from query.exceptions import DatabaseError
except ImportError:
    from project import detect_project_context, ProjectContext, format_project_status
    from exceptions import DatabaseError


class ProjectContextMixin:
    """Mixin for project-aware context building."""

    _project_context: Optional[ProjectContext] = None

    def _init_project_context(self):
        """Initialize project context detection."""
        if self._project_context is None:
            self._project_context = detect_project_context()
            self._log_debug(f"Project context: mode={self._project_context.mode}, "
                          f"name={self._project_context.project_name}")

    def get_project_context(self) -> ProjectContext:
        """Get the current project context."""
        self._init_project_context()
        return self._project_context

    def has_project(self) -> bool:
        """Check if we're in an ELF-initialized project."""
        self._init_project_context()
        return self._project_context.has_project_context()

    def get_project_status(self) -> str:
        """Get formatted project status string."""
        self._init_project_context()
        return format_project_status(self._project_context)

    def _get_project_db_connection(self):
        """Get a connection to the project database if available."""
        self._init_project_context()

        if not self._project_context.has_project_context():
            return None

        db_path = self._project_context.project_db_path
        if not db_path or not db_path.exists():
            return None

        try:
            return sqlite3.connect(str(db_path))
        except Exception as e:
            self._log_debug(f"Failed to connect to project DB: {e}")
            return None

    def get_project_heuristics(
        self,
        domain: Optional[str] = None,
        limit: int = 20,
        min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get heuristics from the project database.

        Args:
            domain: Optional domain filter
            limit: Maximum results
            min_confidence: Minimum confidence threshold

        Returns:
            List of heuristic dictionaries
        """
        conn = self._get_project_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()

            query = '''
                SELECT id, rule, explanation, domain, confidence, source, tags,
                       created_at, validation_count
                FROM heuristics
                WHERE confidence >= ?
            '''
            params = [min_confidence]

            if domain:
                query += ' AND (domain = ? OR domain IS NULL)'
                params.append(domain)

            query += ' ORDER BY confidence DESC, validation_count DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'rule': row[1],
                    'explanation': row[2],
                    'domain': row[3],
                    'confidence': row[4],
                    'source': row[5],
                    'tags': row[6],
                    'created_at': row[7],
                    'validation_count': row[8],
                    '_source': 'project'
                })

            return results

        except Exception as e:
            self._log_debug(f"Error querying project heuristics: {e}")
            return []
        finally:
            conn.close()

    def get_project_learnings(
        self,
        domain: Optional[str] = None,
        learning_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get learnings from the project database.

        Args:
            domain: Optional domain filter
            learning_type: Optional type filter (success, failure, observation)
            limit: Maximum results

        Returns:
            List of learning dictionaries
        """
        conn = self._get_project_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()

            query = 'SELECT id, type, summary, details, domain, tags, created_at FROM learnings WHERE 1=1'
            params = []

            if domain:
                query += ' AND (domain = ? OR domain IS NULL)'
                params.append(domain)

            if learning_type:
                query += ' AND type = ?'
                params.append(learning_type)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'type': row[1],
                    'summary': row[2],
                    'details': row[3],
                    'domain': row[4],
                    'tags': row[5],
                    'created_at': row[6],
                    '_source': 'project'
                })

            return results

        except Exception as e:
            self._log_debug(f"Error querying project learnings: {e}")
            return []
        finally:
            conn.close()

    def get_project_decisions(
        self,
        domain: Optional[str] = None,
        status: str = 'accepted',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get decisions (ADRs) from the project database."""
        conn = self._get_project_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()

            query = '''
                SELECT id, title, decision, rationale, alternatives, status, domain, created_at
                FROM decisions
                WHERE status = ?
            '''
            params = [status]

            if domain:
                query += ' AND (domain = ? OR domain IS NULL)'
                params.append(domain)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'title': row[1],
                    'decision': row[2],
                    'rationale': row[3],
                    'alternatives': row[4],
                    'status': row[5],
                    'domain': row[6],
                    'created_at': row[7],
                    '_source': 'project'
                })

            return results

        except Exception as e:
            self._log_debug(f"Error querying project decisions: {e}")
            return []
        finally:
            conn.close()

    def format_project_context_section(self) -> str:
        """
        Format the project context section for inclusion in build_context.

        Returns:
            Formatted string with project info and context.md content
        """
        self._init_project_context()

        if not self._project_context.has_project_context():
            return ""

        lines = []
        lines.append("# TIER 0: Project Context\n")
        lines.append(f"**Project:** {self._project_context.project_name}")
        lines.append(f"**Root:** {self._project_context.elf_root}")

        if self._project_context.domains:
            lines.append(f"**Domains:** {', '.join(self._project_context.domains)}")

        if self._project_context.inheritance_chain:
            parents = [p.name for p in self._project_context.inheritance_chain]
            lines.append(f"**Inherits from:** {' → '.join(parents)}")

        lines.append("")

        # Load context.md content
        context_content = self._project_context.get_context_md_content()
        if context_content:
            lines.append("## Project Description\n")
            lines.append(context_content)
            lines.append("")

        lines.append("---\n")

        return '\n'.join(lines)

    def format_project_heuristics_section(
        self,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Format project-specific heuristics for inclusion in context.

        Args:
            domain: Optional domain filter
            limit: Maximum heuristics to include

        Returns:
            Formatted string with project heuristics
        """
        heuristics = self.get_project_heuristics(domain=domain, limit=limit)

        if not heuristics:
            return ""

        lines = []
        lines.append("## Project-Specific Heuristics\n")

        for h in heuristics:
            lines.append(f"- **{h['rule']}** (confidence: {h['confidence']:.2f})")
            if h.get('explanation'):
                expl = h['explanation'][:100] + '...' if len(h['explanation']) > 100 else h['explanation']
                lines.append(f"  {expl}")
            lines.append("")

        return '\n'.join(lines)

    def format_project_learnings_section(
        self,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Format project-specific learnings for inclusion in context.

        Args:
            domain: Optional domain filter
            limit: Maximum learnings to include

        Returns:
            Formatted string with project learnings
        """
        learnings = self.get_project_learnings(domain=domain, limit=limit)

        if not learnings:
            return ""

        lines = []
        lines.append("## Project-Specific Learnings\n")

        for l in learnings:
            lines.append(f"- **{l['summary']}** ({l['type']})")
            if l.get('details'):
                details = l['details'][:100] + '...' if len(l['details']) > 100 else l['details']
                lines.append(f"  {details}")
            lines.append("")

        return '\n'.join(lines)


def record_project_heuristic(
    project_db_path: Path,
    rule: str,
    explanation: str,
    domain: Optional[str] = None,
    confidence: float = 0.7,
    source: str = 'observation',
    tags: Optional[str] = None
) -> int:
    """
    Record a heuristic to the project database.

    Args:
        project_db_path: Path to project learnings.db
        rule: The heuristic rule
        explanation: Why this rule matters
        domain: Optional domain
        confidence: Confidence level (0.0-1.0)
        source: Source of heuristic
        tags: Comma-separated tags

    Returns:
        ID of inserted heuristic
    """
    conn = sqlite3.connect(str(project_db_path))
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO heuristics (rule, explanation, domain, confidence, source, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (rule, explanation, domain, confidence, source, tags))

    heuristic_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return heuristic_id


def record_project_learning(
    project_db_path: Path,
    learning_type: str,
    summary: str,
    details: Optional[str] = None,
    domain: Optional[str] = None,
    tags: Optional[str] = None
) -> int:
    """
    Record a learning to the project database.

    Args:
        project_db_path: Path to project learnings.db
        learning_type: Type of learning (success, failure, observation)
        summary: Brief summary
        details: Full details
        domain: Optional domain
        tags: Comma-separated tags

    Returns:
        ID of inserted learning
    """
    conn = sqlite3.connect(str(project_db_path))
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO learnings (type, summary, details, domain, tags)
        VALUES (?, ?, ?, ?, ?)
    ''', (learning_type, summary, details, domain, tags))

    learning_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return learning_id
