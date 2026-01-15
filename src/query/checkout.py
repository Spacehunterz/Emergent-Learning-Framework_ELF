#!/usr/bin/env python3
"""
Emergent Learning Framework - Checkout Workflow Orchestrator

Implements the 8-step checkout process with learning recording prompts,
plan completion, and session summary capture.

Steps:
1. Display Checkout Banner
2. Detect Active Plans
3. Postmortem Prompt (if active plans exist)
4. Heuristic Discovery Prompt
5. Failure Documentation Prompt
6. Quick Notes Collection
7. Session Statistics
8. Complete Checkout
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import subprocess


class CheckoutOrchestrator:
    """Orchestrates the full checkout workflow."""

    BANNER = """
+------------------------------------+
|    Emergent Learning Framework     |
+------------------------------------+
|                                    |
|      Closing Session               |
|      Recording Learnings...        |
|                                    |
+------------------------------------+
"""

    def __init__(self, interactive: Optional[bool] = None):
        """
        Initialize the checkout orchestrator.

        Args:
            interactive: Force interactive mode on/off. If None, auto-detect.
                         When False, skips input() prompts and outputs JSON hints
                         for Claude to ask questions via AskUserQuestion tool.
        """
        if interactive is None:
            self.interactive = sys.stdin.isatty()
        else:
            self.interactive = interactive

        self.elf_home = self._resolve_elf_home()
        self.db_path = self.elf_home / "memory" / "index.db"
        self.state_file = Path.home() / '.claude' / '.elf_checkout_state'
        self.state = self._load_state()
        self.learnings_recorded = {
            'postmortems': 0,
            'heuristics': 0,
            'failures': 0,
            'notes': False
        }

    def _resolve_elf_home(self) -> Path:
        """Resolve ELF home using centralized elf_paths or fallback."""
        try:
            current_dir = Path(__file__).resolve().parent
            src_dir = current_dir.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))

            from elf_paths import get_base_path
            return get_base_path()
        except ImportError:
            return self._find_elf_home_fallback()

    def _find_elf_home_fallback(self) -> Path:
        """Find the ELF home directory by checking multiple locations."""
        if os.environ.get('ELF_BASE_PATH'):
            return Path(os.environ['ELF_BASE_PATH']).expanduser().resolve()

        global_elf = Path.home() / '.claude' / 'emergent-learning'
        if global_elf.exists():
            return global_elf

        current_file = Path(__file__).resolve()
        for parent in [current_file.parent.parent, current_file.parent.parent.parent]:
            if (parent / 'query' / 'query.py').exists():
                return parent

        return global_elf

    def _load_state(self) -> Dict[str, Any]:
        """Load checkout state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_state(self):
        """Persist checkout state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state['last_checkout'] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)

    def display_banner(self):
        """Step 1: Display the checkout banner."""
        print(self.BANNER)

    def detect_active_plans(self) -> List[Dict[str, Any]]:
        """Step 2: Query database for active plans."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, domain, created_at
                FROM plans
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            plans = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return plans

        except Exception as e:
            print(f"[!] Warning: Could not detect active plans: {e}")
            return []

    def prompt_postmortem(self, plans: List[Dict[str, Any]]):
        """Step 3: Prompt for postmortem completion on active plans."""
        if not plans:
            return

        print(f"\n[*] {len(plans)} active plan(s) found:")
        for plan in plans:
            print(f"   [{plan['id']}] {plan['title']} (domain: {plan.get('domain', '-')})")

        if not self.interactive:
            for plan in plans:
                print(f'[PROMPT_NEEDED] {{"type": "postmortem", "plan_id": {plan["id"]}, "title": "{plan["title"]}"}}')
            return

        for plan in plans:
            try:
                response = input(f"\nComplete postmortem for plan {plan['id']} ({plan['title']})? [Y/n]: ").strip().lower()
                if response not in ['n', 'no']:
                    self._collect_and_record_postmortem(plan['id'], plan['title'])
            except (EOFError, KeyboardInterrupt):
                break

    def _collect_and_record_postmortem(self, plan_id: int, title: str):
        """Collect postmortem data and record via subprocess."""
        if not self.interactive:
            return

        try:
            outcome = input("   Actual outcome: ").strip()
            if not outcome:
                print("   Skipped.")
                return

            divergences = input("   What diverged from plan? ").strip()
            went_well = input("   What went well? ").strip()
            went_wrong = input("   What went wrong? ").strip()
            lessons = input("   Key lessons? ").strip()

            cmd = [
                sys.executable,
                str(self.elf_home / 'scripts' / 'record-postmortem.py'),
                '--plan-id', str(plan_id),
                '--outcome', outcome
            ]
            if divergences:
                cmd.extend(['--divergences', divergences])
            if went_well:
                cmd.extend(['--went-well', went_well])
            if went_wrong:
                cmd.extend(['--went-wrong', went_wrong])
            if lessons:
                cmd.extend(['--lessons', lessons])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"   [OK] Postmortem recorded")
                self.learnings_recorded['postmortems'] += 1
            else:
                print(f"   [!] Failed to record postmortem")

        except Exception as e:
            print(f"   [!] Error: {e}")

    def prompt_heuristic(self):
        """Step 4: Prompt for heuristic discovery."""
        if not self.interactive:
            print('[PROMPT_NEEDED] {"type": "heuristic"}')
            return

        print("\n[*] Heuristic Discovery")
        try:
            response = input("   Did you discover any reusable patterns or rules? [Y/n]: ").strip().lower()
            if response in ['n', 'no']:
                return

            self._collect_and_record_heuristic()

        except (EOFError, KeyboardInterrupt):
            pass

    def _collect_and_record_heuristic(self):
        """Collect heuristic data and record via subprocess."""
        try:
            domain = input("   Domain: ").strip()
            if not domain:
                print("   Skipped.")
                return

            rule = input("   Rule (the heuristic): ").strip()
            if not rule:
                print("   Skipped.")
                return

            explanation = input("   Explanation: ").strip()
            confidence = input("   Confidence (0.0-1.0) [0.7]: ").strip() or "0.7"

            cmd = [
                sys.executable,
                str(self.elf_home / 'scripts' / 'record-heuristic.py'),
                '--domain', domain,
                '--rule', rule,
                '--explanation', explanation or "No explanation provided",
                '--confidence', confidence
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"   [OK] Heuristic recorded")
                self.learnings_recorded['heuristics'] += 1
            else:
                print(f"   [!] Failed to record heuristic")

        except Exception as e:
            print(f"   [!] Error: {e}")

    def prompt_failure(self):
        """Step 5: Prompt for failure documentation."""
        if not self.interactive:
            print('[PROMPT_NEEDED] {"type": "failure"}')
            return

        print("\n[*] Failure Documentation")
        try:
            response = input("   Did anything break or fail unexpectedly? [Y/n]: ").strip().lower()
            if response in ['n', 'no']:
                return

            print("   [+] Guidance: Create a failure analysis file at:")
            print(f"       {self.elf_home / 'failure-analysis'}/YYYY-MM-DD-brief-description.md")
            print("")
            print("   Template:")
            print("   # Failure Analysis: [Brief Description]")
            print("   **Date:** YYYY-MM-DD")
            print("   **Context:** [What you were attempting]")
            print("   ## What Went Wrong")
            print("   [Detailed description]")
            print("   ## Root Cause")
            print("   [Why it failed]")
            print("   ## Lesson Learned")
            print("   [Portable knowledge]")

            self.learnings_recorded['failures'] += 1

        except (EOFError, KeyboardInterrupt):
            pass

    def collect_quick_notes(self):
        """Step 6: Collect quick notes for next session."""
        if not self.interactive:
            print('[PROMPT_NEEDED] {"type": "notes"}')
            return

        print("\n[*] Quick Notes for Next Session")
        try:
            notes = input("   > ").strip()
            if notes:
                self._store_notes(notes)
                self.learnings_recorded['notes'] = True
                print(f"   [OK] Notes saved")

        except (EOFError, KeyboardInterrupt):
            pass

    def _store_notes(self, notes: str):
        """Store session notes."""
        try:
            notes_file = Path.home() / '.claude' / '.checkout_notes'
            timestamp = datetime.now().isoformat()
            with open(notes_file, 'a') as f:
                f.write(f"[{timestamp}] {notes}\n")
        except Exception as e:
            print(f"   [!] Could not save notes: {e}")

    def display_session_stats(self):
        """Step 7: Display session statistics."""
        print("\n[=] Session Summary")
        print(f"   Postmortems recorded: {self.learnings_recorded['postmortems']}")
        print(f"   Heuristics recorded: {self.learnings_recorded['heuristics']}")
        print(f"   Failures documented: {self.learnings_recorded['failures']}")
        print(f"   Notes saved: {'Yes' if self.learnings_recorded['notes'] else 'No'}")

    def complete_checkout(self):
        """Step 8: Complete checkout."""
        print("\n[OK] Checkout complete. Session learnings recorded!")
        print("")

    def run(self):
        """Execute the complete checkout workflow."""
        try:
            # Step 1: Display Banner
            self.display_banner()

            # Step 2: Detect Active Plans
            plans = self.detect_active_plans()

            # Step 3: Postmortem Prompt
            if plans:
                self.prompt_postmortem(plans)

            # Step 4: Heuristic Discovery
            self.prompt_heuristic()

            # Step 5: Failure Documentation
            self.prompt_failure()

            # Step 6: Quick Notes
            self.collect_quick_notes()

            # Step 7: Session Statistics
            self.display_session_stats()

            # Step 8: Complete
            self.complete_checkout()

            # Save state
            self._save_state()

        except KeyboardInterrupt:
            print("\nCheckout cancelled.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Checkout failed: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="ELF Checkout Workflow")
    parser.add_argument('--non-interactive', '-n', action='store_true',
                       help="Run in non-interactive mode (output prompts as JSON hints)")
    args = parser.parse_args()

    try:
        orchestrator = CheckoutOrchestrator(interactive=not args.non_interactive)
        orchestrator.run()
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Checkout failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
