# CLI Reference

## Query Commands

```bash
# Build full context (what agents see)
python ~/.claude/emergent-learning/query/query.py --context

# Query by domain
python ~/.claude/emergent-learning/query/query.py --domain testing

# Query by tags
python ~/.claude/emergent-learning/query/query.py --tags api,error

# Get recent learnings
python ~/.claude/emergent-learning/query/query.py --recent 10

# View statistics
python ~/.claude/emergent-learning/query/query.py --stats

# Validate database
python ~/.claude/emergent-learning/query/query.py --validate

# Export learnings
python ~/.claude/emergent-learning/query/query.py --export > backup.json
```

## Session Search

Search your session history with natural language using the `/search` slash command:

```
/search what was my last prompt?
/search what was I working on yesterday?
/search find prompts about git
/search when did I last check in?
/search show me recent conversations
```

Type `/search` followed by any question in plain English. Claude will search your session logs and answer based on your conversation history.

**Token Usage:** ~500 tokens for quick lookups, scales with how much history you request.

## Recording Scripts

```bash
# Record a failure
~/.claude/emergent-learning/scripts/record-failure.sh

# Record a heuristic
~/.claude/emergent-learning/scripts/record-heuristic.sh

# Start an experiment
~/.claude/emergent-learning/scripts/start-experiment.sh
```

## Conductor Commands

```bash
# List workflow runs
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflows

# Show specific run
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflow 123

# Show failures
python ~/.claude/emergent-learning/conductor/query_conductor.py --failures

# Show hotspots
python ~/.claude/emergent-learning/conductor/query_conductor.py --hotspots

# Show trails by scent
python ~/.claude/emergent-learning/conductor/query_conductor.py --trails --scent blocker

# Statistics
python ~/.claude/emergent-learning/conductor/query_conductor.py --stats
```
