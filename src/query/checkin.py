#!/usr/bin/env python3
"""
Emergent Learning Framework - Checkin Workflow Orchestrator

Implements the 8-step checkin process with proper state tracking,
banner display, dashboard prompting, and multi-model selection.

Steps:
1. Display ELF Banner
2. Load and parse building context
3. Display formatted golden rules & heuristics
4. Optionally summarize previous session
5. Ask about dashboard (first checkin only)
6. Ask about model selection (first checkin only)
7. Handle CEO decisions
8. Report ready status
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import subprocess


class CheckinOrchestrator:
    """Orchestrates the full checkin workflow."""

    # Banner for display (ASCII-safe for cross-platform compatibility)
    BANNER = """
+------------------------------------+
|    Emergent Learning Framework     |
+------------------------------------+
|                                    |
|      #####   #      #####          |
|      #       #      #              |
|      ####    #      ####           |
|      #       #      #              |
|      #####   ##### #              |
|                                    |
+------------------------------------+
"""

    def __init__(self, interactive: bool = None):
        """
        Initialize the checkin orchestrator.

        Args:
            interactive: Force interactive mode on/off. If None, auto-detect.
                         When False, skips input() prompts and outputs JSON hints
                         for Claude to ask questions via AskUserQuestion tool.
        """
        # Auto-detect interactive mode if not specified
        if interactive is None:
            self.interactive = sys.stdin.isatty()
        else:
            self.interactive = interactive

        # Find ELF home using elf_paths if available
        self.elf_home = self._resolve_elf_home()
        self.state_file = Path.home() / '.claude' / '.elf_checkin_state'
        self.selected_model = os.environ.get('ELF_MODEL', 'claude')
        self.is_first_checkin = self._check_first_checkin()

    def _resolve_elf_home(self) -> Path:
        """Resolve ELF home using centralized elf_paths or fallback."""
        # Add parent directory (src) to sys.path to find elf_paths
        try:
            current_dir = Path(__file__).resolve().parent
            src_dir = current_dir.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            
            from elf_paths import get_base_path
            return get_base_path()
        except ImportError:
            # Fallback path discovery
            return self._find_elf_home_fallback()

    def _find_elf_home_fallback(self) -> Path:
        """Find the ELF home directory by checking multiple locations (Legacy)."""
        # Try 1: ELF_BASE_PATH env var
        if os.environ.get('ELF_BASE_PATH'):
            return Path(os.environ['ELF_BASE_PATH']).expanduser().resolve()

        # Try 2: ~/.claude/emergent-learning (global install)
        global_elf = Path.home() / '.claude' / 'emergent-learning'
        if global_elf.exists():
            return global_elf

        # Try 3: Parent directories from current script location
        current_file = Path(__file__).resolve()
        for parent in [current_file.parent.parent, current_file.parent.parent.parent]:
            if (parent / 'query' / 'query.py').exists():
                return parent

        # Fallback to global location (will error if not found)
        return global_elf

    def _check_first_checkin(self) -> bool:
        """
        Determine if this is the first checkin of the conversation.

        Uses conversation session ID or a marker file to track state.
        """
        # If we have an explicit session marker, use that
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Check if this is a new session
                    return not state.get('checkin_completed', False)
            except:
                pass

        return True  # Default to first checkin if we can't determine

    def _mark_checkin_complete(self):
        """Mark that first checkin has been completed."""
        state = {'checkin_completed': True, 'timestamp': datetime.now().isoformat()}
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f)

    def display_banner(self):
        """Step 1: Display the ELF ASCII banner."""
        print(self.BANNER)

    def load_building_context(self) -> Dict[str, Any]:
        """Step 2: Load context from the building via query system."""
        print("[*] Loading Building Context...")

        try:
            # Call query.py --context to get the data
            result = subprocess.run(
                [sys.executable, str(self.elf_home / 'src' / 'query' / 'query.py'), '--context'],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'  # Replace problematic chars instead of failing
            )

            if result.returncode == 0:
                return {'raw_output': result.stdout}
            else:
                print(f"[!] Warning: Could not load full context")
                return {'raw_output': ''}

        except subprocess.TimeoutExpired:
            print("[!] Warning: Context loading timed out")
            return {'raw_output': ''}
        except Exception as e:
            print(f"[!] Warning: Error loading context")
            return {'raw_output': ''}

    def display_golden_rules(self, context: Dict[str, Any]):
        """Step 3: Extract and display golden rules from context."""
        output = context.get('raw_output', '')

        # Look for golden rules section in output
        if 'Golden Rules' in output or 'TIER 1' in output:
            print("[OK] Golden Rules loaded")
        else:
            print("[OK] Context loaded")

    def prompt_dashboard(self) -> bool:
        """Step 5: Ask about dashboard (first checkin only)."""
        if not self.is_first_checkin:
            return False  # Don't ask again

        if not self.interactive:
            # Non-interactive: Output JSON hint for Claude to use AskUserQuestion
            print('[PROMPT_NEEDED] {"type": "dashboard", "question": "Start ELF Dashboard?", "default": "yes"}')
            return False  # Claude will handle this

        print("")
        print("[+] Start ELF Dashboard?")
        print("   The dashboard provides metrics, model routing, and system health.")

        try:
            response = input("   Start Dashboard? [Y/n]: ").strip().lower()
            return response in ['y', 'yes', '']  # Default to yes
        except (EOFError, KeyboardInterrupt):
            return False

    def prompt_model_selection(self) -> str:
        """
        Step 6: Ask about model selection (first checkin only).

        Returns the selected model name.
        """
        if not self.is_first_checkin:
            return self.selected_model  # Use environment or default

        if not self.interactive:
            # Non-interactive: Output JSON hint for Claude to use AskUserQuestion
            print('[PROMPT_NEEDED] {"type": "model", "question": "Select AI model", "options": ["claude", "gemini", "codex", "skip"]}')
            return self.selected_model  # Claude will handle this

        print("")
        print("[=] Select Your Active Model")
        print("   Available models:")
        print("     (c)laude    - Orchestrator, backend, architecture (active)")
        print("     (g)emini    - Frontend, React, large codebases (1M context)")
        print("     (o)dex      - Graphics, debugging, precision (128K context)")
        print("     (s)kip      - Use current model")

        try:
            response = input("   Select [c/g/o/s]: ").strip().lower()

            model_map = {
                'c': 'claude',
                'g': 'gemini',
                'o': 'codex',
                's': self.selected_model  # Keep current
            }

            selected = model_map.get(response[0] if response else 's', self.selected_model)

            # Store selection in environment
            os.environ['ELF_MODEL'] = selected
            self.selected_model = selected

            if selected != 'claude':
                print(f"   [OK] Using {selected}")

            return selected

        except (EOFError, KeyboardInterrupt, IndexError):
            return self.selected_model

    def start_dashboard(self):
        """Start the dashboard in a visible terminal window that user can close."""
        try:
            # Check for both .bat and .ps1 versions
            dashboard_bat = self.elf_home / 'apps' / 'dashboard' / 'run-dashboard.bat'
            dashboard_ps1 = self.elf_home / 'apps' / 'dashboard' / 'run-dashboard.ps1'
            dashboard_sh = self.elf_home / 'apps' / 'dashboard' / 'run-dashboard.sh'

            if sys.platform == 'win32':
                # Launch PowerShell with -Command to avoid file association issues
                if dashboard_ps1.exists():
                    # Use & operator to invoke script as command, not "open" it
                    cmd = f'& "{dashboard_ps1}"'
                    subprocess.Popen(
                        ['powershell', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', cmd],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    print(f"   [!] Dashboard script not found")
                    return
                print("   [OK] Dashboard launching (close the terminal window to stop)")
            elif dashboard_sh.exists():
                # Unix: launch in new terminal if possible
                subprocess.Popen(['bash', str(dashboard_sh)])
                print("   [OK] Dashboard launching")
            else:
                print(f"   [!] Dashboard script not found")
        except Exception as e:
            print(f"   [!] Could not start dashboard: {e}")

    def check_ceo_decisions(self) -> bool:
        """Step 7: Check for pending CEO decisions."""
        ceo_inbox = self.elf_home / 'ceo-inbox'

        if ceo_inbox.exists():
            pending = list(ceo_inbox.glob('*.md'))
            if pending:
                print(f"\n[!] Pending CEO Decisions: {len(pending)}")
                for item in pending[:3]:  # Show first 3
                    print(f"   - {item.stem}")
                if len(pending) > 3:
                    print(f"   ... and {len(pending) - 3} more")
                return True

        return False

    def run(self):
        """Execute the complete checkin workflow."""
        # Step 1: Display Banner
        self.display_banner()

        # Step 2: Load building context
        context = self.load_building_context()

        # Step 3: Display golden rules (parsed from context)
        self.display_golden_rules(context)

        # Step 4: Optionally summarize previous session (skipped for now)
        # Would spawn async haiku agent here

        # Step 5: Ask about dashboard (first checkin only)
        if self.is_first_checkin:
            start_dashboard = self.prompt_dashboard()

            if start_dashboard:
                self.start_dashboard()

        # Step 6: Ask about model selection (first checkin only)
        if self.is_first_checkin:
            self.prompt_model_selection()

        # Step 7: Check for CEO decisions
        has_decisions = self.check_ceo_decisions()

        # Step 8: Complete
        print("\n[OK] Checkin complete. Ready to work!")
        print("")

        # Mark first checkin as done
        if self.is_first_checkin:
            self._mark_checkin_complete()


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="ELF Checkin Workflow")
    parser.add_argument('--non-interactive', '-n', action='store_true',
                       help="Run in non-interactive mode (output prompts as JSON hints)")
    args = parser.parse_args()

    try:
        orchestrator = CheckinOrchestrator(interactive=not args.non_interactive)
        orchestrator.run()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nCheckin cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Checkin failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
