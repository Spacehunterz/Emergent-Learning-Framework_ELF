#!/usr/bin/env python3
"""
Run step-based workflows with checkpoint and resume capability.

Usage:
    # List available workflows
    python run-workflow.py --list

    # Start a new workflow
    python run-workflow.py --workflow deep-research --start

    # Resume from last checkpoint
    python run-workflow.py --workflow deep-research --resume

    # Resume from specific step
    python run-workflow.py --workflow deep-research --step 3

    # Mark current step complete and get next
    python run-workflow.py --workflow deep-research --complete

    # Pause workflow
    python run-workflow.py --workflow deep-research --pause "waiting for CEO decision"

    # Show workflow status
    python run-workflow.py --workflow deep-research --status

    # Output as JSON (for programmatic use)
    python run-workflow.py --workflow deep-research --status --format json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
WORKFLOWS_DIR = BASE_DIR / 'workflows'

# Add query module to path
sys.path.insert(0, str(BASE_DIR / 'query'))

from workflow_engine import WorkflowEngine, list_workflows


def format_step_output(data: Dict[str, Any], format_type: str = 'text') -> str:
    """Format step data for display."""
    if format_type == 'json':
        return json.dumps(data, indent=2)

    status = data.get('status', 'unknown')

    if status == 'error':
        return f"ERROR: {data.get('error', 'Unknown error')}"

    lines = []

    if status == 'started':
        lines.append(f"=== Started Workflow: {data.get('workflow')} ===")
        lines.append(f"")
        lines.append(f"Step 1 of {data.get('total_steps')}")
        lines.append(f"")
        lines.append("--- INSTRUCTIONS ---")
        lines.append(data.get('instructions', ''))

    elif status == 'resumed':
        lines.append(f"=== Resumed Workflow: {data.get('workflow')} ===")
        lines.append(f"")
        lines.append(f"Step {data.get('step')} of {data.get('total_steps')}")
        completed = data.get('completed', [])
        if completed:
            lines.append(f"Previously completed: {', '.join(map(str, completed))}")
        lines.append(f"")
        lines.append("--- INSTRUCTIONS ---")
        lines.append(data.get('instructions', ''))

    elif status == 'step_completed':
        lines.append(f"[OK] Step {data.get('completed_step')} completed")
        lines.append(f"")
        lines.append(f"Next: Step {data.get('next_step')} of {data.get('total_steps')}")
        lines.append(f"")
        lines.append("--- INSTRUCTIONS ---")
        lines.append(data.get('instructions', ''))

    elif status == 'completed':
        lines.append(f"=== Workflow Complete: {data.get('workflow', 'unknown')} ===")
        lines.append(f"")
        lines.append(data.get('message', 'All steps completed'))
        lines.append(f"")
        lines.append(f"Output: {data.get('output_path', 'N/A')}")

    elif status == 'paused':
        lines.append(f"=== Workflow Paused: {data.get('workflow')} ===")
        lines.append(f"")
        lines.append(f"Paused at step {data.get('current_step')}")
        reason = data.get('reason')
        if reason:
            lines.append(f"Reason: {reason}")
        lines.append(f"")
        lines.append("Use --resume to continue")

    else:
        lines.append(f"Status: {status}")
        for key, value in data.items():
            if key != 'status':
                lines.append(f"  {key}: {value}")

    return '\n'.join(lines)


def format_status_output(data: Dict[str, Any], format_type: str = 'text') -> str:
    """Format status data for display."""
    if format_type == 'json':
        return json.dumps(data, indent=2)

    lines = [
        f"=== Workflow Status: {data.get('name')} ===",
        f"",
        f"Status:      {data.get('status', 'unknown')}",
        f"Progress:    {data.get('completed_steps', 0)}/{data.get('total_steps', 0)} steps",
        f"Current:     Step {data.get('current_step', 0)}",
        f"Can resume:  {'Yes' if data.get('can_resume') else 'No'}",
    ]

    next_step = data.get('next_step')
    if next_step:
        lines.append(f"Next step:   {next_step}")

    lines.append(f"")
    lines.append(f"Output: {data.get('output_path', 'N/A')}")

    return '\n'.join(lines)


def format_list_output(workflows: list, format_type: str = 'text') -> str:
    """Format workflow list for display."""
    if format_type == 'json':
        return json.dumps(workflows, indent=2)

    if not workflows:
        return "No workflows found."

    lines = ["=== Available Workflows ===", ""]

    for wf in workflows:
        name = wf.get('name', 'unknown')
        status = wf.get('status', 'unknown')
        progress = f"{wf.get('completed_steps', 0)}/{wf.get('total_steps', 0)}"

        # Status indicator
        if status == 'completed':
            indicator = '[DONE]'
        elif status == 'in_progress':
            indicator = '[...]'
        elif status == 'paused':
            indicator = '[||]'
        else:
            indicator = '[   ]'

        lines.append(f"{indicator} {name}")
        lines.append(f"      Progress: {progress} steps | Status: {status}")
        lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Run step-based workflows with checkpoint/resume',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List available workflows
    python run-workflow.py --list

    # Start new workflow
    python run-workflow.py --workflow deep-research --start

    # Resume from checkpoint
    python run-workflow.py --workflow deep-research --resume

    # Complete current step, get next
    python run-workflow.py --workflow deep-research --complete

    # Pause workflow
    python run-workflow.py --workflow deep-research --pause "reason"
"""
    )

    parser.add_argument('--list', action='store_true',
                       help='List available workflows')
    parser.add_argument('--workflow', '-w', type=str,
                       help='Workflow name or path')
    parser.add_argument('--start', action='store_true',
                       help='Start workflow from beginning')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last checkpoint')
    parser.add_argument('--step', type=int,
                       help='Resume from specific step number')
    parser.add_argument('--complete', action='store_true',
                       help='Mark current step complete, get next')
    parser.add_argument('--pause', type=str, nargs='?', const='',
                       help='Pause workflow with optional reason')
    parser.add_argument('--status', action='store_true',
                       help='Show workflow status')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o', type=str,
                       help='Append output content when completing step')

    args = parser.parse_args()

    # List workflows
    if args.list:
        workflows = list_workflows(WORKFLOWS_DIR)
        print(format_list_output(workflows, args.format))
        return 0

    # Require workflow for other operations
    if not args.workflow:
        parser.print_help()
        return 1

    # Resolve workflow path
    if Path(args.workflow).exists():
        workflow_path = Path(args.workflow)
    else:
        workflow_path = WORKFLOWS_DIR / args.workflow

    if not workflow_path.exists():
        print(f"ERROR: Workflow not found: {args.workflow}", file=sys.stderr)
        print(f"Looking in: {workflow_path}", file=sys.stderr)
        print(f"\nUse --list to see available workflows", file=sys.stderr)
        return 1

    # Initialize engine
    try:
        engine = WorkflowEngine(workflow_path)
    except Exception as e:
        print(f"ERROR: Failed to load workflow: {e}", file=sys.stderr)
        return 1

    # Execute command
    if args.status:
        result = engine.get_status_summary()
        print(format_status_output(result, args.format))
        return 0

    if args.start:
        result = engine.start()
        print(format_step_output(result, args.format))
        return 0 if result.get('status') != 'error' else 1

    if args.resume or args.step:
        result = engine.resume(from_step=args.step)
        print(format_step_output(result, args.format))
        return 0 if result.get('status') != 'error' else 1

    if args.complete:
        # Get current step from state
        current = engine.state.current_step
        if current == 0:
            current = 1  # First step

        result = engine.complete_step(current, args.output)
        print(format_step_output(result, args.format))
        return 0 if result.get('status') != 'error' else 1

    if args.pause is not None:
        reason = args.pause if args.pause else None
        result = engine.pause(reason)
        print(format_step_output(result, args.format))
        return 0

    # Default: show status
    result = engine.get_status_summary()
    print(format_status_output(result, args.format))
    return 0


if __name__ == '__main__':
    sys.exit(main())
