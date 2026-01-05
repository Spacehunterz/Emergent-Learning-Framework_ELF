# Extension Development Guide

**Last Updated:** 2026-01-05
**Audience:** Developers
**Difficulty:** Advanced

---

## Overview

The Emergent Learning Framework is designed to be extensible. This guide covers how to extend ELF with custom components:

1. Custom Hooks
2. Custom Query Mixins
3. Custom Agent Personas
4. Dashboard Plugins

---

## 1. Custom Hooks

Hooks intercept Claude Code tool operations to inject learning behavior.

### Hook Types

| Hook Type | Trigger | Purpose |
|-----------|---------|---------|
| `pre_tool` | Before tool execution | Load context, check patterns |
| `post_tool` | After tool execution | Validate outcomes, log learnings |
| `user_prompt` | User prompt submission | Inject context into prompts |

### Creating a Custom Hook

**Location:** `src/hooks/your-hook-name/`

**Required Files:**
```
src/hooks/your-hook-name/
├── __init__.py
├── your_hook.py          # Main hook logic
└── manifest.json         # Hook metadata
```

**manifest.json:**
```json
{
  "name": "your-hook-name",
  "version": "1.0.0",
  "hook_type": "post_tool",
  "entry_point": "your_hook.py",
  "enabled": true
}
```

**your_hook.py:**
```python
import json
import sys
from pathlib import Path
from datetime import datetime

def handle_hook(event_data: dict) -> dict:
    """
    Process the hook event.

    Args:
        event_data: Contains tool_name, input, output, etc.

    Returns:
        dict with 'continue': bool and optional 'message': str
    """
    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input", {})
    tool_output = event_data.get("tool_output", "")

    # Your custom logic here
    result = process_event(tool_name, tool_input, tool_output)

    return {
        "continue": True,  # Always True for advisory hooks
        "message": result.get("message")
    }

def process_event(tool_name: str, tool_input: dict, tool_output: str) -> dict:
    # Implement your logic
    return {"message": None}

if __name__ == "__main__":
    event_data = json.loads(sys.stdin.read())
    result = handle_hook(event_data)
    print(json.dumps(result))
```

### Registering Hooks

Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "post_tool_call": [
      {
        "command": "python",
        "args": ["src/hooks/your-hook-name/your_hook.py"]
      }
    ]
  }
}
```

### Hook Best Practices

1. **Never block** - Return `{"continue": true}` always
2. **Fail gracefully** - Catch exceptions, log, continue
3. **Be fast** - Hooks run synchronously, keep <100ms
4. **Log to building** - Use the learning storage, not stdout

---

## 2. Custom Query Mixins

Query mixins add new query methods to QuerySystem.

### Creating a Mixin

**Location:** `src/query/your_queries.py`

```python
from typing import List, Optional
from datetime import datetime

class YourQueryMixin:
    """Mixin for your custom queries."""

    async def query_your_data(
        self,
        filter_param: str,
        limit: int = 50
    ) -> List[dict]:
        """
        Query your custom data.

        Args:
            filter_param: Filter criteria
            limit: Max results (1-1000)

        Returns:
            List of matching records
        """
        manager = await self._get_manager()

        query = """
            SELECT * FROM your_table
            WHERE column LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """

        results = await manager.execute_query(
            query,
            (f"%{filter_param}%", limit)
        )

        return [dict(row) for row in results]

    async def record_your_data(
        self,
        data: dict
    ) -> int:
        """
        Store custom data.

        Returns:
            ID of inserted record
        """
        manager = await self._get_manager()

        query = """
            INSERT INTO your_table (column1, column2, created_at)
            VALUES (?, ?, ?)
        """

        result = await manager.execute_query(
            query,
            (data["col1"], data["col2"], datetime.now().isoformat())
        )

        return result.lastrowid
```

### Registering the Mixin

In `src/query/core.py`, add to the QuerySystem class inheritance:

```python
from query.your_queries import YourQueryMixin

class QuerySystem(
    BaseQueryMixin,
    HeuristicQueryMixin,
    LearningQueryMixin,
    YourQueryMixin,  # Add your mixin
    # ... other mixins
):
    pass
```

### Mixin Best Practices

1. **Async only** - All methods must be `async def`
2. **Use manager** - Get via `await self._get_manager()`
3. **Validate inputs** - Use validators from `validators.py`
4. **Return typed data** - Use dataclasses or typed dicts

---

## 3. Custom Agent Personas

Agent personas define how the multi-perspective analysis works.

### Creating a Persona

**Location:** `agents/your-persona/personality.md`

```markdown
# Your Persona Name

## Role
[One sentence describing what this persona does]

## Perspective
[How this persona approaches problems]

## Questions This Persona Asks
- Question 1?
- Question 2?
- Question 3?

## Strengths
- Strength 1
- Strength 2

## Weaknesses
- Weakness 1
- Weakness 2

## When to Use
Use this persona when:
- Scenario 1
- Scenario 2

## Example Analysis
Given a [type of problem], this persona would:
1. First, [approach]
2. Then, [analysis]
3. Finally, [recommendation]
```

### Using Custom Personas

Reference in failure analysis or decision making:
```markdown
## Agent Analysis

**Your Persona:** [Analysis from your persona's perspective]

**Researcher:** [Existing persona analysis]

**Architect:** [Existing persona analysis]

## Synthesis
[Combined insights]
```

---

## 4. Dashboard Plugins

Extend the React dashboard with custom components.

### Component Structure

**Location:** `apps/dashboard/frontend/src/plugins/your-plugin/`

```
your-plugin/
├── index.tsx           # Main export
├── YourComponent.tsx   # React component
├── useYourHook.ts      # Custom hook
└── types.ts            # TypeScript types
```

**YourComponent.tsx:**
```tsx
import React from 'react'
import { useAPI } from '../../hooks/useAPI'

interface YourPluginProps {
  title?: string
}

export function YourPlugin({ title = "My Plugin" }: YourPluginProps) {
  const { api } = useAPI()
  const [data, setData] = React.useState<YourData[]>([])

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.get('/api/your-endpoint')
        setData(result)
      } catch (err) {
        console.error('Failed to fetch:', err)
      }
    }
    fetchData()
  }, [api])

  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <h2 className="text-xl font-bold mb-4">{title}</h2>
      {/* Your UI */}
    </div>
  )
}
```

### Adding Backend Endpoints

**Location:** `apps/dashboard/backend/routers/your_router.py`

```python
from fastapi import APIRouter
from ..utils.database import get_db

router = APIRouter(prefix="/api/your-endpoint", tags=["your-plugin"])

@router.get("")
async def get_your_data():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM your_table LIMIT 100")
        return [dict(row) for row in cursor.fetchall()]

@router.post("")
async def create_your_data(data: YourModel):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO your_table (col1, col2) VALUES (?, ?)",
            (data.col1, data.col2)
        )
        conn.commit()
        return {"id": cursor.lastrowid}
```

Register in `apps/dashboard/backend/main.py`:
```python
from routers.your_router import router as your_router
app.include_router(your_router)
```

### Adding to Dashboard Tabs

In `apps/dashboard/frontend/src/App.tsx`, add to tabs array:
```tsx
import { YourPlugin } from './plugins/your-plugin'

// In the tabs section:
{activeTab === 'your-plugin' && <YourPlugin />}
```

---

## Testing Extensions

### Hook Tests
```bash
# Test hook independently
echo '{"tool_name": "Write", "tool_input": {"path": "test.py"}}' | \
  python src/hooks/your-hook-name/your_hook.py
```

### Query Mixin Tests
```python
# tests/test_your_queries.py
import pytest
from src.query.core import QuerySystem

@pytest.mark.asyncio
async def test_your_query():
    qs = await QuerySystem.create()
    try:
        results = await qs.query_your_data("test")
        assert isinstance(results, list)
    finally:
        await qs.cleanup()
```

### Dashboard Tests
```bash
# Run Playwright tests
cd apps/dashboard
npx playwright test your-plugin.spec.ts
```

---

## Extension Checklist

Before deploying an extension:

- [ ] Hook returns `{"continue": true}` always
- [ ] All async methods properly awaited
- [ ] Input validation in place
- [ ] Error handling with graceful fallbacks
- [ ] Tests written and passing
- [ ] No external API dependencies (per golden rules)
- [ ] Documentation in place

---

## See Also

- [API Reference](../api/index.md) - Core API documentation
- [Testing Guide](testing.md) - How to test extensions
- [Architecture](../architecture/per-project-architecture.md) - System design
