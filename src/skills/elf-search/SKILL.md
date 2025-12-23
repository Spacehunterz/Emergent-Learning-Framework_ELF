---
name: search
description: Natural language search through Claude Code session history. Search for previous prompts, conversations, topics, file modifications, and context from past sessions. Useful for finding earlier work and understanding project continuity.
license: MIT
---

# ELF Session Search Command

Search through Claude Code session history using natural language queries.

## Purpose

The `/search` command helps you find:
- Previous prompts and conversations
- Work on specific topics
- Files modified in past sessions
- Context from earlier iterations
- Related discussions across sessions

## Usage Examples

```
/search what was my last prompt?
/search what was I working on yesterday?
/search find prompts about git
/search show me recent conversations
/search where did I edit the router?
```

## How It Works

When you invoke `/search`:

1. **Extract your query** from the command
2. **Search session logs** - Parse JSONL files from `~/.claude/projects/`
3. **Find matches** - Natural language matching against user messages
4. **Show results** - Display relevant prompts and context
5. **Answer your question** - Use results to provide context

## Session Log Format

Session data is stored in:
- Location: `~/.claude/projects/[project-name]/*.jsonl`
- Format: Line-delimited JSON with message objects
- Content: User prompts and Claude responses
- Indexed: Most recent files first (by mtime)

Each JSONL file contains:
- `type: "user"` - Your prompts
- `type: "assistant"` - My responses
- Skips: Subagent logs (agent-*.jsonl)

## Implementation Steps

1. Scan session directory: `ls -t ~/.claude/projects/*/*.jsonl`
2. Skip agent logs: Filter out `agent-*.jsonl`
3. Read JSONL: Parse JSON line-by-line
4. Extract messages: Filter for "user" and "assistant" types
5. Search: Match your query against content
6. Display: Show matching prompts with context

## Search Capabilities

- **Topic search** - Find discussions about specific subjects
- **Temporal search** - Find work from yesterday, last week, etc.
- **File-based search** - Find when you last edited a file
- **Tool search** - Find when you used specific tools
- **Pattern search** - Find similar problems or approaches

## Integration with ELF

The search command integrates with the building's session summaries. After search:
- Relevant heuristics might be suggested
- Related failures/successes found
- Continuous context preserved

This helps you avoid repeating past mistakes and leverage previous insights.

## Search Tips

- Use **specific keywords** - "router" not just "code"
- Try **natural language** - System understands intent
- Include **context** - "when I worked on auth" not just "auth"
- Check **timeframe** - Session logs are dated
