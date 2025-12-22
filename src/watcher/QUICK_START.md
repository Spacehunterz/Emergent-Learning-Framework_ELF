# Tiered Watcher - Quick Start Guide

## Prerequisites

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Start the Watcher

```bash
# Interactive (Ctrl+C to stop)
~/.claude/emergent-learning/scripts/start-watcher.sh

# Daemon mode (background)
~/.claude/emergent-learning/scripts/start-watcher.sh --daemon
```

## Monitor Activity

```bash
# Watch all logs
tail -f ~/.claude/emergent-learning/.coordination/*.log

# Just the orchestrator
tail -f ~/.claude/emergent-learning/.coordination/launcher.log
```

## What to Expect

1. **Launcher** starts and spawns Haiku watcher
2. **Haiku** polls `.coordination/` every 30 seconds
3. **Haiku** exits with code 1 when it detects issues
4. **Launcher** catches exit code 1 and invokes Opus
5. **Opus** analyzes, decides, updates state, exits
6. **Launcher** restarts Haiku to continue monitoring

## Exit Codes

- **0**: Normal shutdown (clean exit)
- **1**: Intervention needed (triggers Opus)
- **2**: Error occurred (will auto-retry)

## Files to Watch

- `launcher.log` - Orchestration events
- `haiku_watcher.log` - Tier 1 checks
- `opus_handler.log` - Tier 2 interventions
- `status.md` - Current system state
- `blackboard.json` - Agent coordination state

## Configuration

Edit `~/.claude/emergent-learning/watcher/config.py`:

```python
POLL_INTERVAL = 30              # Seconds between checks
HEARTBEAT_TIMEOUT = 120         # Stale agent threshold
MAX_RESTART_ATTEMPTS = 3        # Crash protection
```

## Troubleshooting

**Problem**: "ANTHROPIC_API_KEY environment variable is required"
```bash
export ANTHROPIC_API_KEY="your-key-here"
# Add to ~/.bashrc or ~/.zshrc to persist
```

**Problem**: Watcher keeps restarting
```bash
# Check the logs for errors
cat ~/.claude/emergent-learning/.coordination/launcher.log
```

**Problem**: Opus never invoked
```bash
# Verify Haiku is detecting issues
grep "intervention_needed" ~/.claude/emergent-learning/.coordination/haiku_watcher.log
```

## Full Documentation

See `README.md` for complete documentation, architecture details, and advanced usage.

---

*Part of the Emergent Learning Framework*
