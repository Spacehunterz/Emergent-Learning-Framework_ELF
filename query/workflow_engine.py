"""
Workflow Engine for step-based task execution.

Enables long-running, resumable workflows with discrete steps.
Inspired by BMAD-METHOD's step-file architecture but adapted for learning tasks.

Key concepts:
- Workflows are sequences of steps with defined inputs/outputs
- State is tracked in output file frontmatter
- Steps can checkpoint and resume from last completed step
- Each step loads just-in-time to conserve context

Usage:
    from workflow_engine import WorkflowEngine

    engine = WorkflowEngine(workflow_path)
    engine.run()  # Runs from current checkpoint
    engine.run(from_step=3)  # Resume from specific step
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Try to import yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from frontmatter import (
    parse_frontmatter,
    format_frontmatter,
    read_file_with_frontmatter,
    update_file_frontmatter,
)


class WorkflowStep:
    """Represents a single step in a workflow."""

    def __init__(self, step_num: int, path: Path, metadata: Dict[str, Any] = None):
        self.step_num = step_num
        self.path = path
        self.metadata = metadata or {}
        self._content = None
        self._instructions = None

    @property
    def content(self) -> str:
        """Load step content (just-in-time loading)."""
        if self._content is None:
            if self.path.exists():
                self._content = self.path.read_text(encoding='utf-8')
            else:
                self._content = ""
        return self._content

    @property
    def instructions(self) -> str:
        """Extract instructions from step content."""
        if self._instructions is None:
            _, body = parse_frontmatter(self.content)
            self._instructions = body
        return self._instructions

    @property
    def step_metadata(self) -> Dict[str, Any]:
        """Get frontmatter metadata from step file."""
        fm, _ = parse_frontmatter(self.content)
        return fm

    def __repr__(self) -> str:
        return f"WorkflowStep({self.step_num}, {self.path.name})"


class WorkflowState:
    """Tracks workflow execution state."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self._state = None
        self._content = None

    def load(self) -> Tuple[Dict[str, Any], str]:
        """Load current state from output file."""
        if self.output_path.exists():
            self._state, self._content = read_file_with_frontmatter(self.output_path)
        else:
            self._state = self._default_state()
            self._content = ""
        return self._state, self._content

    def _default_state(self) -> Dict[str, Any]:
        """Create default workflow state."""
        return {
            'workflow_status': 'not_started',
            'steps_completed': [],
            'current_step': 0,
            'started': None,
            'updated': None,
            'checkpoints': [],
        }

    @property
    def state(self) -> Dict[str, Any]:
        if self._state is None:
            self.load()
        return self._state

    @property
    def content(self) -> str:
        if self._content is None:
            self.load()
        return self._content

    @property
    def steps_completed(self) -> List[int]:
        return self.state.get('steps_completed', [])

    @property
    def current_step(self) -> int:
        return self.state.get('current_step', 0)

    @property
    def status(self) -> str:
        return self.state.get('workflow_status', 'not_started')

    def mark_step_complete(self, step_num: int, output: str = None) -> None:
        """Mark a step as completed and save state."""
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        if step_num not in self.state['steps_completed']:
            self.state['steps_completed'].append(step_num)
            self.state['steps_completed'].sort()

        self.state['current_step'] = step_num + 1
        self.state['updated'] = now
        self.state['workflow_status'] = 'in_progress'

        # Add checkpoint
        checkpoint = {
            'step': step_num,
            'completed_at': now,
        }
        self.state['checkpoints'].append(checkpoint)

        # Update content if output provided
        if output:
            self._content = (self._content or "") + output

        self._save()

    def mark_started(self) -> None:
        """Mark workflow as started."""
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.state['workflow_status'] = 'in_progress'
        self.state['started'] = now
        self.state['updated'] = now
        self._save()

    def mark_completed(self) -> None:
        """Mark workflow as completed."""
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.state['workflow_status'] = 'completed'
        self.state['updated'] = now
        self._save()

    def mark_paused(self, reason: str = None) -> None:
        """Mark workflow as paused at current step."""
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.state['workflow_status'] = 'paused'
        self.state['updated'] = now
        if reason:
            self.state['pause_reason'] = reason
        self._save()

    def append_content(self, content: str) -> None:
        """Append content to output file."""
        self._content = (self._content or "") + content
        self._save()

    def _save(self) -> None:
        """Save state to output file."""
        full_content = format_frontmatter(self.state) + (self._content or "")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(full_content, encoding='utf-8')


class WorkflowEngine:
    """
    Engine for executing step-based workflows.

    Workflow Directory Structure:
        workflow_name/
        +-- workflow.yaml      # Workflow metadata and step definitions
        +-- steps/
        |   +-- step-01-name.md
        |   +-- step-02-name.md
        |   +-- step-03-name.md
        +-- output/            # Generated output (state tracked here)
    """

    def __init__(self, workflow_path: Path):
        """
        Initialize workflow engine.

        Args:
            workflow_path: Path to workflow directory or workflow.yaml
        """
        if workflow_path.is_file():
            self.workflow_dir = workflow_path.parent
            self.config_path = workflow_path
        else:
            self.workflow_dir = workflow_path
            self.config_path = workflow_path / 'workflow.yaml'

        self.config = self._load_config()
        self.steps = self._load_steps()
        self.state = WorkflowState(self._get_output_path())

    def _load_config(self) -> Dict[str, Any]:
        """Load workflow configuration."""
        if not self.config_path.exists():
            # Look for workflow.md as alternative
            md_path = self.workflow_dir / 'workflow.md'
            if md_path.exists():
                fm, _ = read_file_with_frontmatter(md_path)
                return fm
            return self._default_config()

        content = self.config_path.read_text(encoding='utf-8')

        if YAML_AVAILABLE:
            return yaml.safe_load(content) or {}
        else:
            # Basic fallback parser
            return self._basic_yaml_parse(content)

    def _default_config(self) -> Dict[str, Any]:
        """Default workflow configuration."""
        return {
            'name': self.workflow_dir.name,
            'description': 'Workflow',
            'steps_dir': 'steps',
            'output_dir': 'output',
            'output_file': 'result.md',
        }

    def _basic_yaml_parse(self, content: str) -> Dict[str, Any]:
        """Basic YAML-like parser for simple configs."""
        result = {}
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                result[key] = value
        return result

    def _load_steps(self) -> List[WorkflowStep]:
        """Load all step files."""
        steps_dir = self.workflow_dir / self.config.get('steps_dir', 'steps')

        if not steps_dir.exists():
            return []

        steps = []
        step_files = sorted(steps_dir.glob('step-*.md'))

        for path in step_files:
            # Extract step number from filename (step-01-name.md -> 1)
            try:
                num_str = path.stem.split('-')[1]
                step_num = int(num_str)
            except (IndexError, ValueError):
                continue

            steps.append(WorkflowStep(step_num, path))

        return steps

    def _get_output_path(self) -> Path:
        """Get path to output file."""
        output_dir = self.workflow_dir / self.config.get('output_dir', 'output')
        output_file = self.config.get('output_file', 'result.md')
        return output_dir / output_file

    @property
    def name(self) -> str:
        return self.config.get('name', self.workflow_dir.name)

    @property
    def description(self) -> str:
        return self.config.get('description', '')

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    def get_step(self, step_num: int) -> Optional[WorkflowStep]:
        """Get step by number."""
        for step in self.steps:
            if step.step_num == step_num:
                return step
        return None

    def get_next_step(self) -> Optional[WorkflowStep]:
        """Get the next step to execute based on current state."""
        next_num = self.state.current_step + 1
        return self.get_step(next_num)

    def get_pending_steps(self) -> List[WorkflowStep]:
        """Get all steps not yet completed."""
        completed = set(self.state.steps_completed)
        return [s for s in self.steps if s.step_num not in completed]

    def can_resume(self) -> bool:
        """Check if workflow can be resumed."""
        return self.state.status in ('in_progress', 'paused') and len(self.get_pending_steps()) > 0

    def get_status_summary(self) -> Dict[str, Any]:
        """Get workflow status summary."""
        return {
            'name': self.name,
            'status': self.state.status,
            'total_steps': self.total_steps,
            'completed_steps': len(self.state.steps_completed),
            'current_step': self.state.current_step,
            'can_resume': self.can_resume(),
            'next_step': self.get_next_step().step_num if self.get_next_step() else None,
            'output_path': str(self.state.output_path),
        }

    def get_step_instructions(self, step_num: int) -> Optional[str]:
        """Get instructions for a specific step."""
        step = self.get_step(step_num)
        if step:
            return step.instructions
        return None

    def start(self) -> Dict[str, Any]:
        """
        Start the workflow from the beginning.

        Returns:
            Dict with first step information
        """
        self.state.load()  # Reset state
        self.state._state = self.state._default_state()
        self.state.mark_started()

        first_step = self.get_step(1)
        if not first_step:
            return {'error': 'No steps defined in workflow'}

        return {
            'status': 'started',
            'workflow': self.name,
            'step': 1,
            'total_steps': self.total_steps,
            'instructions': first_step.instructions,
        }

    def resume(self, from_step: int = None) -> Dict[str, Any]:
        """
        Resume workflow from checkpoint or specific step.

        Args:
            from_step: Optional step number to resume from

        Returns:
            Dict with step information
        """
        self.state.load()

        if from_step is not None:
            step_num = from_step
        else:
            # Resume from next incomplete step
            step_num = self.state.current_step + 1
            if step_num == 1 and self.state.status == 'not_started':
                return self.start()

        step = self.get_step(step_num)
        if not step:
            if step_num > self.total_steps:
                return {
                    'status': 'completed',
                    'message': 'All steps completed',
                    'output_path': str(self.state.output_path),
                }
            return {'error': f'Step {step_num} not found'}

        return {
            'status': 'resumed',
            'workflow': self.name,
            'step': step_num,
            'total_steps': self.total_steps,
            'completed': self.state.steps_completed,
            'instructions': step.instructions,
        }

    def complete_step(self, step_num: int, output: str = None) -> Dict[str, Any]:
        """
        Mark a step as complete and get next step.

        Args:
            step_num: Step number that was completed
            output: Optional output content to append

        Returns:
            Dict with next step information or completion status
        """
        self.state.mark_step_complete(step_num, output)

        next_step = self.get_step(step_num + 1)
        if not next_step:
            self.state.mark_completed()
            return {
                'status': 'completed',
                'workflow': self.name,
                'message': 'Workflow completed successfully',
                'output_path': str(self.state.output_path),
            }

        return {
            'status': 'step_completed',
            'completed_step': step_num,
            'next_step': step_num + 1,
            'total_steps': self.total_steps,
            'instructions': next_step.instructions,
        }

    def pause(self, reason: str = None) -> Dict[str, Any]:
        """
        Pause workflow at current step.

        Args:
            reason: Optional reason for pausing

        Returns:
            Dict with pause status
        """
        self.state.mark_paused(reason)
        return {
            'status': 'paused',
            'workflow': self.name,
            'current_step': self.state.current_step,
            'reason': reason,
            'can_resume': True,
        }


def list_workflows(base_dir: Path) -> List[Dict[str, Any]]:
    """
    List all available workflows in a directory.

    Args:
        base_dir: Directory containing workflow subdirectories

    Returns:
        List of workflow summaries
    """
    workflows = []

    if not base_dir.exists():
        return workflows

    for path in base_dir.iterdir():
        if not path.is_dir():
            continue

        # Check for workflow.yaml or workflow.md
        config_yaml = path / 'workflow.yaml'
        config_md = path / 'workflow.md'

        if config_yaml.exists() or config_md.exists():
            try:
                engine = WorkflowEngine(path)
                workflows.append(engine.get_status_summary())
            except Exception:
                continue

    return workflows


# CLI for testing
if __name__ == '__main__':
    import sys

    print("=== Workflow Engine Test ===\n")

    # Test with example workflow path
    if len(sys.argv) > 1:
        workflow_path = Path(sys.argv[1])
        if workflow_path.exists():
            engine = WorkflowEngine(workflow_path)
            print(f"Workflow: {engine.name}")
            print(f"Description: {engine.description}")
            print(f"Total steps: {engine.total_steps}")
            print(f"\nStatus: {json.dumps(engine.get_status_summary(), indent=2)}")
        else:
            print(f"Workflow not found: {workflow_path}")
    else:
        print("Usage: python workflow_engine.py <workflow_path>")
