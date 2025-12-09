# Claim Chains Quick Reference

## What Are Claim Chains?

Transactional file claims that prevent concurrent edits to interdependent files. An agent must claim files before editing them, and the system ensures no other agent can touch those files until released.

## Quick Start

### 1. Find Related Files

```bash
python coordinator/dependency_graph.py cluster . src/auth.py 2
```

This shows files within 2 hops of `src/auth.py` in the dependency graph.

### 2. Claim Files

```python
from blackboard import Blackboard

bb = Blackboard(".")
chain = bb.claim_chain(
    agent_id="agent-123",
    files=["src/auth.py", "src/user.py", "tests/test_auth.py"],
    reason="Refactoring authentication flow",
    ttl_minutes=30  # Auto-expire after 30 min
)
```

### 3. Work on Files

Edit your files. The enforcement hook (when enabled) will prevent other agents from editing them.

### 4. Release When Done

```python
bb.release_chain("agent-123", chain.chain_id)
# or
bb.complete_chain("agent-123", chain.chain_id)
```

## API Reference

### Blackboard Methods

**claim_chain(agent_id, files, reason="", ttl_minutes=30)**
- Claims files atomically (all or nothing)
- Raises `BlockedError` if any file is already claimed
- Returns `ClaimChain` object

**release_chain(agent_id, chain_id)**
- Immediately releases a claim chain
- Returns `True` if successful

**complete_chain(agent_id, chain_id)**
- Marks chain as completed (also releases files)
- Returns `True` if successful

**get_claim_for_file(file_path)**
- Returns `ClaimChain` if file is claimed, `None` otherwise

**get_blocking_chains(files)**
- Returns list of chains that block any of the specified files

**get_agent_chains(agent_id)**
- Returns all chains owned by an agent

**get_all_active_chains()**
- Returns all currently active chains

### ClaimChain Object

```python
@dataclass
class ClaimChain:
    chain_id: str           # Unique identifier
    agent_id: str          # Agent that owns the chain
    files: Set[str]        # Files in this chain
    reason: str            # Why these files were claimed
    claimed_at: datetime   # When claimed
    expires_at: datetime   # When it auto-expires
    status: str            # active, completed, expired, released
```

### BlockedError Exception

```python
try:
    bb.claim_chain(...)
except BlockedError as e:
    print(e.blocking_chains)    # List of blocking ClaimChain objects
    print(e.conflicting_files)  # Set of file paths in conflict
```

## Dependency Graph

### Scan Project

```bash
python coordinator/dependency_graph.py scan .
```

Shows statistics about dependencies in the project.

### Get Dependencies

```bash
python coordinator/dependency_graph.py deps . coordinator/blackboard.py
```

Shows what files `blackboard.py` imports.

### Get Dependents

```bash
python coordinator/dependency_graph.py dependents . coordinator/blackboard.py
```

Shows what files import `blackboard.py`.

### Get Cluster

```bash
python coordinator/dependency_graph.py cluster . coordinator/blackboard.py 3
```

Shows all files within 3 hops (dependencies and dependents).

### Suggest Chain

```bash
python coordinator/dependency_graph.py suggest . file1.py file2.py
```

Given files you want to edit, suggests the complete chain to claim.

## Enforcement Hook

The `hooks/enforce_claims.py` hook can intercept Edit/Write tool calls to enforce claims.

When a file is not claimed:
```
WARNING: File not claimed: src/auth.py

You must claim this file before editing it.
...
```

When a file is claimed by another agent:
```
WARNING: File claimed by another agent: src/auth.py

Claimed by: agent-456
Reason: Updating authentication
Chain ID: abc123...
Expires at: 2025-12-08 18:30:00 (TTL: 25.3 min)
...
```

## Best Practices

1. **Always claim dependencies together** - Use dependency graph to find related files
2. **Use descriptive reasons** - Help other agents understand what you're doing
3. **Set appropriate TTL** - Default is 30 min; adjust based on task complexity
4. **Release when done** - Don't hold claims longer than necessary
5. **Check for conflicts first** - Use `get_blocking_chains()` before claiming

## Example Workflow

```python
from coordinator.dependency_graph import DependencyGraph
from coordinator.blackboard import Blackboard, BlockedError

# 1. Discover dependencies
dg = DependencyGraph(".")
dg.scan()
files_to_claim = dg.suggest_chain(["src/auth.py"])

# 2. Claim the chain
bb = Blackboard(".")
try:
    chain = bb.claim_chain(
        agent_id="my-agent",
        files=files_to_claim,
        reason="Implementing OAuth2 support"
    )
    print(f"Claimed {len(chain.files)} files")
except BlockedError as e:
    print(f"Blocked by: {[c.agent_id for c in e.blocking_chains]}")
    # Either wait or do something else
    exit(1)

# 3. Do your work
# ... edit files ...

# 4. Release
bb.complete_chain("my-agent", chain.chain_id)
print("Work complete, files released")
```

## Testing

Run the test suite:

```bash
pytest tests/test_claim_chains.py -v
```

All 19 tests should pass.
