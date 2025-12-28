#!/usr/bin/env python3
"""
Swarm Orchestrator - Run unlimited agents without context exhaustion.

This script generates agent prompts that enforce file-based output,
ensuring context stays flat regardless of how many agents you spawn.

Supports multi-model agents: claude, gemini, codex
- Claude agents: Use Task tool (native subagents)
- Gemini/Codex agents: Use spawn-model.py (external CLIs)

Usage:
    python run-swarm.py --config swarm.yaml
    python run-swarm.py --config swarm.yaml --init-only  # Just create .coordination
    python run-swarm.py --list-results                    # Show all agent results
    python run-swarm.py --summary                         # Summarize all results
    python run-swarm.py --detect-models                   # Show available AI CLIs

The key insight: agents write full output to files, return only paths.
Context grows by ~20 tokens per agent instead of ~2000.
"""

import argparse
import json
import os
import sys
import yaml
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add query directory to path for model detection
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src' / 'query'))
try:
    from model_detection import detect_installed_models, suggest_model_for_task
    HAS_MODEL_DETECTION = True
except ImportError:
    HAS_MODEL_DETECTION = False
# Force UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except:
        pass

SWARM_RESULTS_DIR = ".coordination/swarm-results"
AGENT_LOG = ".coordination/AGENT_LOG.md"

FILE_OUTPUT_INSTRUCTIONS = '''
## CRITICAL: File-Based Output Protocol

You MUST follow this output protocol to prevent context exhaustion:

### Rule: Write to files, return only paths

1. **All substantial output** (>100 tokens) goes to files:
   - Results: `.coordination/swarm-results/{agent_name}-result.md`
   - Code: Write directly to target files in the codebase
   - Logs: `.coordination/swarm-results/{agent_name}-log.md`

2. **Your return message** must be ONLY:
   ```
   COMPLETED: {agent_name}
   Results: .coordination/swarm-results/{agent_name}-result.md
   Files changed: [list of files]
   ```

3. **DO NOT** return:
   - Full code blocks in your response
   - Detailed explanations (put in result file)
   - Analysis text (put in result file)

### Result File Format

Write to `.coordination/swarm-results/{agent_name}-result.md`:

```markdown
# {Agent Name} Results

**Task:** {what you were asked to do}
**Status:** COMPLETED | PARTIAL | BLOCKED
**Duration:** {rough estimate}

## Summary
{2-3 sentence summary}

## Details
{full detailed output, code explanations, etc.}

## Files Changed
- `path/to/file.ts` - {what changed}

## Decisions Made
- {decision}: {rationale}

## Handoff Notes
{anything the orchestrator or next agent needs to know}
```

### Why This Matters

Without this protocol, 10 agents returning 2000 tokens each = 20,000 tokens in main context = OOM.
With this protocol, 10 agents returning 20 tokens each = 200 tokens = unlimited agents possible.
'''

SWARM_CONFIG_TEMPLATE = '''# Swarm Configuration
# Define your agents and their tasks here

name: "{swarm_name}"
created: "{timestamp}"

# Coordination directory (created automatically)
coordination_dir: ".coordination"

# Multi-model support: {available_models}
# Claude models (sonnet, opus, haiku): Use Task tool (native)
# External models (gemini, codex): Use spawn-model.py

# Agent definitions
agents:
  - name: "designer"
    description: "Design and plan the implementation"
    scope:
      - "docs/"
    task: |
      Your detailed task description here.
      Be specific about what needs to be done.
    model: "sonnet"  # Claude: sonnet, opus, haiku | External: gemini, codex

  - name: "implementer"
    description: "Implement the designs"
    scope:
      - "src/"
    task: |
      Another task description.
    model: "haiku"

# Execution strategy
strategy:
  mode: "parallel"        # parallel or sequential
  batch_size: 5           # For parallel: max concurrent agents
  compact_between: false  # Run /compact between batches
  auto_route: false       # Auto-suggest models based on task content
'''


def get_project_root() -> Path:
    cwd = Path.cwd()
    if (cwd / ".coordination").exists():
        return cwd
    if (cwd / ".git").exists():
        return cwd
    return cwd


def init_coordination(project_root: Path) -> None:
    coord_dir = project_root / ".coordination"
    results_dir = coord_dir / "swarm-results"

    coord_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)

    gitkeep = results_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("")

    print(f"[OK] Initialized {coord_dir}")
    print(f"[OK] Created {results_dir}")


def load_swarm_config(config_path: Path) -> dict:
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def generate_agent_prompt(agent: dict, swarm_name: str, project_root: Path = None) -> str:
    if project_root is None:
        project_root = get_project_root()
    abs_root = project_root.resolve()
    root_str = str(abs_root).replace(chr(92), "/")
    abs_result = abs_root / ".coordination/swarm-results" / f"{agent["name"]}-result.md"
    result_str = str(abs_result).replace(chr(92), "/")

    agent_name = agent["name"]
    task = agent["task"]
    scope = agent.get("scope", [])
    description = agent.get("description", "")

    scope_text = ""
    if scope:
        scope_text = f"""
### Your Scope
You are responsible for these paths:
{chr(10).join(f'- `{s}`' for s in scope)}

Do NOT modify files outside your scope unless absolutely necessary.
"""

    prompt = f'''# Agent: {agent_name}
Swarm: {swarm_name}

{description}

{FILE_OUTPUT_INSTRUCTIONS.replace("{agent_name}", agent_name).replace(".coordination/swarm-results/", f"{root_str}/.coordination/swarm-results/")}

## Coordination Protocol

Before starting:
1. Read `.coordination/PROJECT_CONTEXT.md` if it exists
2. Read `.coordination/INTERFACES.md` if it exists
3. Check `.coordination/AGENT_LOG.md` for recent activity

When done:
1. Write your full results to `.coordination/swarm-results/{agent_name}-result.md`
2. Update `.coordination/AGENT_LOG.md` with a brief entry
3. Return ONLY the completion message (not full results)
{scope_text}
## Your Task

{task}

---

Remember: Write results to file, return only the path. This is mandatory.
'''
    return prompt


def is_claude_model(model: str) -> bool:
    """Check if model is a Claude variant (uses Task tool)."""
    return model.lower() in ['sonnet', 'opus', 'haiku', 'claude']


def is_external_model(model: str) -> bool:
    """Check if model is external (uses spawn-model.py)."""
    return model.lower() in ['gemini', 'codex']


def get_available_models_string() -> str:
    """Get string of available models for display."""
    if not HAS_MODEL_DETECTION:
        return "claude (sonnet, opus, haiku)"

    models = detect_installed_models()
    available = []
    for name, info in models.items():
        if info.get('installed'):
            available.append(name)
    return ', '.join(available) if available else 'claude only'


def generate_orchestrator_instructions(config: dict, available_models: Dict[str, Any] = None) -> str:
    swarm_name = config.get("name", "unnamed-swarm")
    agents = config.get("agents", [])
    strategy = config.get("strategy", {})
    mode = strategy.get("mode", "parallel")
    batch_size = strategy.get("batch_size", 5)
    compact_between = strategy.get("compact_between", False)

    # Detect available models
    if available_models is None and HAS_MODEL_DETECTION:
        available_models = detect_installed_models()

    # Categorize agents by model type
    claude_agents = [a for a in agents if is_claude_model(a.get("model", "sonnet"))]
    external_agents = [a for a in agents if is_external_model(a.get("model", ""))]

    agent_list = []
    for i, agent in enumerate(agents, 1):
        model = agent.get("model", "sonnet")
        model_type = "Task tool" if is_claude_model(model) else "spawn-model.py"
        agent_list.append(f'{i}. **{agent["name"]}** ({model} via {model_type}): {agent.get("description", "No description")}')

    instructions = f'''# Swarm Orchestration Instructions

## Swarm: {swarm_name}
Generated: {datetime.now().isoformat()}

## Available Models
'''

    if available_models:
        for name, info in available_models.items():
            if info.get('installed'):
                version = info.get('version', 'unknown')
                instructions += f"- **{name}**: v{version} [ready]\n"
            else:
                instructions += f"- **{name}**: not installed\n"

    instructions += f'''
## Agents to Spawn

{chr(10).join(agent_list)}

## Execution Strategy

- **Mode:** {mode}
- **Batch size:** {batch_size}
- **Compact between batches:** {compact_between}
- **Claude agents:** {len(claude_agents)}
- **External agents (gemini/codex):** {len(external_agents)}

## How to Execute

### Step 1: Initialize Coordination
```bash
python <elf-repo>/tools/scripts/run-swarm.py --config swarm.yaml --init-only
```

### Step 2: Spawn Agents

'''

    # Claude agents section
    if claude_agents:
        instructions += "**Claude Agents** (via Task tool):\n\n"
        for agent in claude_agents:
            model = agent.get("model", "sonnet")
            instructions += f'''```
Task tool:
  description: "{agent['name']}"
  subagent_type: "general-purpose"
  model: "{model}"
  run_in_background: true
  prompt: [See generated prompt for {agent['name']}]
```

'''

    # External agents section
    if external_agents:
        instructions += "**External Agents** (via spawn-model.py):\n\n"
        for agent in external_agents:
            model = agent.get("model", "gemini")
            instructions += f'''```bash
# Run {agent['name']} with {model}
python <elf-repo>/tools/scripts/spawn-model.py \\
  --model {model} \\
  --prompt-file .coordination/swarm-prompts/{agent['name']}-prompt.md \\
  --output .coordination/swarm-results/{agent['name']}-result.md
```

'''

    instructions += '''### Step 3: Monitor Progress

Check agent status:
```bash
ls -la .coordination/swarm-results/
```

Read individual results:
```bash
cat .coordination/swarm-results/{agent-name}-result.md
```

### Step 4: Summarize Results

```bash
python <elf-repo>/tools/scripts/run-swarm.py --summary
```

## Important Notes

- Agents write full output to `.coordination/swarm-results/`
- Agents return only "COMPLETED" + file path (~20 tokens)
- Context stays flat regardless of agent count
- You can run 20+ agents without context exhaustion

'''
    return instructions


def list_results(project_root: Path) -> None:
    results_dir = project_root / SWARM_RESULTS_DIR
    if not results_dir.exists():
        print("No swarm results directory found.")
        return

    results = list(results_dir.glob("*-result.md"))
    if not results:
        print("No agent results found.")
        return

    print(f"\n{'='*60}")
    print("SWARM RESULTS")
    print(f"{'='*60}\n")

    for result_file in sorted(results):
        agent_name = result_file.stem.replace("-result", "")
        stat = result_file.stat()
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        content = result_file.read_text(encoding='utf-8')
        status = "UNKNOWN"
        if "Status:** COMPLETED" in content:
            status = "[OK] COMPLETED"
        elif "Status:** PARTIAL" in content:
            status = "[~] PARTIAL"
        elif "Status:** BLOCKED" in content:
            status = "[X] BLOCKED"

        print(f"  {agent_name}")
        print(f"    Status: {status}")
        print(f"    Size: {size} bytes")
        print(f"    Modified: {mtime}")
        print()


def summarize_results(project_root: Path) -> None:
    results_dir = project_root / SWARM_RESULTS_DIR
    if not results_dir.exists():
        print("No swarm results directory found.")
        return

    results = list(results_dir.glob("*-result.md"))
    if not results:
        print("No agent results found.")
        return

    print(f"\n{'='*60}")
    print("SWARM SUMMARY")
    print(f"{'='*60}\n")

    completed = 0
    partial = 0
    blocked = 0

    all_files_changed = []
    all_decisions = []
    all_handoffs = []

    for result_file in sorted(results):
        content = result_file.read_text(encoding='utf-8')

        if "Status:** COMPLETED" in content:
            completed += 1
        elif "Status:** PARTIAL" in content:
            partial += 1
        elif "Status:** BLOCKED" in content:
            blocked += 1

        if "## Files Changed" in content:
            start = content.find("## Files Changed")
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            files_section = content[start:end]
            for line in files_section.split("\n"):
                if line.startswith("- "):
                    all_files_changed.append(line)

        if "## Decisions Made" in content:
            start = content.find("## Decisions Made")
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            decisions_section = content[start:end]
            for line in decisions_section.split("\n"):
                if line.startswith("- "):
                    all_decisions.append(line)

        if "## Handoff Notes" in content:
            start = content.find("## Handoff Notes")
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            handoff_section = content[start:end].strip()
            if handoff_section and handoff_section != "## Handoff Notes":
                agent_name = result_file.stem.replace("-result", "")
                all_handoffs.append(f"**{agent_name}:** {handoff_section.replace('## Handoff Notes', '').strip()}")

    total = completed + partial + blocked
    print(f"Agents: {total} total")
    print(f"  [OK] Completed: {completed}")
    print(f"  [~] Partial: {partial}")
    print(f"  [X] Blocked: {blocked}")
    print()

    if all_files_changed:
        print("Files Changed:")
        for f in all_files_changed[:20]:
            print(f"  {f}")
        if len(all_files_changed) > 20:
            print(f"  ... and {len(all_files_changed) - 20} more")
        print()

    if all_decisions:
        print("Key Decisions:")
        for d in all_decisions[:10]:
            print(f"  {d}")
        if len(all_decisions) > 10:
            print(f"  ... and {len(all_decisions) - 10} more")
        print()

    if all_handoffs:
        print("Handoff Notes:")
        for h in all_handoffs:
            print(f"  {h[:200]}...")
        print()


def detect_models_cli() -> None:
    """CLI command to detect and display available models."""
    print("\n" + "=" * 50)
    print("MULTI-MODEL DETECTION")
    print("=" * 50 + "\n")

    if not HAS_MODEL_DETECTION:
        print("[!] Model detection module not available")
        print("    Claude is always available (current session)")
        return

    models = detect_installed_models()

    for name, info in models.items():
        if info.get('installed'):
            version = info.get('version', 'unknown')
            path = info.get('path', 'current session')
            strengths = ', '.join(info.get('strengths', [])[:3])
            print(f"[OK] {name}")
            print(f"     Version: {version}")
            print(f"     Path: {path}")
            print(f"     Strengths: {strengths}")
            print()
        else:
            print(f"[ ] {name} - not installed")
            print()

    # Summary
    available = [n for n, i in models.items() if i.get('installed')]
    print("-" * 50)
    print(f"Available for swarm: {', '.join(available)}")
    print("\nIn swarm.yaml, use:")
    print("  - Claude: model: sonnet | opus | haiku")
    if 'gemini' in available:
        print("  - Gemini: model: gemini")
    if 'codex' in available:
        print("  - Codex:  model: codex")
    print()


def create_template(output_path: Path) -> None:
    timestamp = datetime.now().isoformat()
    available_models = get_available_models_string()
    content = SWARM_CONFIG_TEMPLATE.format(
        swarm_name="my-swarm",
        timestamp=timestamp,
        available_models=available_models
    )
    output_path.write_text(content)
    print(f"[OK] Created swarm config template: {output_path}")
    print(f"     Available models: {available_models}")


def main():
    parser = argparse.ArgumentParser(
        description="Swarm Orchestrator - Run unlimited agents without context exhaustion"
    )
    parser.add_argument("--config", type=Path, help="Path to swarm config YAML")
    parser.add_argument("--init-only", action="store_true", help="Only initialize .coordination directory")
    parser.add_argument("--list-results", action="store_true", help="List all agent results")
    parser.add_argument("--summary", action="store_true", help="Summarize all agent results")
    parser.add_argument("--create-template", type=Path, help="Create a swarm config template")
    parser.add_argument("--generate-prompts", action="store_true", help="Generate agent prompts to stdout")
    parser.add_argument("--agent", type=str, help="Generate prompt for specific agent only")
    parser.add_argument("--output-dir", type=Path, help="Directory to write generated prompts")
    parser.add_argument("--detect-models", action="store_true", help="Detect available AI CLIs")

    args = parser.parse_args()
    project_root = get_project_root()

    if args.detect_models:
        detect_models_cli()
        return

    if args.create_template:
        create_template(args.create_template)
        return

    if args.list_results:
        list_results(project_root)
        return

    if args.summary:
        summarize_results(project_root)
        return

    if args.init_only:
        init_coordination(project_root)
        return

    if not args.config:
        parser.print_help()
        print("\nExamples:")
        print("  python run-swarm.py --detect-models                   # Check available AI CLIs")
        print("  python run-swarm.py --create-template swarm.yaml")
        print("  python run-swarm.py --config swarm.yaml --init-only")
        print("  python run-swarm.py --config swarm.yaml --generate-prompts")
        print("  python run-swarm.py --list-results")
        print("  python run-swarm.py --summary")
        return

    config = load_swarm_config(args.config)
    swarm_name = config.get("name", "unnamed-swarm")

    if args.generate_prompts:
        init_coordination(project_root)

        output_dir = args.output_dir or (project_root / ".coordination" / "swarm-prompts")
        output_dir.mkdir(parents=True, exist_ok=True)

        agents = config.get("agents", [])
        for agent in agents:
            if args.agent and agent["name"] != args.agent:
                continue

            prompt = generate_agent_prompt(agent, swarm_name)

            prompt_file = output_dir / f"{agent['name']}-prompt.md"
            prompt_file.write_text(prompt)
            print(f"[OK] Generated: {prompt_file}")

        instructions = generate_orchestrator_instructions(config)
        instructions_file = output_dir / "ORCHESTRATOR_INSTRUCTIONS.md"
        instructions_file.write_text(instructions)
        print(f"[OK] Generated: {instructions_file}")

        print(f"\nPrompts written to: {output_dir}")
        print("Read ORCHESTRATOR_INSTRUCTIONS.md for execution steps.")
    else:
        print(f"Swarm: {swarm_name}")
        print(f"Agents: {len(config.get('agents', []))}")
        print("\nUse --generate-prompts to create agent prompts")
        print("Use --init-only to initialize coordination directory")


if __name__ == "__main__":
    main()
