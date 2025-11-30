#!/usr/bin/env python3
"""
Emergent Learning Framework - Query System
A tiered retrieval system for knowledge retrieval across the learning framework.

Tier 1: Golden rules (always loaded, ~500 tokens)
Tier 2: Query-matched content by domain/tags (~2-5k tokens)
Tier 3: On-demand deep history
"""

import sqlite3
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json


class QuerySystem:
    """Manages knowledge retrieval from the Emergent Learning Framework."""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the query system.

        Args:
            base_path: Base path to the emergent-learning directory.
                      Defaults to ~/.claude/emergent-learning
        """
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"
        self.golden_rules_path = self.memory_path / "golden-rules.md"

        # Ensure directories exist
        self.memory_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize the database with required schema if it does not exist."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create learnings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                filepath TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                tags TEXT,
                domain TEXT,
                severity INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create heuristics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heuristics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                rule TEXT NOT NULL,
                explanation TEXT,
                source_type TEXT,
                source_id INTEGER,
                confidence REAL DEFAULT 0.5,
                times_validated INTEGER DEFAULT 0,
                times_violated INTEGER DEFAULT 0,
                is_golden BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hypothesis TEXT,
                status TEXT DEFAULT 'active',
                cycles_run INTEGER DEFAULT 0,
                folder_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create ceo_reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ceo_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                context TEXT,
                recommendation TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP
            )
        """)

        # Create indexes for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learnings_domain
            ON learnings(domain)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learnings_type
            ON learnings(type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_heuristics_domain
            ON heuristics(domain)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_heuristics_golden
            ON heuristics(is_golden)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_status
            ON experiments(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ceo_reviews_status
            ON ceo_reviews(status)
        """)

        conn.commit()
        conn.close()

    def get_golden_rules(self) -> str:
        """
        Read and return golden rules from memory/golden-rules.md.

        Returns:
            Content of golden rules file, or empty string if file does not exist.
        """
        if not self.golden_rules_path.exists():
            return "# Golden Rules\n\nNo golden rules have been established yet."

        try:
            with open(self.golden_rules_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"# Error Reading Golden Rules\n\nError: {str(e)}"

    def query_by_domain(self, domain: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get heuristics and learnings for a specific domain.

        Args:
            domain: The domain to query (e.g., 'coordination', 'debugging')
            limit: Maximum number of results to return

        Returns:
            Dictionary containing heuristics and learnings for the domain
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get heuristics for domain
        cursor.execute("""
            SELECT * FROM heuristics
            WHERE domain = ?
            ORDER BY confidence DESC, times_validated DESC
            LIMIT ?
        """, (domain, limit))
        heuristics = [dict(row) for row in cursor.fetchall()]

        # Get learnings for domain
        cursor.execute("""
            SELECT * FROM learnings
            WHERE domain = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (domain, limit))
        learnings = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'domain': domain,
            'heuristics': heuristics,
            'learnings': learnings,
            'count': {
                'heuristics': len(heuristics),
                'learnings': len(learnings)
            }
        }

    def query_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get learnings matching specified tags.

        Args:
            tags: List of tags to search for
            limit: Maximum number of results to return

        Returns:
            List of learnings matching any of the tags
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query for tag matching (tags stored as comma-separated string)
        tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
        query = f"""
            SELECT * FROM learnings
            WHERE {tag_conditions}
            ORDER BY created_at DESC
            LIMIT ?
        """

        # Prepare parameters with wildcards for LIKE queries
        params = [f"%{tag}%" for tag in tags] + [limit]

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return results

    def query_recent(self, type_filter: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent learnings, optionally filtered by type.

        Args:
            type_filter: Optional type filter (e.g., 'incident', 'success')
            limit: Maximum number of results to return

        Returns:
            List of recent learnings
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if type_filter:
            cursor.execute("""
                SELECT * FROM learnings
                WHERE type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (type_filter, limit))
        else:
            cursor.execute("""
                SELECT * FROM learnings
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        results = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return results

    def get_active_experiments(self) -> List[Dict[str, Any]]:
        """
        List all active experiments.

        Returns:
            List of active experiments
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM experiments
            WHERE status = 'active'
            ORDER BY updated_at DESC
        """)

        results = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return results

    def get_pending_ceo_reviews(self) -> List[Dict[str, Any]]:
        """
        List pending CEO decisions.

        Returns:
            List of pending CEO reviews
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ceo_reviews
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """)

        results = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return results

    def build_context(
        self,
        task: str,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_tokens: int = 5000
    ) -> str:
        """
        Build a context string for agents with tiered retrieval.

        Tier 1: Golden rules (always included)
        Tier 2: Domain-specific heuristics and tag-matched learnings
        Tier 3: Recent context if tokens remain

        Args:
            task: Description of the task for context
            domain: Optional domain to focus on
            tags: Optional tags to match
            max_tokens: Maximum tokens to use (approximate, based on ~4 chars/token)

        Returns:
            Formatted context string for agent consumption
        """
        context_parts = []
        approx_tokens = 0
        max_chars = max_tokens * 4  # Rough approximation

        # Tier 1: Golden Rules (always loaded)
        golden_rules = self.get_golden_rules()
        context_parts.append("# TIER 1: Golden Rules\n")
        context_parts.append(golden_rules)
        context_parts.append("\n")
        approx_tokens += len(golden_rules) // 4

        # Tier 2: Query-matched content
        context_parts.append("# TIER 2: Relevant Knowledge\n\n")

        if domain:
            context_parts.append(f"## Domain: {domain}\n\n")
            domain_data = self.query_by_domain(domain, limit=5)

            if domain_data['heuristics']:
                context_parts.append("### Heuristics:\n")
                for h in domain_data['heuristics']:
                    entry = f"- **{h['rule']}** (confidence: {h['confidence']:.2f}, validated: {h['times_validated']}x)\n"
                    entry += f"  {h['explanation']}\n\n"
                    context_parts.append(entry)
                    approx_tokens += len(entry) // 4

            if domain_data['learnings']:
                context_parts.append("### Recent Learnings:\n")
                for l in domain_data['learnings']:
                    entry = f"- **{l['title']}** ({l['type']})\n"
                    if l['summary']:
                        entry += f"  {l['summary']}\n"
                    entry += f"  Tags: {l['tags']}\n\n"
                    context_parts.append(entry)
                    approx_tokens += len(entry) // 4

        if tags:
            context_parts.append(f"## Tag Matches: {', '.join(tags)}\n\n")
            tag_results = self.query_by_tags(tags, limit=5)

            for l in tag_results:
                entry = f"- **{l['title']}** ({l['type']}, domain: {l['domain']})\n"
                if l['summary']:
                    entry += f"  {l['summary']}\n"
                entry += f"  Tags: {l['tags']}\n\n"
                context_parts.append(entry)
                approx_tokens += len(entry) // 4

        # Tier 3: Recent context if tokens remain
        remaining_tokens = max_tokens - approx_tokens
        if remaining_tokens > 500:
            context_parts.append("# TIER 3: Recent Context\n\n")
            recent = self.query_recent(limit=3)

            for l in recent:
                entry = f"- **{l['title']}** ({l['type']}, {l['created_at']})\n"
                if l['summary']:
                    entry += f"  {l['summary']}\n\n"
                context_parts.append(entry)
                approx_tokens += len(entry) // 4

                if approx_tokens >= max_tokens:
                    break

        # Add active experiments
        experiments = self.get_active_experiments()
        if experiments:
            context_parts.append("\n# Active Experiments\n\n")
            for exp in experiments:
                entry = f"- **{exp['name']}** ({exp['cycles_run']} cycles)\n"
                if exp['hypothesis']:
                    entry += f"  Hypothesis: {exp['hypothesis']}\n\n"
                context_parts.append(entry)

        # Add pending CEO reviews
        ceo_reviews = self.get_pending_ceo_reviews()
        if ceo_reviews:
            context_parts.append("\n# Pending CEO Reviews\n\n")
            for review in ceo_reviews:
                entry = f"- **{review['title']}**\n"
                if review['context']:
                    entry += f"  Context: {review['context']}\n"
                if review['recommendation']:
                    entry += f"  Recommendation: {review['recommendation']}\n\n"
                context_parts.append(entry)

        # Task context
        context_parts.insert(0, f"# Task Context\n\n{task}\n\n---\n\n")

        return "".join(context_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.

        Returns:
            Dictionary containing various statistics
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        stats = {}

        # Count learnings by type
        cursor.execute("SELECT type, COUNT(*) as count FROM learnings GROUP BY type")
        stats['learnings_by_type'] = dict(cursor.fetchall())

        # Count learnings by domain
        cursor.execute("SELECT domain, COUNT(*) as count FROM learnings GROUP BY domain")
        stats['learnings_by_domain'] = dict(cursor.fetchall())

        # Count heuristics by domain
        cursor.execute("SELECT domain, COUNT(*) as count FROM heuristics GROUP BY domain")
        stats['heuristics_by_domain'] = dict(cursor.fetchall())

        # Count golden heuristics
        cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
        stats['golden_heuristics'] = cursor.fetchone()[0]

        # Count experiments by status
        cursor.execute("SELECT status, COUNT(*) as count FROM experiments GROUP BY status")
        stats['experiments_by_status'] = dict(cursor.fetchall())

        # Count CEO reviews by status
        cursor.execute("SELECT status, COUNT(*) as count FROM ceo_reviews GROUP BY status")
        stats['ceo_reviews_by_status'] = dict(cursor.fetchall())

        # Total counts
        cursor.execute("SELECT COUNT(*) FROM learnings")
        stats['total_learnings'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM heuristics")
        stats['total_heuristics'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM experiments")
        stats['total_experiments'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ceo_reviews")
        stats['total_ceo_reviews'] = cursor.fetchone()[0]

        conn.close()

        return stats


def format_output(data: Any, format_type: str = 'text') -> str:
    """
    Format query results for display.

    Args:
        data: Data to format
        format_type: Output format ('text' or 'json')

    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)

    # Text formatting
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}:")
                lines.append(format_output(value, format_type))
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    elif isinstance(data, list):
        lines = []
        for i, item in enumerate(data, 1):
            lines.append(f"\n--- Item {i} ---")
            lines.append(format_output(item, format_type))
        return "\n".join(lines)

    else:
        return str(data)


def main():
    """Command-line interface for the query system."""
    parser = argparse.ArgumentParser(
        description="Emergent Learning Framework - Query System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query.py --context --domain coordination
  python query.py --domain debugging --limit 5
  python query.py --tags error,fix --limit 10
  python query.py --recent 10
  python query.py --experiments
  python query.py --ceo-reviews
  python query.py --stats
        """
    )

    parser.add_argument('--base-path', type=str, help='Base path to emergent-learning directory')
    parser.add_argument('--context', action='store_true', help='Build full context for agents')
    parser.add_argument('--domain', type=str, help='Query by domain')
    parser.add_argument('--tags', type=str, help='Query by tags (comma-separated)')
    parser.add_argument('--recent', type=int, metavar='N', help='Get N recent learnings')
    parser.add_argument('--type', type=str, help='Filter recent learnings by type')
    parser.add_argument('--experiments', action='store_true', help='List active experiments')
    parser.add_argument('--ceo-reviews', action='store_true', help='List pending CEO reviews')
    parser.add_argument('--golden-rules', action='store_true', help='Display golden rules')
    parser.add_argument('--stats', action='store_true', help='Display knowledge base statistics')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10)')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--max-tokens', type=int, default=5000, help='Max tokens for context building (default: 5000)')

    args = parser.parse_args()

    # Initialize query system
    query_system = QuerySystem(base_path=args.base_path)

    # Execute query based on arguments
    result = None

    if args.context:
        # Build full context
        task = "Agent task context generation"
        domain = args.domain
        tags = args.tags.split(',') if args.tags else None
        result = query_system.build_context(task, domain, tags, args.max_tokens)
        print(result)
        return

    elif args.golden_rules:
        result = query_system.get_golden_rules()
        print(result)
        return

    elif args.domain:
        result = query_system.query_by_domain(args.domain, args.limit)

    elif args.tags:
        tags = [t.strip() for t in args.tags.split(',')]
        result = query_system.query_by_tags(tags, args.limit)

    elif args.recent is not None:
        result = query_system.query_recent(args.type, args.recent)

    elif args.experiments:
        result = query_system.get_active_experiments()

    elif args.ceo_reviews:
        result = query_system.get_pending_ceo_reviews()

    elif args.stats:
        result = query_system.get_statistics()

    else:
        parser.print_help()
        return

    # Output result
    if result is not None:
        print(format_output(result, args.format))


if __name__ == '__main__':
    main()
