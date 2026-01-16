#!/usr/bin/env python3
"""
Emergent Learning Framework - Automated Checkout

Fully automated session closing - no prompts, just capture and display.
Analyzes session activity, extracts any auto-learned patterns, and shows summary.
"""

import sys
import io
import sqlite3
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class CheckoutOrchestrator:
    """Automated checkout - captures session data without prompting."""

    BANNER = """
┌────────────────────────────────────┐
│    Emergent Learning Framework     │
├────────────────────────────────────┤
│                                    │
│      Session Complete              │
│      Auto-capturing learnings...   │
│                                    │
└────────────────────────────────────┘
"""

    def __init__(self):
        self.elf_home = self._resolve_elf_home()
        self.db_path = self.elf_home / "memory" / "index.db"
        self.session_data = {
            'domains': [],
            'tool_counts': {},
            'files_touched': [],
            'heuristics_captured': 0,
            'commits_made': 0
        }

    def _resolve_elf_home(self) -> Path:
        try:
            current_dir = Path(__file__).resolve().parent
            src_dir = current_dir.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            from elf_paths import get_base_path
            return get_base_path()
        except ImportError:
            return Path.home() / '.claude' / 'emergent-learning'

    def display_banner(self):
        print(self.BANNER)

    def analyze_session(self):
        """Auto-detect session activity from git and file system."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~5', 'HEAD'],
                capture_output=True, text=True, timeout=10, cwd=str(self.elf_home)
            )
            if result.returncode == 0:
                files = [f for f in result.stdout.strip().split('\n') if f]
                self.session_data['files_touched'] = files[:20]

                domains = set()
                for f in files:
                    if 'dashboard' in f:
                        domains.add('dashboard')
                    if 'query' in f:
                        domains.add('infrastructure')
                    if '.tsx' in f or '.jsx' in f:
                        domains.add('frontend')
                    if '.py' in f:
                        domains.add('backend')
                self.session_data['domains'] = list(domains)

            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD~5..HEAD'],
                capture_output=True, text=True, timeout=10, cwd=str(self.elf_home)
            )
            if result.returncode == 0:
                self.session_data['commits_made'] = int(result.stdout.strip() or 0)

        except Exception:
            pass

    def count_recent_heuristics(self) -> int:
        """Count heuristics recorded in the last 4 hours."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM heuristics
                    WHERE created_at > datetime('now', '-4 hours')
                """)
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def display_summary(self):
        """Display automated session summary."""
        print("[*] Session Summary (auto-detected)")

        if self.session_data['domains']:
            print(f"   Domains: {', '.join(self.session_data['domains'])}")

        if self.session_data['commits_made']:
            print(f"   Commits: {self.session_data['commits_made']}")

        files = self.session_data['files_touched']
        if files:
            print(f"   Files modified: {len(files)}")
            for f in files[:5]:
                print(f"     - {f}")
            if len(files) > 5:
                print(f"     ... and {len(files) - 5} more")

        heuristics = self.count_recent_heuristics()
        if heuristics:
            print(f"   Heuristics recorded: {heuristics}")

        print("")

    def run(self):
        """Execute automated checkout."""
        self.display_banner()
        self.analyze_session()
        self.display_summary()
        print("[OK] Checkout complete.")


def main():
    try:
        orchestrator = CheckoutOrchestrator()
        orchestrator.run()
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Checkout failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
