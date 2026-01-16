#!/usr/bin/env python3
"""
Ralph Loop Orchestrator

Coordinates Code Reviewer and Code Simplifier agents in iterative cycles.
Uses blackboard architecture (.coordination/ folder) for cross-agent communication.

Usage:
    python ralph_orchestrator.py --target <file> --max-iterations 5
    python ralph_orchestrator.py --target <file> --completion-promise "DONE: Code is clean"

The Ralph loop works like this:
1. Code Reviewer analyzes the code, identifies issues
2. Code Simplifier refactors based on review
3. Loop iterates - Reviewer checks simplifier output
4. Continue until quality gates met or max iterations

Handoff Protocol:
    Reviewer → Simplifier: .coordination/review-findings.json
    Simplifier → Reviewer: .coordination/simplified-code.json
    Loop status: .coordination/ralph-status.json
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional
from argparse import ArgumentParser


class RalphOrchestrator:
    """Orchestrates Code Reviewer and Code Simplifier in Ralph loop"""

    def __init__(self, target: str, max_iterations: int = 5, completion_promise: Optional[str] = None):
        self.target = Path(target)
        self.max_iterations = max_iterations
        self.completion_promise = completion_promise
        self.coordination_dir = Path.home() / '.claude' / '.coordination' / 'ralph-loop'
        self.iteration = 0
        self.state = self._init_state()

    def _init_state(self):
        """Initialize or load orchestrator state"""
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

        state_file = self.coordination_dir / 'status.json'
        if state_file.exists():
            with open(state_file) as f:
                return json.load(f)

        return {
            'target': str(self.target),
            'iterations': [],
            'current_iteration': 0,
            'status': 'initialized',
            'started_at': time.time()
        }

    def _save_state(self):
        """Persist orchestrator state to blackboard"""
        state_file = self.coordination_dir / 'status.json'
        with open(state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _read_target(self) -> str:
        """Read target file content"""
        if not self.target.exists():
            raise FileNotFoundError(f"Target file not found: {self.target}")

        with open(self.target) as f:
            return f.read()

    def _write_handoff_reviewer(self, code: str):
        """Write code to review for Code Reviewer agent"""
        handoff = {
            'iteration': self.iteration,
            'action': 'review',
            'code': code,
            'timestamp': time.time()
        }
        with open(self.coordination_dir / 'review-input.json', 'w') as f:
            json.dump(handoff, f, indent=2)

    def _read_handoff_reviewer(self) -> dict:
        """Read Code Reviewer findings"""
        findings_file = self.coordination_dir / 'review-findings.json'
        if not findings_file.exists():
            return {}

        with open(findings_file) as f:
            return json.load(f)

    def _write_handoff_simplifier(self, code: str, findings: dict):
        """Write review findings + code for Code Simplifier agent"""
        handoff = {
            'iteration': self.iteration,
            'action': 'simplify',
            'code': code,
            'review_findings': findings,
            'timestamp': time.time()
        }
        with open(self.coordination_dir / 'simplify-input.json', 'w') as f:
            json.dump(handoff, f, indent=2)

    def _read_handoff_simplifier(self) -> dict:
        """Read simplified code from Code Simplifier"""
        simplified_file = self.coordination_dir / 'simplified-code.json'
        if not simplified_file.exists():
            return {}

        with open(simplified_file) as f:
            return json.load(f)

    async def invoke_reviewer(self, code: str) -> dict:
        """Invoke Code Reviewer agent"""
        print(f"\n{'='*70}")
        print(f"ITERATION {self.iteration}: CODE REVIEWER")
        print(f"{'='*70}")

        self._write_handoff_reviewer(code)
        print("✓ Review request written to .coordination/")
        print(f"✓ Reviewing {len(code)} characters of code...")

        # Simulate agent execution - in real use, this would invoke
        # the code-reviewer agent through Claude Code Task tool
        print("[REVIEWER WOULD RUN HERE]")
        print("  - Analyze code structure")
        print("  - Identify issues/improvements")
        print("  - Write findings to .coordination/review-findings.json")

        # For now, read what was prepared
        findings = self._read_handoff_reviewer()
        return findings

    async def invoke_simplifier(self, code: str, findings: dict) -> str:
        """Invoke Code Simplifier agent"""
        print(f"\n{'='*70}")
        print(f"ITERATION {self.iteration}: CODE SIMPLIFIER")
        print(f"{'='*70}")

        self._write_handoff_simplifier(code, findings)
        print("✓ Simplify request written to .coordination/")
        print(f"✓ Found {len(findings.get('issues', []))} issues to address...")

        # Simulate agent execution
        print("[SIMPLIFIER WOULD RUN HERE]")
        print("  - Read review findings")
        print("  - Refactor code to address issues")
        print("  - Write simplified code to .coordination/simplified-code.json")

        # For now, read what was prepared
        result = self._read_handoff_simplifier()
        return result.get('code', code)

    async def run(self):
        """Execute Ralph loop"""
        print(f"\n{'='*70}")
        print("RALPH LOOP ORCHESTRATOR")
        print(f"{'='*70}")
        print(f"Target: {self.target}")
        print(f"Max iterations: {self.max_iterations}")
        print(f"Coordination: {self.coordination_dir}")
        print(f"{'='*70}\n")

        current_code = self._read_target()

        for iteration in range(1, self.max_iterations + 1):
            self.iteration = iteration
            self.state['current_iteration'] = iteration
            self.state['status'] = 'running'
            self._save_state()

            print(f"\n{'*'*70}")
            print(f"RALPH LOOP ITERATION {iteration}/{self.max_iterations}")
            print(f"{'*'*70}")

            # Step 1: Code Reviewer analyzes current code
            findings = await self.invoke_reviewer(current_code)

            # Step 2: Code Simplifier refactors based on findings
            simplified = await self.invoke_simplifier(current_code, findings)

            # Step 3: Check if we should continue or stop
            iteration_result = {
                'iteration': iteration,
                'timestamp': time.time(),
                'issues_found': len(findings.get('issues', [])),
                'refactored': simplified != current_code
            }
            self.state['iterations'].append(iteration_result)

            if simplified == current_code:
                print(f"\n✓ No changes made - code is stable")
                break

            current_code = simplified

            if iteration < self.max_iterations:
                print(f"\nWaiting before next iteration...")
                await asyncio.sleep(1)

        # Completion
        self.state['status'] = 'complete'
        self.state['completed_at'] = time.time()
        self._save_state()

        print(f"\n{'='*70}")
        print("RALPH LOOP COMPLETE")
        print(f"{'='*70}")
        print(f"Iterations: {len(self.state['iterations'])}")
        print(f"Final status: {self.state['status']}")

        if self.completion_promise:
            print(f"\n✓ Completion promise detected: {self.completion_promise}")
            print("✓ Ralph loop satisfied")


async def main():
    parser = ArgumentParser(description="Ralph Loop Orchestrator for Code Review cycles")
    parser.add_argument("--target", required=True, help="Target file to review and simplify")
    parser.add_argument("--max-iterations", type=int, default=5, help="Maximum loop iterations")
    parser.add_argument("--completion-promise", help="Promise to exit loop (e.g., 'DONE: Code is clean')")

    args = parser.parse_args()

    try:
        orchestrator = RalphOrchestrator(
            target=args.target,
            max_iterations=args.max_iterations,
            completion_promise=args.completion_promise
        )
        await orchestrator.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
