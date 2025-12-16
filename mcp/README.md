# ELF MCP Server

Exposes the Emergent Learning Framework to external tools via Model Context Protocol.

## Requirements

- Python 3.10+ with MCP SDK installed: `pip install mcp`
- The `peewee-aio` package for async database access

## Registration

```bash
claude mcp add ELF_FLOW_MCP python3.13 ~/.claude/emergent-learning/mcp/elf_server.py
```

**Note:** Use Python 3.13 (not 3.14) - the MCP SDK has compatibility issues with Python 3.14.

Or add to your Claude configuration:

```json
{
  "mcpServers": {
    "ELF_FLOW_MCP": {
      "command": "python3.13",
      "args": ["~/.claude/emergent-learning/mcp/elf_server.py"]
    }
  }
}
```

## Available Tools

### `elf_query`
Query the building for context (golden rules, heuristics, learnings).

**Parameters:**
- `domain` (optional): Focus on a specific domain
- `depth`: `minimal` | `standard` | `deep`
- `max_tokens`: Maximum tokens to return (default: 5000)

**Example:**
```json
{
  "domain": "react",
  "depth": "standard",
  "max_tokens": 3000
}
```

### `elf_record_heuristic`
Record a new heuristic (rule of thumb) discovered during work.

**Parameters:**
- `domain` (required): Domain for the heuristic
- `rule` (required): The heuristic statement
- `explanation`: Why this heuristic works
- `source`: `failure` | `success` | `observation`
- `confidence`: 0.0 to 1.0

**Example:**
```json
{
  "domain": "react",
  "rule": "Always memoize callbacks passed to child components",
  "explanation": "Prevents unnecessary re-renders in child components",
  "source": "observation",
  "confidence": 0.8
}
```

### `elf_record_failure`
Record a failure for future learning.

**Parameters:**
- `title` (required): Brief description
- `domain` (required): Domain where failure occurred
- `summary` (required): What happened and what was learned
- `severity`: 1-5 (default: 3)
- `tags`: Comma-separated tags

**Example:**
```json
{
  "title": "WebSocket reconnect loop",
  "domain": "react",
  "summary": "useEffect with callback dependencies caused infinite reconnects",
  "severity": 4,
  "tags": "websocket,hooks,bug"
}
```

### `elf_ceo_inbox`
Check pending decisions in the CEO inbox.

**Parameters:** None

**Returns:** List of pending items with status, priority, and summary.

### `elf_search`
Search the knowledge base.

**Parameters:**
- `query` (required): Search query
- `domain` (optional): Filter by domain
- `limit`: Max results (default: 10)

**Example:**
```json
{
  "query": "git commit",
  "domain": "git",
  "limit": 5
}
```

## Integration with Claude-Flow

1. Claude-flow pre-task hook: `elf_query(depth="standard")`
2. Claude-flow post-task hook: `elf_record_heuristic()` for lessons learned
3. Golden rules from ELF are respected in all operations
4. ELF = "brain" (knowledge), Claude-flow = "nervous system" (orchestration)
