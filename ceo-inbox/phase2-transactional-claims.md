# Phase 2: Transactional File Claims with Dependency Graph

**Created:** 2025-12-08
**Priority:** HIGH
**Status:** SPEC READY

## Problem

Current coordination is opt-in. Agents CAN claim files but nothing enforces it. Result: agents can still edit interdependent files without coordination → broken imports, interface mismatches.

## Solution: Transactional Claim Chains

### Core Concept

```
Agent claims a CHAIN of related files atomically.
System enforces: no other agent can touch ANY file in the chain.
Dependency graph helps agents discover what to claim.
```

### Components

#### 1. Dependency Graph Builder (`dependency_graph.py`)

```python
class DependencyGraph:
    def __init__(self, project_root: str):
        self.root = project_root
        self.graph = {}  # file -> set of files it depends on
        self.reverse = {}  # file -> set of files that depend on it
    
    def scan(self):
        """Scan project, build import/include graph"""
        # Python: parse imports
        # JS/TS: parse imports/requires
        # Rust: parse use/mod
        # etc.
    
    def get_dependencies(self, file: str) -> Set[str]:
        """What does this file import?"""
        
    def get_dependents(self, file: str) -> Set[str]:
        """What files import this file?"""
    
    def get_cluster(self, file: str, depth: int = 2) -> Set[str]:
        """Get file + dependencies + dependents up to depth"""
        
    def suggest_chain(self, files: List[str]) -> List[str]:
        """Given files agent wants, suggest full chain needed"""
```

#### 2. Claim Chain System (`blackboard.py` extension)

```python
@dataclass
class ClaimChain:
    chain_id: str
    agent_id: str
    files: Set[str]
    reason: str
    claimed_at: datetime
    expires_at: datetime
    status: str  # active, completed, expired, released

class Blackboard:
    def claim_chain(
        self, 
        agent_id: str, 
        files: List[str],
        reason: str = "",
        ttl_minutes: int = 30
    ) -> Result[ClaimChain, BlockedError]:
        """
        Atomically claim all files or fail.
        Returns BlockedError with details if any file is taken.
        """
        
    def release_chain(self, agent_id: str, chain_id: str):
        """Release all files in chain"""
        
    def get_blocking_chains(self, files: List[str]) -> List[ClaimChain]:
        """What chains block these files?"""
        
    def wait_for_files(
        self, 
        agent_id: str, 
        files: List[str],
        timeout: int = 300
    ) -> bool:
        """Block until files available or timeout"""
```

#### 3. Enforcement Hook (`hooks/enforce_claims.py`)

```python
def pre_tool_use(tool_name: str, tool_input: dict) -> HookResult:
    """Intercept Edit/Write, enforce claims"""
    
    if tool_name not in ["Edit", "Write"]:
        return HookResult.allow()
    
    file_path = tool_input.get("file_path")
    agent_id = get_current_agent_id()
    
    # Check if file is in an active chain for this agent
    bb = Blackboard()
    claim = bb.get_claim_for_file(file_path)
    
    if claim is None:
        return HookResult.deny(
            f"File not claimed. Run: claim_chain(['{file_path}', ...])"
        )
    
    if claim.agent_id != agent_id:
        return HookResult.deny(
            f"File claimed by {claim.agent_id}: {claim.reason}\n"
            f"Expires: {claim.expires_at}"
        )
    
    return HookResult.allow()
```

#### 4. Agent Workflow

```
1. Agent starts task
2. Agent queries: "What files will I need to modify?"
3. Agent asks dependency graph: "What else is connected?"
   → graph.suggest_chain(["auth.py"]) 
   → ["auth.py", "user.py", "test_auth.py", "conftest.py"]
4. Agent claims chain atomically
5. If blocked: wait or pick different task
6. Agent works on files
7. Agent releases chain on completion
```

### API Examples

```python
# Agent discovers dependencies
graph = DependencyGraph("/project")
graph.scan()

# "I want to edit auth.py, what else should I claim?"
cluster = graph.get_cluster("src/auth.py", depth=2)
# Returns: {"src/auth.py", "src/user.py", "src/models.py", "tests/test_auth.py"}

# Claim the chain
bb = Blackboard()
result = bb.claim_chain(
    agent_id="agent-123",
    files=list(cluster),
    reason="Refactoring authentication flow"
)

if result.is_error():
    print(f"Blocked by: {result.error.blocking_agent}")
    print(f"Files in conflict: {result.error.conflicting_files}")
    # Either wait or do something else

# Work on files...

# Release when done
bb.release_chain("agent-123", result.chain_id)
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| Deadlock (A waits for B, B waits for A) | TTL expiration + priority queue |
| Agent crashes without releasing | Auto-expire after TTL |
| Agent needs MORE files mid-chain | Extend chain (atomic) or release and reclaim |
| Conflicting chains overlap | First claim wins, others queue |
| Emergency override | CEO/human can force-release |

### Language Support for Dependency Graph

| Language | Parse Method |
|----------|--------------|
| Python | `ast.parse()` → find Import/ImportFrom |
| JavaScript/TS | Regex or `@babel/parser` |
| Rust | Regex for `use`/`mod` statements |
| Go | Regex for `import` blocks |
| Generic | File mentions in comments/strings |

### Implementation Order

1. **MVP:** Manual chain claiming (no auto-graph) + enforcement hook
2. **v1.1:** Python dependency graph
3. **v1.2:** Multi-language graph support
4. **v1.3:** Smart suggestions ("You edited X, should also update Y")

### Files to Create/Modify

```
coordinator/
  dependency_graph.py    # NEW - graph builder
  blackboard.py          # EXTEND - add claim_chain methods
  
hooks/
  enforce_claims.py      # NEW - pre-tool hook

scripts/
  scan-deps.sh           # NEW - CLI to scan project deps
  
tests/
  test_dependency_graph.py
  test_claim_chains.py
```

### Success Criteria

- [ ] Agent cannot edit file without claiming it first
- [ ] Claim chains are atomic (all or nothing)
- [ ] Dependency graph suggests related files
- [ ] Blocked agents see clear message with who/why/when
- [ ] Chains auto-expire to prevent deadlocks
- [ ] Works across async parallel agents

---

## Estimated Scope

- dependency_graph.py: ~200 lines
- blackboard.py extensions: ~150 lines
- enforce_claims.py hook: ~50 lines
- Tests: ~200 lines

**Total: ~600 lines of code**

This is a weekend project that permanently solves file coordination.
