# Session Search Command

Natural language search through Claude Code session history.

## Usage
```
/search what was my last prompt?
/search what was I working on yesterday?
/search find prompts about git
/search show me recent conversations
```

## Instructions for Claude

**User's query:** $ARGUMENTS

**Step 1:** Extract user prompts from session logs by running:

```bash
python3 ~/.claude/commands/session-search.py
```

**Step 2:** Answer the user's natural language query based on the results.

## Session Log Format
- Location: `~/.claude/projects/[project-name]/*.jsonl`
- User messages: `{"type": "user", "message": {"content": "..."}}`
- Sorted by mtime = most recent first
- Skip `agent-*.jsonl` files (subagent logs)
