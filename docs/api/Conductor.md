# Conductor API

Comprehensive API reference for the Conductor workflow orchestration engine and swarm coordination system.

## Table of Contents

- [Overview](#overview)
- [Conductor Class](#conductor-class)
- [Workflow Definition](#workflow-definition)
- [Node Types](#node-types)
- [Agent Spawning](#agent-spawning)
- [Blackboard Communication](#blackboard-communication)
- [Pheromone Trails](#pheromone-trails)
- [Examples](#examples)

---

## Overview

The Conductor is a workflow orchestration engine that enables multi-agent coordination through:

1. **Workflow Graphs**: Define DAGs with nodes and edges
2. **Node Execution**: Fire nodes in dependency order
3. **Agent Spawning**: Single, parallel, or swarm execution
4. **Blackboard**: Shared state for real-time coordination
5. **Pheromone Trails**: Swarm intelligence hotspot tracking
6. **SQLite Persistence**: Historical query and analysis

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Conductor                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Workflows   │  │   Executor   │  │  Blackboard  │     │
│  │   (SQLite)   │  │   (Spawn)    │  │   (JSON)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Trails     │  │   Decisions  │  │     Runs     │     │
│  │ (Pheromone)  │  │   (Audit)    │  │  (Tracking)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Key Concepts

- **Workflow**: A named collection of nodes and edges
- **Node**: A unit of work (single agent, parallel agents, or swarm)
- **Edge**: A directed connection between nodes with optional conditions
- **Run**: An instance of workflow execution with tracked state
- **Execution**: A single node invocation within a run
- **Trail**: A pheromone marker laid by agents for coordination

---

## Conductor Class

### Initialization

```python
from conductor import Conductor

conductor = Conductor(
    base_path="~/.claude/emergent-learning",  # Optional: auto-resolved
    project_root="."                          # Project for blackboard coordination
)
```

#### Parameters

- `base_path` (Optional[str]): Path to emergent-learning directory. If None, resolved via `elf_paths.get_base_path()`
- `project_root` (str): Project root directory for blackboard coordination. Default: "."

#### Attributes

- `base_path` (Path): Resolved base path
- `db_path` (Path): Path to `memory/index.db`
- `project_root` (Path): Resolved project root
- `blackboard` (Optional[Blackboard]): Blackboard instance for real-time coordination
- `_node_executor` (Optional[Callable]): Custom node executor function

### Methods

#### `set_node_executor(executor)`

Set the callback function for executing nodes.

```python
def my_executor(node, context) -> Tuple[str, Dict]:
    """
    Execute a node.

    Args:
        node: Node object (id, name, node_type, prompt_template, config)
        context: Shared workflow context

    Returns:
        (result_text, result_dict)
    """
    # Your execution logic
    return "Result text", {"key": "value"}

conductor.set_node_executor(my_executor)
```

**Signature:**

```python
executor: Callable[[Node, Dict], Tuple[str, Dict]]
```

**Built-in Executors:**

- `CLIExecutor`: Spawns Claude CLI tasks
- `HookSignalExecutor`: Signals via files for hook-based execution

---

## Workflow Definition

### Creating Workflows

#### `create_workflow(name, description, nodes, edges, config) -> int`

Create a new workflow definition.

```python
workflow_id = conductor.create_workflow(
    name="bug-investigation",
    description="Multi-agent bug investigation workflow",
    nodes=[
        {
            "id": "scout",
            "name": "Scout Phase",
            "node_type": "swarm",
            "prompt_template": "Investigate bug: {bug_description}",
            "config": {
                "num_ants": 3,
                "roles": ["scout", "analyzer", "fixer"],
                "agent_type": "Explore"
            }
        },
        {
            "id": "synthesize",
            "name": "Synthesize Findings",
            "node_type": "single",
            "prompt_template": "Analyze findings and propose solution",
            "config": {"agent_type": "Analyst"}
        }
    ],
    edges=[
        {"from_node": "__start__", "to_node": "scout"},
        {"from_node": "scout", "to_node": "synthesize"},
        {"from_node": "synthesize", "to_node": "__end__"}
    ],
    config={"timeout": 600}
)
```

**Parameters:**

- `name` (str): Unique workflow name
- `description` (str): Human-readable description
- `nodes` (List[Dict]): List of node definitions (see [Node Structure](#node-structure))
- `edges` (List[Dict]): List of edge definitions (see [Edge Structure](#edge-structure))
- `config` (Dict): Default workflow configuration

**Returns:** Workflow ID (int)

#### Node Structure

```python
{
    "id": str,                    # Unique node ID
    "name": str,                  # Display name
    "node_type": str,             # "single" | "parallel" | "swarm"
    "prompt_template": str,       # Template with {variables}
    "config": {                   # Optional node configuration
        "agent_type": str,        # Agent persona
        "num_ants": int,          # For swarm nodes
        "roles": List[str],       # For swarm nodes
        "prompts": List[str]      # For parallel nodes
    }
}
```

#### Edge Structure

```python
{
    "from_node": str,        # Source node ID (or "__start__")
    "to_node": str,          # Target node ID (or "__end__")
    "condition": str,        # Optional condition (see [Conditions](#edge-conditions))
    "priority": int          # Execution order (default: 100)
}
```

### Retrieving Workflows

#### `get_workflow(name) -> Optional[Dict]`

Get a workflow by name.

```python
workflow = conductor.get_workflow("bug-investigation")

# Returns:
{
    "id": 1,
    "name": "bug-investigation",
    "description": "Multi-agent bug investigation workflow",
    "nodes": [...],
    "edges": [...],
    "config": {...},
    "created_at": "2025-12-11T10:30:00"
}
```

#### `list_workflows() -> List[Dict]`

List all workflow definitions.

```python
workflows = conductor.list_workflows()

# Returns:
[
    {
        "id": 1,
        "name": "bug-investigation",
        "description": "Multi-agent bug investigation",
        "created_at": "2025-12-11T10:30:00"
    },
    ...
]
```

---

## Node Types

### Single Node

Execute one agent with a prompt.

```python
{
    "id": "analyze",
    "name": "Analyze Bug",
    "node_type": "single",
    "prompt_template": "Analyze the bug in {file_path}",
    "config": {
        "agent_type": "Analyst"
    }
}
```

**Execution:**

1. Format prompt with context
2. Spawn single agent
3. Return result

### Parallel Node

Execute multiple agents concurrently.

```python
{
    "id": "multi-check",
    "name": "Run Multiple Checks",
    "node_type": "parallel",
    "prompt_template": "Check codebase",
    "config": {
        "agent_type": "QA",
        "prompts": [
            "Check for security vulnerabilities",
            "Check for performance issues",
            "Check for code quality"
        ]
    }
}
```

**Execution:**

1. Spawn agent for each prompt
2. Aggregate results
3. Merge findings and files

**Result Structure:**

```python
{
    "findings": [...],              # Merged from all agents
    "files_modified": [...],        # Unique files from all agents
    "parallel_results": [           # Individual results
        {
            "index": 0,
            "result_text": "...",
            "result_dict": {...}
        },
        ...
    ]
}
```

### Swarm Node

Execute multiple ants with different roles.

```python
{
    "id": "swarm-explore",
    "name": "Swarm Exploration",
    "node_type": "swarm",
    "prompt_template": "Explore the codebase for {issue}",
    "config": {
        "num_ants": 3,
        "roles": ["scout", "analyzer", "fixer"],
        "agent_type": "Explore"
    }
}
```

**Execution:**

1. Spawn `num_ants` agents with role-specific prompts
2. Each ant reports findings with standardized format
3. Aggregate all findings and trails

**Ant Prompt Format:**

```
[SWARM] You are a {role} agent.

{base_prompt}

Report findings in ## FINDINGS section with format:
- [type:tags:importance] description

Types: fact, discovery, warning, blocker, hypothesis
Importance: low, normal, high, critical
```

**Result Structure:**

```python
{
    "findings": [...],              # Merged from all ants
    "files_modified": [...],        # Unique files from all ants
    "swarm_results": [              # Individual ant results
        {
            "role": "scout",
            "result_text": "...",
            "result_dict": {...}
        },
        ...
    ]
}
```

---

## Agent Spawning

### CLIExecutor

Spawn agents via Claude Code CLI.

```python
from executor import CLIExecutor

executor = CLIExecutor(
    project_root=".",    # Project directory
    timeout=300          # Max seconds per execution
)

conductor.set_node_executor(executor.execute)
```

#### Execution Flow

1. **Validate inputs**: Check node_id and agent_type for security
2. **Create signal file**: Write execution metadata
3. **Spawn subprocess**: Execute `claude --print -p "{prompt}"`
4. **Capture output**: Parse stdout/stderr
5. **Extract findings**: Parse `## FINDINGS` section
6. **Extract files**: Detect modified files
7. **Return result**: Tuple of (result_text, result_dict)

#### Security Validation

The executor validates all identifiers to prevent command injection:

```python
from validation import validate_node_id, validate_agent_type, ValidationError

try:
    validated_node_id = validate_node_id(node.id)
    validated_agent_type = validate_agent_type(agent_type)
except ValidationError as e:
    return f"[VALIDATION ERROR] {str(e)}", {"error": "validation_error"}
```

**Validation Rules:**

- Only alphanumeric, underscore, hyphen allowed
- Max length: 100 chars (node_id), 50 chars (agent_type)
- Cannot start/end with special characters
- Agent types can include spaces

#### Environment Variables

```python
env = {
    **os.environ,
    "CLAUDE_SWARM_NODE": validated_node_id  # Node identifier
}
```

### HookSignalExecutor

Execute via hook-based signaling.

```python
from executor import HookSignalExecutor

executor = HookSignalExecutor(project_root=".")
conductor.set_node_executor(executor.execute)
```

#### Execution Flow

1. **Write signal file**: `conductor-signal-{node_id}.json`
2. **Wait for completion**: Hook updates signal file
3. **Read result**: Parse completed signal
4. **Cleanup**: Remove signal file

**Signal Format:**

```json
{
    "action": "execute",
    "node_id": "node-123",
    "node_name": "Analyze Bug",
    "prompt": "Formatted prompt text",
    "node_type": "single",
    "config": {},
    "timestamp": "2025-12-11T10:30:00",
    "status": "pending"
}
```

**Updated by Hook:**

```json
{
    ...
    "status": "completed",
    "result_text": "Analysis complete",
    "result_dict": {"findings": [...]}
}
```

---

## Workflow Execution

### Running Workflows

#### `run_workflow(workflow_name, input_data, on_node_complete) -> int`

Execute a workflow from start to finish.

```python
def progress_callback(node_id, success, result):
    print(f"Node {node_id}: {'✓' if success else '✗'}")

run_id = conductor.run_workflow(
    workflow_name="bug-investigation",
    input_data={"bug_description": "Login fails with null pointer"},
    on_node_complete=progress_callback
)
```

**Parameters:**

- `workflow_name` (str): Name of workflow to execute
- `input_data` (Dict): Initial context variables
- `on_node_complete` (Callable): Optional callback after each node

**Returns:** Run ID (int)

**Execution Algorithm:**

1. Load workflow definition
2. Create run record
3. Initialize context with input_data
4. Build edge index for traversal
5. Get initial nodes from `__start__`
6. Execute nodes in topological order:
   - Execute current batch (could be parallel)
   - Merge results into context
   - Evaluate edge conditions
   - Get next nodes
7. Update run status to completed
8. Return run_id

### Run Management

#### `start_run(workflow_name, workflow_id, input_data, phase) -> int`

Start a new workflow run.

```python
run_id = conductor.start_run(
    workflow_name="bug-investigation",
    workflow_id=1,
    input_data={"bug_description": "Login fails"},
    phase="init"
)
```

**Parameters:**

- `workflow_name` (Optional[str]): Workflow name (for ad-hoc runs)
- `workflow_id` (Optional[int]): Workflow ID
- `input_data` (Dict): Initial parameters
- `phase` (str): Initial phase name

**Returns:** Run ID (int)

#### `get_run(run_id) -> Optional[Dict]`

Get a workflow run by ID.

```python
run = conductor.get_run(123)

# Returns:
{
    "id": 123,
    "workflow_id": 1,
    "workflow_name": "bug-investigation",
    "status": "completed",
    "phase": "synthesis",
    "input": {"bug_description": "..."},
    "output": {"solution": "..."},
    "context": {"findings": [...], ...},
    "total_nodes": 5,
    "completed_nodes": 5,
    "failed_nodes": 0,
    "started_at": "2025-12-11T10:30:00",
    "completed_at": "2025-12-11T10:35:00",
    "error_message": null
}
```

#### `update_run_status(run_id, status, error_message, output)`

Update the status of a workflow run.

```python
conductor.update_run_status(
    run_id=123,
    status="completed",
    output={"solution": "Fixed by updating auth logic"}
)
```

**Status Values:**

- `"pending"`: Not started
- `"running"`: In progress
- `"completed"`: Successfully finished
- `"failed"`: Encountered error
- `"cancelled"`: User cancelled

#### `update_run_phase(run_id, phase)`

Update the current phase of a workflow run.

```python
conductor.update_run_phase(123, "synthesis")
```

Logs a decision record for phase transition.

#### `update_run_context(run_id, context)`

Update the shared context of a workflow run.

```python
conductor.update_run_context(123, {
    "bug_description": "Login fails",
    "findings": [...],
    "solution": "Update auth logic"
})
```

### Node Execution

#### `record_node_start(run_id, node, prompt, agent_id) -> int`

Record the start of a node execution.

```python
from conductor import Node, NodeType

node = Node(
    id="analyze",
    name="Analyze Bug",
    node_type=NodeType.SINGLE,
    prompt_template="Analyze {bug_description}",
    config={"agent_type": "Analyst"}
)

exec_id = conductor.record_node_start(
    run_id=123,
    node=node,
    prompt="Analyze login failure bug",
    agent_id="analyst-001"
)
```

**Returns:** Execution ID (int)

Creates a record in `node_executions` table and updates run node count.

#### `record_node_completion(exec_id, result_text, result_dict, findings, files_modified, duration_ms, token_count)`

Record successful completion of a node execution.

```python
conductor.record_node_completion(
    exec_id=456,
    result_text="Found null pointer in LoginController.validate()",
    result_dict={
        "issue": "null_pointer",
        "location": "LoginController.java:45"
    },
    findings=[
        {
            "type": "blocker",
            "content": "Null check missing on user object",
            "importance": "critical"
        }
    ],
    files_modified=["LoginController.java"],
    duration_ms=5432,
    token_count=1250
)
```

**Parameters:**

- `exec_id` (int): Execution record ID
- `result_text` (str): Human-readable result
- `result_dict` (Dict): Structured result data
- `findings` (List[Dict]): Discovered findings
- `files_modified` (List[str]): Modified file paths
- `duration_ms` (int): Execution time in milliseconds
- `token_count` (int): Tokens used

#### `record_node_failure(exec_id, error_message, error_type, duration_ms)`

Record failure of a node execution.

```python
conductor.record_node_failure(
    exec_id=456,
    error_message="Timeout waiting for agent response",
    error_type="timeout",
    duration_ms=300000
)
```

**Parameters:**

- `exec_id` (int): Execution record ID
- `error_message` (str): Error description
- `error_type` (str): Error category ("error", "timeout", "validation_error")
- `duration_ms` (int): Time before failure

#### `get_node_executions(run_id) -> List[Dict]`

Get all node executions for a run.

```python
executions = conductor.get_node_executions(123)

# Returns:
[
    {
        "id": 456,
        "run_id": 123,
        "node_id": "analyze",
        "node_name": "Analyze Bug",
        "node_type": "single",
        "agent_id": "analyst-001",
        "prompt": "Analyze login failure bug",
        "status": "completed",
        "result_text": "...",
        "result": {"issue": "null_pointer", ...},
        "findings": [{...}, ...],
        "files_modified": ["LoginController.java"],
        "duration_ms": 5432,
        "token_count": 1250,
        "started_at": "2025-12-11T10:30:00",
        "completed_at": "2025-12-11T10:30:05"
    },
    ...
]
```

### Edge Conditions

Edges support conditional traversal based on context:

```python
{
    "from_node": "analyze",
    "to_node": "fix",
    "condition": "context.get('severity') == 'critical'"
}
```

**Supported Syntax:**

```python
# Simple boolean
"true"
"false"

# Context membership
"'key' in context"
"'key' not in context"

# Comparisons (==, !=, >, <, >=, <=)
"context.get('severity') == 'critical'"
"context['count'] > 10"
"context.get('confidence') >= 0.8"
```

**Safe Evaluation:**

Conditions are evaluated via `safe_eval_condition()` which:
- Uses regex matching (no `eval()`)
- Supports only whitelisted operations
- Returns `False` on parse errors
- Prevents code injection

---

## Blackboard Communication

The Conductor bridges SQLite persistence with real-time Blackboard coordination.

### Syncing Findings

#### `sync_findings_to_blackboard(run_id)`

Sync findings from SQLite to blackboard for real-time access.

```python
conductor.sync_findings_to_blackboard(run_id=123)
```

**Workflow:**

1. Get all node executions for run
2. For each completed execution:
   - Extract findings from result
   - Add to blackboard via `blackboard.add_finding()`

**Finding Format:**

```python
blackboard.add_finding(
    agent_id="analyst-001",
    finding_type="blocker",
    content="Null check missing on user object",
    files=["LoginController.java"],
    importance="critical",
    tags=["null-pointer", "authentication"]
)
```

### Syncing Trails

#### `sync_trails_to_blackboard(run_id)`

Convert pheromone trails to blackboard findings for agent visibility.

```python
conductor.sync_trails_to_blackboard(run_id=123)
```

**Workflow:**

1. Get hot spots (top 10 trail locations)
2. For each hot spot:
   - Create blackboard finding with trail metadata
   - Set importance based on total strength

**Finding Content:**

```
Hot spot: src/auth/LoginController.java (15 trails, scents: discovery,warning,blocker)
```

---

## Pheromone Trails

Swarm intelligence hotspot tracking inspired by ant colony optimization.

### Laying Trails

#### `lay_trail(run_id, location, scent, strength, agent_id, node_id, message, tags, ttl_hours)`

Lay a pheromone trail at a location.

```python
conductor.lay_trail(
    run_id=123,
    location="src/auth/LoginController.java",
    scent="blocker",
    strength=0.9,
    agent_id="fixer-002",
    node_id="fix-bug",
    message="Critical null pointer found",
    tags=["authentication", "null-safety"],
    ttl_hours=48
)
```

**Parameters:**

- `run_id` (int): Workflow run ID
- `location` (str): File path, function name, or concept
- `scent` (str): Trail type (see [Scent Types](#scent-types))
- `strength` (float): Trail strength 0.0-1.0
- `agent_id` (str): Agent that laid the trail
- `node_id` (str): Node that laid the trail
- `message` (str): Optional description
- `tags` (List[str]): Optional tags
- `ttl_hours` (int): Hours until trail expires (default: 24)

#### Scent Types

- `discovery`: New finding or insight
- `warning`: Potential issue detected
- `blocker`: Critical problem blocking progress
- `hot`: High activity area (multiple visits)
- `cold`: Low activity area (abandoned)
- `read`: File was read/examined
- `write`: File was modified

### Querying Trails

#### `get_trails(location, scent, min_strength, run_id, include_expired) -> List[Dict]`

Get pheromone trails matching criteria.

```python
trails = conductor.get_trails(
    location="LoginController",  # Substring match
    scent="blocker",
    min_strength=0.5,
    run_id=123,
    include_expired=False
)

# Returns:
[
    {
        "id": 789,
        "run_id": 123,
        "location": "src/auth/LoginController.java",
        "scent": "blocker",
        "strength": 0.9,
        "agent_id": "fixer-002",
        "node_id": "fix-bug",
        "message": "Critical null pointer found",
        "tags": "authentication,null-safety",
        "created_at": "2025-12-11T10:30:00",
        "expires_at": "2025-12-13T10:30:00"
    },
    ...
]
```

**Parameters:**

- `location` (Optional[str]): Filter by location (substring match)
- `scent` (Optional[str]): Filter by scent type
- `min_strength` (float): Minimum trail strength (default: 0.0)
- `run_id` (Optional[int]): Filter by workflow run
- `include_expired` (bool): Include expired trails (default: False)

**Returns:** List of up to 100 trails, ordered by strength DESC, created_at DESC

#### `get_hot_spots(run_id, limit) -> List[Dict]`

Get locations with the most trail activity.

```python
hot_spots = conductor.get_hot_spots(run_id=123, limit=20)

# Returns:
[
    {
        "location": "src/auth/LoginController.java",
        "trail_count": 15,
        "max_strength": 0.95,
        "total_strength": 8.7,
        "scents": "discovery,warning,blocker",
        "agents": "scout-001,analyzer-002,fixer-003",
        "last_activity": "2025-12-11T10:35:00"
    },
    ...
]
```

**Parameters:**

- `run_id` (Optional[int]): Filter by workflow run
- `limit` (int): Max results (default: 20)

**Returns:** Aggregated trail data grouped by location, ordered by total_strength DESC

### Trail Decay

#### `decay_trails(decay_rate)`

Decay all trail strengths by a percentage.

```python
# Reduce all trail strengths by 10%
conductor.decay_trails(decay_rate=0.1)
```

**Workflow:**

1. Multiply all non-expired trail strengths by `(1.0 - decay_rate)`
2. Delete trails with strength < 0.01

This simulates pheromone evaporation over time, allowing old trails to fade.

---

## Decision Logging

The Conductor logs all decisions for audit and analysis.

### Recording Decisions

Decisions are logged automatically:

```python
# When starting a run
conductor.start_run(...)
# Logs: {"decision_type": "start_run", "data": {"workflow_name": "...", "phase": "..."}}

# When changing phase
conductor.update_run_phase(run_id, "synthesis")
# Logs: {"decision_type": "phase_change", "data": {"new_phase": "synthesis"}}

# When firing a node
conductor.record_node_start(...)
# Logs: {"decision_type": "fire_node", "data": {"node_id": "...", "node_name": "..."}}

# When node fails
conductor.record_node_failure(...)
# Logs: {"decision_type": "node_failed", "data": {"error_type": "...", "error_message": "..."}}
```

### Querying Decisions

#### `get_decisions(run_id) -> List[Dict]`

Get all decisions for a workflow run.

```python
decisions = conductor.get_decisions(123)

# Returns:
[
    {
        "id": 1,
        "run_id": 123,
        "decision_type": "start_run",
        "data": {
            "workflow_name": "bug-investigation",
            "phase": "init"
        },
        "reason": "Workflow run started",
        "created_at": "2025-12-11T10:30:00"
    },
    {
        "id": 2,
        "decision_type": "fire_node",
        "data": {
            "node_id": "scout",
            "node_name": "Scout Phase",
            "node_type": "swarm",
            "execution_id": 456
        },
        "reason": "Started node: Scout Phase",
        "created_at": "2025-12-11T10:30:01"
    },
    ...
]
```

**Decision Types:**

- `start_run`: Workflow started
- `phase_change`: Phase transition
- `fire_node`: Node execution started
- `node_failed`: Node execution failed

---

## Examples

### Example 1: Simple Linear Workflow

```python
from conductor import Conductor

conductor = Conductor()

# Create workflow
workflow_id = conductor.create_workflow(
    name="simple-analysis",
    description="Single-agent linear workflow",
    nodes=[
        {
            "id": "read",
            "name": "Read Codebase",
            "node_type": "single",
            "prompt_template": "Read files in {directory}",
            "config": {"agent_type": "Explorer"}
        },
        {
            "id": "analyze",
            "name": "Analyze Code",
            "node_type": "single",
            "prompt_template": "Analyze the code for {issue_type}",
            "config": {"agent_type": "Analyst"}
        },
        {
            "id": "report",
            "name": "Generate Report",
            "node_type": "single",
            "prompt_template": "Generate report on findings",
            "config": {"agent_type": "Reporter"}
        }
    ],
    edges=[
        {"from_node": "__start__", "to_node": "read"},
        {"from_node": "read", "to_node": "analyze"},
        {"from_node": "analyze", "to_node": "report"},
        {"from_node": "report", "to_node": "__end__"}
    ]
)

# Execute workflow
from executor import CLIExecutor

executor = CLIExecutor()
conductor.set_node_executor(executor.execute)

run_id = conductor.run_workflow(
    workflow_name="simple-analysis",
    input_data={
        "directory": "src/",
        "issue_type": "security vulnerabilities"
    }
)

# Check results
run = conductor.get_run(run_id)
print(f"Status: {run['status']}")
print(f"Output: {run['output']}")
```

### Example 2: Conditional Branching

```python
workflow_id = conductor.create_workflow(
    name="conditional-fix",
    description="Fix bugs conditionally based on severity",
    nodes=[
        {
            "id": "detect",
            "name": "Detect Bug",
            "node_type": "single",
            "prompt_template": "Analyze bug: {bug_description}",
            "config": {"agent_type": "Detector"}
        },
        {
            "id": "auto-fix",
            "name": "Auto Fix",
            "node_type": "single",
            "prompt_template": "Automatically fix the bug",
            "config": {"agent_type": "Fixer"}
        },
        {
            "id": "escalate",
            "name": "Escalate to Human",
            "node_type": "single",
            "prompt_template": "Prepare escalation report",
            "config": {"agent_type": "Reporter"}
        }
    ],
    edges=[
        {"from_node": "__start__", "to_node": "detect"},
        {
            "from_node": "detect",
            "to_node": "auto-fix",
            "condition": "context.get('severity') == 'low'"
        },
        {
            "from_node": "detect",
            "to_node": "escalate",
            "condition": "context.get('severity') == 'critical'"
        },
        {"from_node": "auto-fix", "to_node": "__end__"},
        {"from_node": "escalate", "to_node": "__end__"}
    ]
)

# Execute - will branch based on detected severity
run_id = conductor.run_workflow(
    workflow_name="conditional-fix",
    input_data={"bug_description": "Null pointer in login"}
)
```

### Example 3: Parallel Analysis

```python
workflow_id = conductor.create_workflow(
    name="parallel-review",
    description="Multi-perspective code review",
    nodes=[
        {
            "id": "parallel-review",
            "name": "Multiple Reviews",
            "node_type": "parallel",
            "prompt_template": "Review the codebase",
            "config": {
                "agent_type": "Reviewer",
                "prompts": [
                    "Review for security vulnerabilities",
                    "Review for performance issues",
                    "Review for code quality and maintainability",
                    "Review for test coverage"
                ]
            }
        },
        {
            "id": "synthesize",
            "name": "Synthesize Reviews",
            "node_type": "single",
            "prompt_template": "Synthesize all review findings",
            "config": {"agent_type": "Synthesizer"}
        }
    ],
    edges=[
        {"from_node": "__start__", "to_node": "parallel-review"},
        {"from_node": "parallel-review", "to_node": "synthesize"},
        {"from_node": "synthesize", "to_node": "__end__"}
    ]
)

run_id = conductor.run_workflow("parallel-review", input_data={})
```

### Example 4: Swarm Investigation

```python
workflow_id = conductor.create_workflow(
    name="swarm-bug-hunt",
    description="Multi-agent swarm for bug investigation",
    nodes=[
        {
            "id": "scout-phase",
            "name": "Scout Phase",
            "node_type": "swarm",
            "prompt_template": "Investigate bug: {bug_description}",
            "config": {
                "num_ants": 5,
                "roles": ["scout", "analyzer", "tester", "reviewer", "fixer"],
                "agent_type": "Explore"
            }
        },
        {
            "id": "analyze-trails",
            "name": "Analyze Trails",
            "node_type": "single",
            "prompt_template": "Analyze hot spots from swarm exploration",
            "config": {"agent_type": "Analyst"}
        },
        {
            "id": "focused-fix",
            "name": "Focused Fix",
            "node_type": "single",
            "prompt_template": "Fix the bug based on hot spot analysis",
            "config": {"agent_type": "Fixer"}
        }
    ],
    edges=[
        {"from_node": "__start__", "to_node": "scout-phase"},
        {"from_node": "scout-phase", "to_node": "analyze-trails"},
        {"from_node": "analyze-trails", "to_node": "focused-fix"},
        {"from_node": "focused-fix", "to_node": "__end__"}
    ]
)

# Execute swarm
run_id = conductor.run_workflow(
    workflow_name="swarm-bug-hunt",
    input_data={"bug_description": "Login fails intermittently"}
)

# Check hot spots
hot_spots = conductor.get_hot_spots(run_id, limit=10)
for spot in hot_spots:
    print(f"{spot['location']}: {spot['trail_count']} trails, strength {spot['total_strength']}")
```

### Example 5: Trail-Based Coordination

```python
from conductor import Conductor

conductor = Conductor()
run_id = 123  # Existing run

# Ant lays discovery trail
conductor.lay_trail(
    run_id=run_id,
    location="src/auth/LoginController.java:45",
    scent="discovery",
    strength=0.7,
    agent_id="scout-001",
    message="Found null pointer vulnerability",
    tags=["null-safety", "critical"]
)

# Another ant reinforces the trail
conductor.lay_trail(
    run_id=run_id,
    location="src/auth/LoginController.java:45",
    scent="blocker",
    strength=0.9,
    agent_id="analyzer-002",
    message="Confirmed: null check missing",
    tags=["null-safety", "critical"]
)

# Query trails at this location
trails = conductor.get_trails(
    location="LoginController.java:45",
    run_id=run_id
)

print(f"Total trails: {len(trails)}")
print(f"Total strength: {sum(t['strength'] for t in trails)}")

# Get hot spots
hot_spots = conductor.get_hot_spots(run_id)
print(f"Top hot spot: {hot_spots[0]['location']}")
print(f"  {hot_spots[0]['trail_count']} trails")
print(f"  Scents: {hot_spots[0]['scents']}")
print(f"  Agents: {hot_spots[0]['agents']}")
```

### Example 6: Custom Executor

```python
from conductor import Conductor, Node

def my_custom_executor(node: Node, context: dict) -> tuple:
    """Custom execution logic."""
    print(f"Executing: {node.name}")

    # Your execution logic here
    # Could integrate with external APIs, custom agents, etc.

    result_text = f"Completed {node.name}"
    result_dict = {
        "findings": [
            {
                "type": "discovery",
                "content": "Custom finding",
                "importance": "normal"
            }
        ],
        "files_modified": [],
        "custom_data": {"key": "value"}
    }

    return result_text, result_dict

conductor = Conductor()
conductor.set_node_executor(my_custom_executor)

# Now all nodes will use your custom executor
run_id = conductor.run_workflow("my-workflow", input_data={})
```

---

## CLI Usage

The Conductor provides a command-line interface:

### List Workflows

```bash
python ~/.claude/emergent-learning/src/conductor/conductor.py list

# Output:
# Workflows:
#   - bug-investigation: Multi-agent bug investigation workflow
#   - code-review: Parallel code review workflow
```

### Show Workflow

```bash
python ~/.claude/emergent-learning/src/conductor/conductor.py show bug-investigation

# Output: JSON workflow definition
```

### Show Run

```bash
python ~/.claude/emergent-learning/src/conductor/conductor.py run 123

# Output:
# {
#   "id": 123,
#   "workflow_name": "bug-investigation",
#   "status": "completed",
#   ...
# }
#
# Node Executions:
#   ✓ Scout Phase (completed)
#   ✓ Analyze Findings (completed)
#   ✗ Fix Bug (failed)
```

### Show Hot Spots

```bash
python ~/.claude/emergent-learning/src/conductor/conductor.py hotspots --run-id 123 --limit 10

# Output:
# Hot Spots (by trail activity):
#   src/auth/LoginController.java
#     Trails: 15, Strength: 8.70
#     Scents: discovery,warning,blocker
```

---

## Best Practices

### Workflow Design

1. **Start simple**: Begin with linear workflows before adding complexity
2. **Use descriptive IDs**: `"analyze-auth"` better than `"node1"`
3. **Limit branching**: Too many conditional edges make workflows hard to debug
4. **Document nodes**: Use clear `name` and `description` fields

### Node Configuration

1. **Choose appropriate types**:
   - `single`: One focused task
   - `parallel`: Independent tasks that can run concurrently
   - `swarm`: Exploratory tasks needing multiple perspectives
2. **Set timeouts**: Configure execution timeouts in node config
3. **Use context variables**: Parameterize prompts with `{variable}` syntax

### Swarm Coordination

1. **Diverse roles**: Use different roles for different perspectives
2. **Right-size swarms**: 3-5 ants is usually sufficient
3. **Standardize findings**: Use consistent finding format
4. **Analyze trails**: Use `get_hot_spots()` to find convergence

### Trail Management

1. **Meaningful scents**: Choose scents that match finding types
2. **Appropriate strength**: High strength (0.8-1.0) for critical findings
3. **Decay regularly**: Call `decay_trails()` to remove stale trails
4. **Set TTL**: Use reasonable expiration times (24-48 hours)

### Performance

1. **Limit trail queries**: Use filters to reduce result sets
2. **Batch operations**: Group database operations when possible
3. **Monitor execution times**: Track `duration_ms` for optimization
4. **Clean up runs**: Archive or delete old runs periodically

---

## See Also

- [Hook API](./Hooks.md) - Hook development and security verification
- [Validation Utilities](../../src/conductor/validation.py) - Input validation for security
- [Blackboard Documentation](../../coordinator/README.md) - Real-time coordination
