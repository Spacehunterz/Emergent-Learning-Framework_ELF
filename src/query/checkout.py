#!/usr/bin/env python3
"""
Emergent Learning Framework - Checkout Workflow Orchestrator

Implements the 11-step checkout process with automated session analysis,
learning recording prompts, plan completion, and session summary capture.

Steps:
0. Analyze Session Data (auto)
1. Display Checkout Banner
2. Detect Active Plans
3. Postmortem Prompt (if active plans exist)
4. Heuristic Validation (review relevant heuristics)
5. Auto-Detected Patterns (suggest potential heuristics)
6. Heuristic Discovery Prompt (manual)
7. Failure Documentation Prompt
8. Quick Notes Collection
9. Session Statistics
10. Complete Checkout
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import Counter
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
            'heuristics_validated': 0,
            'heuristics_violated': 0,
            'failures': 0,
            'notes': False
        }
        self.session_analysis = {
            'domains': [],
            'tool_counts': {},
            'patterns': [],
            'suggested_heuristics': []
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

    def analyze_session(self) -> Dict[str, Any]:
        """Step 0: Analyze current session data for patterns and metrics."""
        analysis = {
            'domains': [],
            'tool_counts': {},
            'patterns': [],
            'suggested_heuristics': [],
            'relevant_heuristics': []
        }

        try:
            sessions_dir = Path.home() / '.claude' / 'projects'
            if not sessions_dir.exists():
                return analysis

            session_files = sorted(
                sessions_dir.glob('*/*.jsonl'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            current_session = None
            for sf in session_files:
                if 'agent-' not in sf.name:
                    current_session = sf
                    break

            if not current_session:
                return analysis

            tool_counts = Counter()
            domains_mentioned = set()
            actions = []

            with open(current_session, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('type') == 'tool_use':
                            tool_name = entry.get('name', 'unknown')
                            tool_counts[tool_name] += 1
                            actions.append(tool_name)
                        if entry.get('type') == 'assistant':
                            content = str(entry.get('message', {}).get('content', ''))
                            for domain in ['react', 'api', 'database', 'frontend', 'backend', 'security', 'testing', 'infrastructure']:
                                if domain in content.lower():
                                    domains_mentioned.add(domain)
                    except (json.JSONDecodeError, KeyError):
                        continue

            analysis['tool_counts'] = dict(tool_counts.most_common(10))
            analysis['domains'] = list(domains_mentioned)

            if len(actions) >= 3:
                action_counts = Counter(actions)
                for action, count in action_counts.most_common(3):
                    if count >= 3:
                        analysis['patterns'].append({
                            'action': action,
                            'count': count,
                            'suggestion': f"Repeated {action} usage ({count}x) - consider automation"
                        })

            if tool_counts.get('Edit', 0) > 5 and tool_counts.get('Bash', 0) > 3:
                analysis['suggested_heuristics'].append({
                    'domain': 'workflow',
                    'rule': 'Run tests after multiple file edits',
                    'explanation': 'Session had many edits followed by bash commands - testing pattern detected'
                })

            if tool_counts.get('Read', 0) > 10:
                analysis['suggested_heuristics'].append({
                    'domain': 'exploration',
                    'rule': 'Use grep/glob before reading many files',
                    'explanation': f'High file read count ({tool_counts.get("Read", 0)}) - targeted search may be faster'
                })

        except (OSError, IOError):
            pass

        self.session_analysis = analysis
        return analysis

    def display_session_analysis(self):
        """Display automated session analysis results."""
        if not any(self.session_analysis.values()):
            return

        print("\n[*] Session Analysis (auto-detected)")

        if self.session_analysis.get('domains'):
            print(f"   Domains worked on: {', '.join(self.session_analysis['domains'])}")

        if self.session_analysis.get('tool_counts'):
            top_tools = list(self.session_analysis['tool_counts'].items())[:5]
            tool_str = ', '.join([f"{t[0]}({t[1]}x)" for t in top_tools])
            print(f"   Tool usage: {tool_str}")

        if self.session_analysis.get('patterns'):
            print(f"   Patterns detected: {len(self.session_analysis['patterns'])}")
            for p in self.session_analysis['patterns'][:3]:
                print(f"      - {p['suggestion']}")

    def get_relevant_heuristics(self) -> List[Dict[str, Any]]:
        """Get heuristics relevant to domains worked on today."""
        if not self.session_analysis.get('domains'):
            return []

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                domains = self.session_analysis['domains']
                placeholders = ','.join(['?' for _ in domains])

                cursor.execute(f"""
                    SELECT id, domain, rule, times_validated, times_violated, confidence
                    FROM heuristics
                    WHERE status = 'active'
                    AND domain IN ({placeholders})
                    AND (times_validated + times_violated) >= 3
                    ORDER BY confidence DESC
                    LIMIT 5
                """, domains)

                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error:
            return []

    def prompt_heuristic_validation(self, heuristics: List[Dict[str, Any]]):
        """Step 4: Allow user to validate or violate relevant heuristics."""
        if not heuristics:
            return

        print("\n[*] Heuristic Validation (review today's relevant rules)")
        for h in heuristics:
            print(f"   [{h['id']}] {h['rule']}")
            print(f"       Domain: {h['domain']} | Confidence: {h['confidence']:.2f} | Validated: {h['times_validated']} | Violated: {h['times_violated']}")

        if not self.interactive:
            print('[PROMPT_NEEDED] {"type": "heuristic_validation", "heuristics": ' + json.dumps([h['id'] for h in heuristics]) + '}')
            return

        try:
            response = input("\n   Validate any of these? (enter IDs comma-separated, or 'n'): ").strip()
            if response.lower() not in ['n', 'no', '']:
                for hid in response.split(','):
                    hid = hid.strip()
                    if hid.isdigit():
                        self._record_validation(int(hid), validated=True)
                        self.learnings_recorded['heuristics_validated'] += 1

            response = input("   Violate any? (enter IDs comma-separated, or 'n'): ").strip()
            if response.lower() not in ['n', 'no', '']:
                for hid in response.split(','):
                    hid = hid.strip()
                    if hid.isdigit():
                        self._record_validation(int(hid), validated=False)
                        self.learnings_recorded['heuristics_violated'] += 1

        except (EOFError, KeyboardInterrupt):
            pass

    def _record_validation(self, heuristic_id: int, validated: bool):
        """Record a validation or violation for a heuristic."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                if validated:
                    cursor.execute("""
                        UPDATE heuristics
                        SET times_validated = times_validated + 1,
                            confidence = MIN(1.0, confidence + 0.02)
                        WHERE id = ?
                    """, (heuristic_id,))
                else:
                    cursor.execute("""
                        UPDATE heuristics
                        SET times_violated = times_violated + 1,
                            confidence = MAX(0.1, confidence - 0.05)
                        WHERE id = ?
                    """, (heuristic_id,))

                if cursor.rowcount == 0:
                    print(f"   [!] Heuristic {heuristic_id} not found")
                    return

                conn.commit()
                print(f"   [OK] Heuristic {heuristic_id} {'validated' if validated else 'violated'}")
        except sqlite3.Error as e:
            print(f"   [!] Could not record: {e}")

    def prompt_suggested_heuristics(self):
        """Step 5: Present auto-detected patterns as potential heuristics."""
        suggestions = self.session_analysis.get('suggested_heuristics', [])
        if not suggestions:
            return

        print("\n[*] Auto-Detected Patterns (potential heuristics)")
        for i, s in enumerate(suggestions, 1):
            print(f"   [{i}] {s['rule']}")
            print(f"       Domain: {s['domain']} | Reason: {s['explanation']}")

        if not self.interactive:
            print('[PROMPT_NEEDED] {"type": "suggested_heuristics", "suggestions": ' + json.dumps(suggestions) + '}')
            return

        try:
            response = input("\n   Record any of these? (enter numbers comma-separated, or 'n'): ").strip()
            if response.lower() not in ['n', 'no', '']:
                for idx in response.split(','):
                    idx = idx.strip()
                    if idx.isdigit() and 0 < int(idx) <= len(suggestions):
                        s = suggestions[int(idx) - 1]
                        self._record_suggested_heuristic(s)

        except (EOFError, KeyboardInterrupt):
            pass

    def _record_suggested_heuristic(self, suggestion: Dict[str, Any]):
        """Record an auto-suggested heuristic."""
        try:
            cmd = [
                sys.executable,
                str(self.elf_home / 'scripts' / 'record-heuristic.py'),
                '--domain', suggestion['domain'],
                '--rule', suggestion['rule'],
                '--explanation', suggestion['explanation'],
                '--confidence', '0.5',
                '--source', 'auto-detected'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"   [OK] Heuristic recorded: {suggestion['rule'][:50]}...")
                self.learnings_recorded['heuristics'] += 1
            else:
                error_detail = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"   [!] Failed to record heuristic: {error_detail}")
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"   [!] Error: {e}")

    def _load_state(self) -> Dict[str, Any]:
        """Load checkout state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
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
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, title, domain, created_at
                    FROM plans
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)

                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
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
                prompt_data = {"type": "postmortem", "plan_id": plan["id"], "title": plan["title"]}
                print(f'[PROMPT_NEEDED] {json.dumps(prompt_data)}')
            return

        for plan in plans:
            try:
                response = input(f"\nComplete postmortem for plan {plan['id']} ({plan['title']})? [Y/n]: ").strip().lower()
                if response not in ['n', 'no']:
                    self._collect_and_record_postmortem(plan['id'], plan['title'])
            except (EOFError, KeyboardInterrupt):
                break

    def _collect_and_record_postmortem(self, plan_id: int, _title: str):
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
        """Step 9: Display session statistics."""
        print("\n[=] Session Summary")
        print(f"   Postmortems recorded: {self.learnings_recorded['postmortems']}")
        print(f"   Heuristics recorded: {self.learnings_recorded['heuristics']}")
        if self.learnings_recorded['heuristics_validated'] > 0 or self.learnings_recorded['heuristics_violated'] > 0:
            print(f"   Heuristics validated: {self.learnings_recorded['heuristics_validated']}")
            print(f"   Heuristics violated: {self.learnings_recorded['heuristics_violated']}")
        print(f"   Failures documented: {self.learnings_recorded['failures']}")
        print(f"   Notes saved: {'Yes' if self.learnings_recorded['notes'] else 'No'}")

    def complete_checkout(self):
        """Step 8: Complete checkout."""
        print("\n[OK] Checkout complete. Session learnings recorded!")
        print("")

    def run(self):
        """Execute the complete checkout workflow."""
        try:
            # Step 0: Analyze Session (auto)
            self.analyze_session()

            # Step 1: Display Banner
            self.display_banner()

            # Step 1b: Display Session Analysis
            self.display_session_analysis()

            # Step 2: Detect Active Plans
            plans = self.detect_active_plans()

            # Step 3: Postmortem Prompt
            if plans:
                self.prompt_postmortem(plans)

            # Step 4: Heuristic Validation
            relevant_heuristics = self.get_relevant_heuristics()
            if relevant_heuristics:
                self.prompt_heuristic_validation(relevant_heuristics)

            # Step 5: Auto-Detected Pattern Suggestions
            self.prompt_suggested_heuristics()

            # Step 6: Manual Heuristic Discovery
            self.prompt_heuristic()

            # Step 7: Failure Documentation
            self.prompt_failure()

            # Step 8: Quick Notes
            self.collect_quick_notes()

            # Step 9: Session Statistics
            self.display_session_stats()

            # Step 10: Complete
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
