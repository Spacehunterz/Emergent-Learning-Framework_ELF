#!/usr/bin/env python3
"""
Emergent Learning Framework - Proposal Integration Script

Reads approved proposal markdown files and integrates them into the ELF:
- heuristic: Adds to heuristics table in DB + creates markdown file
- failure: Adds to learnings table + creates markdown file
- pattern: Adds as observation to learnings table
- contradiction: Creates CEO inbox item for human review

Usage:
    python integrate-proposal.py <approved_proposal_path>
    python integrate-proposal.py proposals/approved/2025-12-11_heuristic_validate.md
"""

import sqlite3
import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class ProposalIntegrationError(Exception):
    """Raised when proposal integration fails."""
    pass


class ProposalIntegrator:
    """Handles integration of approved proposals into the ELF."""

    def __init__(self, base_path: Optional[str] = None, debug: bool = False):
        """
        Initialize the integrator.

        Args:
            base_path: Base path to emergent-learning directory
            debug: Enable debug output
        """
        self.debug = debug

        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"
        self.heuristics_dir = self.memory_path / "heuristics"
        self.failures_dir = self.memory_path / "failures"
        self.successes_dir = self.memory_path / "successes"
        self.ceo_inbox = self.base_path / "ceo-inbox"
        self.logs_dir = self.base_path / "logs"

        # Ensure directories exist
        self.heuristics_dir.mkdir(parents=True, exist_ok=True)
        self.failures_dir.mkdir(parents=True, exist_ok=True)
        self.successes_dir.mkdir(parents=True, exist_ok=True)
        self.ceo_inbox.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self._log_debug(f"Initialized with base_path: {self.base_path}")

    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _log_to_file(self, level: str, message: str):
        """Log message to daily log file."""
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{level}] [integrate-proposal] {message}\n")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def parse_frontmatter(self, content: str) -> Tuple[Dict[str, str], str]:
        """
        Parse YAML-like frontmatter from markdown content.

        Args:
            content: Full markdown content

        Returns:
            Tuple of (frontmatter dict, body content)
        """
        frontmatter = {}
        body = content

        # Check for frontmatter delimiters
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm_lines = parts[1].strip().split('\n')
                for line in fm_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip().lower()] = value.strip()
                body = parts[2].strip()

        return frontmatter, body

    def extract_title(self, body: str) -> str:
        """Extract title from markdown body (first # heading)."""
        for line in body.split('\n'):
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled Proposal"

    def extract_section(self, body: str, section_name: str) -> str:
        """Extract content of a specific section from markdown."""
        pattern = rf'^##\s+{re.escape(section_name)}\s*$'
        lines = body.split('\n')
        in_section = False
        section_content = []

        for line in lines:
            if re.match(pattern, line, re.IGNORECASE):
                in_section = True
                continue
            elif in_section and line.startswith('## '):
                break
            elif in_section:
                section_content.append(line)

        return '\n'.join(section_content).strip()

    def sanitize_for_sql(self, value: str) -> str:
        """Escape single quotes for SQL safety."""
        if value is None:
            return ""
        return value.replace("'", "''")

    def sanitize_filename(self, name: str, max_length: int = 100) -> str:
        """Create safe filename from string."""
        # Convert to lowercase and replace spaces with hyphens
        safe = name.lower().replace(' ', '-')
        # Remove non-alphanumeric chars except hyphens
        safe = re.sub(r'[^a-z0-9-]', '', safe)
        # Collapse multiple hyphens
        safe = re.sub(r'-+', '-', safe)
        # Trim leading/trailing hyphens
        safe = safe.strip('-')
        return safe[:max_length]

    def integrate_heuristic(self, frontmatter: Dict, body: str) -> int:
        """
        Integrate a heuristic proposal into the ELF.

        Returns:
            Database ID of inserted heuristic
        """
        title = self.extract_title(body)
        summary = self.extract_section(body, 'Summary') or self.extract_section(body, 'Details')
        domain = frontmatter.get('domain', 'general')
        confidence = float(frontmatter.get('confidence', '0.7'))
        source_type = frontmatter.get('source', 'observation')

        self._log_debug(f"Integrating heuristic: {title} (domain: {domain})")

        # Insert into database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO heuristics (domain, rule, explanation, source_type, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (domain, title, summary, source_type, confidence))
            heuristic_id = cursor.lastrowid
            conn.commit()

            # Create/update domain markdown file
            domain_safe = self.sanitize_filename(domain)
            domain_file = self.heuristics_dir / f"{domain_safe}.md"

            if not domain_file.exists():
                domain_file.write_text(
                    f"# Heuristics: {domain}\n\n"
                    f"Generated from failures, successes, and observations in the **{domain}** domain.\n\n"
                    "---\n\n",
                    encoding='utf-8'
                )

            # Append heuristic
            with open(domain_file, 'a', encoding='utf-8') as f:
                f.write(f"## H-{heuristic_id}: {title}\n\n")
                f.write(f"**Confidence**: {confidence}\n")
                f.write(f"**Source**: {source_type}\n")
                f.write(f"**Created**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                f.write(f"{summary}\n\n")
                f.write("---\n\n")

            self._log_to_file("INFO", f"Integrated heuristic ID={heuristic_id}: {title}")
            return heuristic_id

        finally:
            conn.close()

    def integrate_failure(self, frontmatter: Dict, body: str) -> int:
        """
        Integrate a failure proposal into the ELF.

        Returns:
            Database ID of inserted learning
        """
        title = self.extract_title(body)
        summary = self.extract_section(body, 'Summary')
        details = self.extract_section(body, 'Details')
        domain = frontmatter.get('domain', 'general')
        severity = int(frontmatter.get('severity', '3'))
        tags = frontmatter.get('tags', '')

        self._log_debug(f"Integrating failure: {title} (domain: {domain})")

        # Generate filename
        date_prefix = datetime.now().strftime('%Y%m%d')
        filename_slug = self.sanitize_filename(title)
        filename = f"{date_prefix}_{filename_slug}.md"
        filepath = self.failures_dir / filename
        relative_path = f"memory/failures/{filename}"

        # Create markdown file
        filepath.write_text(
            f"# {title}\n\n"
            f"**Domain**: {domain}\n"
            f"**Severity**: {severity}\n"
            f"**Tags**: {tags}\n"
            f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"## Summary\n\n{summary}\n\n"
            f"## Details\n\n{details}\n\n"
            f"## Root Cause\n\n[Extracted from proposal]\n\n"
            f"## Prevention\n\n[See proposal recommendations]\n",
            encoding='utf-8'
        )

        # Insert into database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
                VALUES ('failure', ?, ?, ?, ?, ?, ?)
            """, (relative_path, title, summary[:500] if summary else '', tags, domain, severity))
            learning_id = cursor.lastrowid
            conn.commit()

            self._log_to_file("INFO", f"Integrated failure ID={learning_id}: {title}")
            return learning_id

        finally:
            conn.close()

    def integrate_pattern(self, frontmatter: Dict, body: str) -> int:
        """
        Integrate a pattern proposal as an observation.

        Returns:
            Database ID of inserted learning
        """
        title = self.extract_title(body)
        summary = self.extract_section(body, 'Summary')
        details = self.extract_section(body, 'Details')
        domain = frontmatter.get('domain', 'general')
        tags = frontmatter.get('tags', 'pattern')

        self._log_debug(f"Integrating pattern: {title} (domain: {domain})")

        # Generate filename
        date_prefix = datetime.now().strftime('%Y%m%d')
        filename_slug = self.sanitize_filename(title)
        filename = f"{date_prefix}_{filename_slug}.md"
        filepath = self.successes_dir / filename  # Patterns go to successes as observations
        relative_path = f"memory/successes/{filename}"

        # Create markdown file
        filepath.write_text(
            f"# Pattern: {title}\n\n"
            f"**Domain**: {domain}\n"
            f"**Tags**: {tags}\n"
            f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"## Summary\n\n{summary}\n\n"
            f"## Details\n\n{details}\n",
            encoding='utf-8'
        )

        # Insert into database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
                VALUES ('observation', ?, ?, ?, ?, ?, 1)
            """, (relative_path, title, summary[:500] if summary else '', tags, domain))
            learning_id = cursor.lastrowid
            conn.commit()

            self._log_to_file("INFO", f"Integrated pattern ID={learning_id}: {title}")
            return learning_id

        finally:
            conn.close()

    def integrate_contradiction(self, frontmatter: Dict, body: str) -> str:
        """
        Create a CEO inbox item for contradiction review.

        Returns:
            Path to created CEO inbox file
        """
        title = self.extract_title(body)
        summary = self.extract_section(body, 'Summary')
        details = self.extract_section(body, 'Details')
        evidence = self.extract_section(body, 'Evidence')
        recommendation = self.extract_section(body, 'Recommendation')
        domain = frontmatter.get('domain', 'general')

        self._log_debug(f"Creating CEO inbox item for contradiction: {title}")

        # Generate filename
        date_prefix = datetime.now().strftime('%Y-%m-%d')
        filename_slug = self.sanitize_filename(title)
        filename = f"{date_prefix}-contradiction-{filename_slug}.md"
        filepath = self.ceo_inbox / filename

        # Create CEO inbox file
        filepath.write_text(
            f"# CEO Review Required\n\n"
            f"**Priority:** high\n"
            f"**Created:** {datetime.now().strftime('%Y-%m-%d')}\n"
            f"**Status:** PENDING\n"
            f"**Type:** Contradiction Resolution\n\n"
            f"## Situation\n\n"
            f"A contradiction has been detected in the knowledge base that requires human judgment.\n\n"
            f"**Title:** {title}\n"
            f"**Domain:** {domain}\n\n"
            f"## Context\n\n{summary}\n\n"
            f"## Details\n\n{details}\n\n"
            f"## Evidence\n\n{evidence}\n\n"
            f"## Options\n\n"
            f"1. **Keep existing knowledge:** Reject the contradicting evidence\n"
            f"   - Pros: Stability, proven track record\n"
            f"   - Cons: May ignore valid new information\n\n"
            f"2. **Update with new evidence:** Modify existing heuristics/learnings\n"
            f"   - Pros: Adapts to new reality\n"
            f"   - Cons: May break working patterns\n\n"
            f"3. **Create conditional rule:** Both can be true in different contexts\n"
            f"   - Pros: Captures nuance\n"
            f"   - Cons: Adds complexity\n\n"
            f"## Agent Recommendations\n\n"
            f"- **Researcher:** Review the evidence thoroughly\n"
            f"- **Architect:** Consider system-wide implications\n"
            f"- **Skeptic:** Challenge both positions\n\n"
            f"## Recommendation\n\n{recommendation}\n\n"
            f"---\n\n"
            f"## CEO Decision\n\n"
            f"**Decision:** [To be filled by human]\n"
            f"**Reasoning:** [To be filled by human]\n"
            f"**Date:** YYYY-MM-DD\n",
            encoding='utf-8'
        )

        self._log_to_file("INFO", f"Created CEO inbox for contradiction: {filepath}")
        return str(filepath)

    def integrate(self, proposal_path: str) -> Dict[str, Any]:
        """
        Main integration entry point.

        Args:
            proposal_path: Path to approved proposal file

        Returns:
            Dictionary with integration results
        """
        proposal_path = Path(proposal_path)

        if not proposal_path.exists():
            raise ProposalIntegrationError(f"Proposal file not found: {proposal_path}")

        self._log_debug(f"Reading proposal: {proposal_path}")

        # Read proposal content
        content = proposal_path.read_text(encoding='utf-8')
        frontmatter, body = self.parse_frontmatter(content)

        # Determine proposal type
        proposal_type = frontmatter.get('type', 'pattern').lower()

        self._log_debug(f"Proposal type: {proposal_type}")
        self._log_to_file("INFO", f"Starting integration of {proposal_type}: {proposal_path.name}")

        result = {
            'proposal_path': str(proposal_path),
            'type': proposal_type,
            'title': self.extract_title(body),
            'success': False,
            'result_id': None,
            'result_path': None,
            'error': None
        }

        try:
            if proposal_type == 'heuristic':
                result['result_id'] = self.integrate_heuristic(frontmatter, body)
                result['success'] = True

            elif proposal_type == 'failure':
                result['result_id'] = self.integrate_failure(frontmatter, body)
                result['success'] = True

            elif proposal_type == 'pattern':
                result['result_id'] = self.integrate_pattern(frontmatter, body)
                result['success'] = True

            elif proposal_type == 'contradiction':
                result['result_path'] = self.integrate_contradiction(frontmatter, body)
                result['success'] = True

            else:
                raise ProposalIntegrationError(f"Unknown proposal type: {proposal_type}")

        except Exception as e:
            result['error'] = str(e)
            self._log_to_file("ERROR", f"Integration failed: {e}")
            raise

        return result


def main():
    """Command-line interface for proposal integration."""
    parser = argparse.ArgumentParser(
        description="Integrate approved proposals into the Emergent Learning Framework"
    )
    parser.add_argument('proposal_path', help='Path to approved proposal file')
    parser.add_argument('--base-path', help='Base path to emergent-learning directory')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    try:
        integrator = ProposalIntegrator(base_path=args.base_path, debug=args.debug)
        result = integrator.integrate(args.proposal_path)

        if result['success']:
            print(f"Integration successful!")
            print(f"  Type: {result['type']}")
            print(f"  Title: {result['title']}")
            if result['result_id']:
                print(f"  Database ID: {result['result_id']}")
            if result['result_path']:
                print(f"  Created: {result['result_path']}")
            return 0
        else:
            print(f"Integration failed: {result['error']}", file=sys.stderr)
            return 1

    except ProposalIntegrationError as e:
        print(f"Integration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
