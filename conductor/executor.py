#!/usr/bin/env python3
"""
Real Executor: Execute nodes by signaling to Claude Code CLI via hooks.

This module provides actual execution of workflow nodes by:
1. Writing task instructions to a signal file
2. Waiting for hook-based execution
3. Reading results from SQLite

INTEGRATION:
- Works with existing hooks (pre_task.py, post_task.py)
- Uses SQLite bridge for result capture
- Supports both synchronous and async execution patterns

USAGE:
    from executor import CLIExecutor

    executor = CLIExecutor()
    conductor.set_node_executor(executor.execute)
    conductor.run_workflow("my-workflow")
"""

import json
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, Tuple, List
from datetime import datetime

# Import validation utilities
from validation import (
    validate_identifier,
    validate_node_id,
    validate_agent_type,
    ValidationError
)


class CLIExecutor:
    """
    Execute nodes via Claude Code CLI.

    This executor creates signal files that hooks can read,
    or directly invokes Claude Code CLI for subagent tasks.
    """

    def __init__(self, project_root: str = ".", timeout: int = 300):
        """
        Initialize the CLI executor.

        Args:
            project_root: Project directory for coordination
            timeout: Max seconds to wait for execution (default 5 min)
        """
        self.project_root = Path(project_root).resolve()
        self.timeout = timeout
        self.coordination_dir = self.project_root / ".coordination"

        # Ensure coordination directory exists
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

        # SQLite for result checking
        self.db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

    def execute(self, node, context: Dict) -> Tuple[str, Dict]:
        """
        Execute a node - main entry point for conductor.

        Args:
            node: Node object with id, name, prompt_template, node_type, config
            context: Shared workflow context

        Returns:
            Tuple of (result_text, result_dict)
        """
        node_type = node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type)

        if node_type == "swarm":
            return self._execute_swarm(node, context)
        elif node_type == "parallel":
            return self._execute_parallel(node, context)
        else:
            return self._execute_single(node, context)

    def _execute_single(self, node, context: Dict) -> Tuple[str, Dict]:
        """Execute a single agent node."""
        # Validate node.id before using it
        try:
            validated_node_id = validate_node_id(node.id)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        # Format prompt with context
        prompt = node.prompt_template
        if context:
            try:
                prompt = prompt.format(**context)
            except KeyError:
                pass  # Keep original if formatting fails

        # Get agent type from config and validate it
        agent_type = node.config.get("agent_type", "general-purpose") if node.config else "general-purpose"
        try:
            validated_agent_type = validate_agent_type(agent_type)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        # Write signal file for execution
        signal_file = self._write_signal(validated_node_id, {
            "action": "execute_node",
            "node_id": validated_node_id,
            "node_name": node.name,
            "agent_type": validated_agent_type,
            "prompt": prompt,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })

        # For CLI execution, we need to spawn the actual process
        # This uses claude CLI with the prompt
        result_text, result_dict = self._spawn_claude_task(
            node_id=validated_node_id,
            prompt=prompt,
            agent_type=validated_agent_type
        )

        # Clean up signal file
        signal_file.unlink(missing_ok=True)

        return result_text, result_dict

    def _execute_swarm(self, node, context: Dict) -> Tuple[str, Dict]:
        """Execute a swarm phase with multiple ants."""
        # Validate base node.id
        try:
            validated_node_id = validate_node_id(node.id)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        config = node.config or {}
        num_ants = config.get("num_ants", 3)
        roles = config.get("roles", ["scout", "analyzer", "fixer"])

        # Validate agent_type if provided
        agent_type = config.get("agent_type", "Explore")
        try:
            validated_agent_type = validate_agent_type(agent_type)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        # Format base prompt
        base_prompt = node.prompt_template
        if context:
            try:
                base_prompt = base_prompt.format(**context)
            except KeyError:
                pass

        # Spawn multiple ants
        results = []
        for i in range(min(num_ants, len(roles))):
            role = roles[i % len(roles)]
            # Validate role before using it in node_id
            try:
                validated_role = validate_identifier(role, "role", max_length=50)
            except ValidationError as e:
                # Skip invalid roles
                continue

            ant_prompt = f"""[SWARM] You are a {validated_role} agent.

{base_prompt}

Report findings in ## FINDINGS section with format:
- [type:tags:importance] description

Types: fact, discovery, warning, blocker, hypothesis
Importance: low, normal, high, critical
"""
            result_text, result_dict = self._spawn_claude_task(
                node_id=f"{validated_node_id}-{validated_role}-{i}",
                prompt=ant_prompt,
                agent_type=validated_agent_type
            )
            results.append({
                "role": validated_role,
                "result_text": result_text,
                "result_dict": result_dict
            })

        # Aggregate results
        all_findings = []
        all_files = []
        for r in results:
            all_findings.extend(r["result_dict"].get("findings", []))
            all_files.extend(r["result_dict"].get("files_modified", []))

        combined_text = "\n\n---\n\n".join([
            f"## {r['role']}\n{r['result_text']}" for r in results
        ])

        return combined_text, {
            "findings": all_findings,
            "files_modified": list(set(all_files)),
            "swarm_results": results
        }

    def _execute_parallel(self, node, context: Dict) -> Tuple[str, Dict]:
        """Execute parallel sub-nodes."""
        # Validate base node.id
        try:
            validated_node_id = validate_node_id(node.id)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        config = node.config or {}
        sub_prompts = config.get("prompts", [node.prompt_template])

        # Validate agent_type if provided
        agent_type = config.get("agent_type", "general-purpose")
        try:
            validated_agent_type = validate_agent_type(agent_type)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        results = []
        for i, sub_prompt in enumerate(sub_prompts):
            if context:
                try:
                    sub_prompt = sub_prompt.format(**context)
                except KeyError:
                    pass

            result_text, result_dict = self._spawn_claude_task(
                node_id=f"{validated_node_id}-parallel-{i}",
                prompt=sub_prompt,
                agent_type=validated_agent_type
            )
            results.append({
                "index": i,
                "result_text": result_text,
                "result_dict": result_dict
            })

        # Aggregate
        all_findings = []
        all_files = []
        for r in results:
            all_findings.extend(r["result_dict"].get("findings", []))
            all_files.extend(r["result_dict"].get("files_modified", []))

        combined_text = "\n\n---\n\n".join([r['result_text'] for r in results])

        return combined_text, {
            "findings": all_findings,
            "files_modified": list(set(all_files)),
            "parallel_results": results
        }

    def _spawn_claude_task(self, node_id: str, prompt: str,
                          agent_type: str = "general-purpose") -> Tuple[str, Dict]:
        """
        Spawn a Claude Code task and capture results.

        This is the core execution that actually runs claude CLI.

        Args:
            node_id: Node identifier (must be pre-validated)
            prompt: Prompt text to execute
            agent_type: Agent type (must be pre-validated)

        Returns:
            Tuple of (result_text, result_dict)
        """
        # SECURITY: Validate node_id before using it in filenames and environment variables
        # This prevents command injection through malicious node IDs
        try:
            validated_node_id = validate_node_id(node_id)
        except ValidationError as e:
            error_msg = f"[SECURITY ERROR] Invalid node_id: {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        # Validate agent_type
        try:
            validated_agent_type = validate_agent_type(agent_type)
        except ValidationError as e:
            error_msg = f"[SECURITY ERROR] Invalid agent_type: {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        # Create a temp file for the prompt using validated node_id
        prompt_file = self.coordination_dir / f"prompt-{validated_node_id}.md"
        result_file = self.coordination_dir / f"result-{validated_node_id}.json"

        # Write prompt to file
        prompt_file.write_text(prompt, encoding='utf-8')

        # Build claude command
        # Using --print for non-interactive output capture
        cmd = [
            "claude",
            "--print",  # Non-interactive, print result
            "--dangerously-skip-permissions",  # Skip confirmations
            "-p", prompt
        ]

        try:
            # Execute claude CLI with validated node_id in environment
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.project_root),
                env={**os.environ, "CLAUDE_SWARM_NODE": validated_node_id}
            )

            result_text = result.stdout or ""
            if result.stderr:
                result_text += f"\n\n[STDERR]\n{result.stderr}"

            # Parse findings from output
            findings = self._extract_findings(result_text)
            files = self._extract_files(result_text)

            result_dict = {
                "exit_code": result.returncode,
                "findings": findings,
                "files_modified": files,
                "success": result.returncode == 0
            }

            # Save result using validated_node_id
            result_file.write_text(json.dumps({
                "node_id": validated_node_id,
                "result_text": result_text[:10000],  # Truncate
                "result_dict": result_dict,
                "timestamp": datetime.now().isoformat()
            }, indent=2), encoding='utf-8')

            return result_text, result_dict

        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Node {validated_node_id} timed out after {self.timeout}s", {
                "error": "timeout",
                "findings": [],
                "files_modified": []
            }
        except FileNotFoundError:
            return "[ERROR] claude CLI not found", {
                "error": "cli_not_found",
                "findings": [],
                "files_modified": []
            }
        except Exception as e:
            return f"[ERROR] {str(e)}", {
                "error": str(e),
                "findings": [],
                "files_modified": []
            }
        finally:
            # Cleanup
            prompt_file.unlink(missing_ok=True)

    def _write_signal(self, node_id: str, data: Dict) -> Path:
        """
        Write a signal file for hook coordination.

        Args:
            node_id: Node identifier (must be pre-validated)
            data: Signal data to write

        Returns:
            Path to the signal file
        """
        # SECURITY: Validate node_id before using it in filename
        # This should already be validated by callers, but defense in depth
        try:
            validated_node_id = validate_node_id(node_id)
        except ValidationError as e:
            # If validation fails, raise an exception since this is a programming error
            raise ValueError(f"Invalid node_id passed to _write_signal: {str(e)}")

        signal_file = self.coordination_dir / f"signal-{validated_node_id}.json"
        signal_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return signal_file

    def _extract_findings(self, output: str) -> List[Dict]:
        """Extract findings from output text."""
        import re
        findings = []

        # Look for ## FINDINGS section
        match = re.search(r'## FINDINGS\s*\n(.*?)(?=\n##|\n---|\Z)', output, re.DOTALL | re.IGNORECASE)
        if match:
            for line in match.group(1).split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    # Parse [type:tags:importance] content
                    type_match = re.match(r'-\s*\[([^\]]+)\]\s*(.+)', line)
                    if type_match:
                        bracket = type_match.group(1)
                        content = type_match.group(2)
                        parts = bracket.split(':')
                        findings.append({
                            "type": parts[0] if parts else "note",
                            "tags": parts[1].split(',') if len(parts) > 1 else [],
                            "importance": parts[2] if len(parts) > 2 else "normal",
                            "content": content
                        })

        return findings

    def _extract_files(self, output: str) -> List[str]:
        """Extract modified files from output."""
        import re
        files = []
        patterns = [
            r'(?:created|modified|edited|wrote|updated)\s+[`"\']?([^\s`"\']+\.[a-zA-Z]+)',
            r'File\s+[`"\']([^\s`"\']+\.[a-zA-Z]+)[`"\']',
        ]
        for pattern in patterns:
            files.extend(re.findall(pattern, output, re.IGNORECASE))
        return list(set(files))


class HookSignalExecutor:
    """
    Alternative executor that signals via files for hook-based execution.

    Use this when you want the existing Claude Code session to execute
    nodes via the hook system rather than spawning new CLI processes.
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.coordination_dir = self.project_root / ".coordination"
        self.coordination_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

    def execute(self, node, context: Dict) -> Tuple[str, Dict]:
        """
        Signal for execution via hooks and wait for result.

        The active Claude session should pick up the signal via hooks
        and execute the task.
        """
        # SECURITY: Validate node_id before using it
        try:
            validated_node_id = validate_node_id(node.id)
        except ValidationError as e:
            error_msg = f"[VALIDATION ERROR] {str(e)}"
            return error_msg, {
                "error": "validation_error",
                "error_message": str(e),
                "findings": [],
                "files_modified": []
            }

        # Write instruction signal
        instruction = {
            "action": "execute",
            "node_id": validated_node_id,
            "node_name": node.name,
            "prompt": node.prompt_template.format(**context) if context else node.prompt_template,
            "node_type": node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
            "config": node.config or {},
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }

        signal_file = self.coordination_dir / f"conductor-signal-{validated_node_id}.json"
        signal_file.write_text(json.dumps(instruction, indent=2), encoding='utf-8')

        # Wait for result (hook should update the signal file)
        timeout = 300
        start = time.time()

        while time.time() - start < timeout:
            try:
                data = json.loads(signal_file.read_text())
                if data.get("status") == "completed":
                    signal_file.unlink(missing_ok=True)
                    return data.get("result_text", ""), data.get("result_dict", {})
                elif data.get("status") == "failed":
                    signal_file.unlink(missing_ok=True)
                    return data.get("error", "Unknown error"), {"error": data.get("error")}
            except (json.JSONDecodeError, FileNotFoundError):
                pass

            time.sleep(1)

        signal_file.unlink(missing_ok=True)
        return f"[TIMEOUT] Waiting for node {validated_node_id}", {"error": "timeout"}


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test executor")
    parser.add_argument("--prompt", "-p", required=True, help="Prompt to execute")
    parser.add_argument("--type", default="single", choices=["single", "swarm", "parallel"])
    parser.add_argument("--project", default=".", help="Project root")

    args = parser.parse_args()

    from dataclasses import dataclass
    from enum import Enum

    class NodeType(Enum):
        SINGLE = "single"
        SWARM = "swarm"
        PARALLEL = "parallel"

    @dataclass
    class TestNode:
        id: str = "test-node"
        name: str = "Test Node"
        node_type: NodeType = NodeType.SINGLE
        prompt_template: str = ""
        config: Dict = None

    executor = CLIExecutor(args.project)
    node = TestNode(
        prompt_template=args.prompt,
        node_type=NodeType(args.type)
    )

    print(f"Executing {args.type} node...")
    result_text, result_dict = executor.execute(node, {})

    print("\n=== RESULT TEXT ===")
    print(result_text[:2000])
    print("\n=== RESULT DICT ===")
    print(json.dumps(result_dict, indent=2))
