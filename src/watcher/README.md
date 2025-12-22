# Tiered Watcher Pattern

A two-tier AI-powered monitoring system that provides cost-effective continuous monitoring with intelligent escalation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LAUNCHER.PY                            │
│  Orchestrates the system, manages process lifecycle        │
└──────────────┬────────────────────────────┬─────────────────┘
               │                            │
               ▼                            ▼
    ┌──────────────────┐        ┌──────────────────────┐
    │  TIER 1: HAIKU   │        │   TIER 2: OPUS       │
    │  Fast, Frequent  │        │  Deep Analysis       │
    │  Basic Checks    │        │  Decision Making     │
    └──────────────────┘        └──────────────────────┘
               │                            ▲
               │ Exit Code 1                │
               │ (Need Help)                │
               └────────────────────────────┘

           ┌────────────────────────┐
           │   .coordination/       │
           │   - blackboard.json    │
           │   - status.md          │
           │   - events.jsonl       │
           │   - *.log              │
           └────────────────────────┘
```

## Concept

The Tiered Watcher Pattern solves the problem of continuous AI monitoring at scale:

- **Problem**: Running Opus constantly is expensive
- **Solution**: Use Haiku for frequent basic checks, escalate to Opus only when needed
- **Benefit**: 95% cost reduction while maintaining high-quality oversight

### Tier 1: Haiku Watcher
- Runs every 30 seconds
- Checks coordination files for issues
- Fast pattern recognition
- Low cost (~$0.001 per check)
- Exits with code 1 when it needs help

### Tier 2: Opus Handler
- Invoked only when Haiku requests intervention
- Deep analysis and decision-making
- Updates coordination state
- Higher cost but infrequent (~5-10x per day)

### Launcher
- Runs Haiku in a loop
- Monitors exit codes
- Invokes Opus when needed
- Handles graceful shutdown
- Logs all activity

## Quick Start

### 1. Start the Watcher

```bash
# Using the convenience script
~/.claude/emergent-learning/scripts/start-watcher.sh

# Or directly
cd ~/.claude/emergent-learning
python watcher/launcher.py
```

### 2. Stop the Watcher

```bash
# Graceful shutdown (SIGINT)
Ctrl+C

# Or send SIGTERM
kill <launcher_pid>
```

### 3. Monitor Activity

```bash
# Watch the logs
tail -f ~/.claude/emergent-learning/.coordination/launcher.log

# Check Haiku logs
tail -f ~/.claude/emergent-learning/.coordination/haiku_watcher.log

# Check Opus logs
tail -f ~/.claude/emergent-learning/.coordination/opus_handler.log

# View current status
cat ~/.claude/emergent-learning/.coordination/status.md
```

## Configuration

Edit `watcher/config.py` to customize:

```python
POLL_INTERVAL = 30              # Seconds between Haiku checks
HEARTBEAT_TIMEOUT = 120         # Seconds before considering watcher dead
MAX_RESTART_ATTEMPTS = 3        # Max consecutive restarts
LOG_RETENTION = 100             # Log entries to keep in memory
```

### Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Files and Directories

```
watcher/
├── __init__.py          # Package initialization
├── config.py            # Configuration settings
├── launcher.py          # Main orchestrator
├── haiku_watcher.py     # Tier 1 watcher (created by Agent 2)
├── opus_handler.py      # Tier 2 handler (created by Agent 3)
└── README.md            # This file

.coordination/
├── blackboard.json      # Shared state between agents
├── status.md            # Current system status
├── events.jsonl         # Event log
├── launcher.log         # Launcher activity
├── haiku_watcher.log    # Haiku checks and findings
└── opus_handler.log     # Opus interventions
```

## Exit Codes

- **0**: Normal exit (clean shutdown)
- **1**: Intervention needed (Haiku requests Opus)
- **2**: Error occurred (will retry)

## Troubleshooting

### Watcher Won't Start

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
cd ~/.claude/emergent-learning
pip install anthropic  # or bun install if using JS version
```

**Problem**: `ANTHROPIC_API_KEY not found`

**Solution**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
# Or add to ~/.bashrc or ~/.zshrc
```

### Watcher Keeps Restarting

**Check the logs**:
```bash
tail -50 ~/.claude/emergent-learning/.coordination/launcher.log
```

**Common causes**:
- Haiku watcher script has bugs
- Configuration files missing
- Permissions issues with .coordination directory

### Opus Never Invoked

**Verify Haiku is detecting issues**:
```bash
cat ~/.claude/emergent-learning/.coordination/haiku_watcher.log
```

**Haiku should exit with code 1 when intervention is needed**. If it's not detecting issues, check the detection logic in `haiku_watcher.py`.

### Too Many Opus Invocations

**Problem**: Opus being called too frequently (high cost)

**Solutions**:
1. Adjust Haiku detection thresholds (make it less sensitive)
2. Increase `POLL_INTERVAL` to reduce check frequency
3. Review Haiku logic to ensure it's handling common issues independently

### Logs Growing Too Large

**Problem**: Log files consuming disk space

**Solution**: Implement log rotation
```bash
# Add to crontab
0 0 * * * find ~/.claude/emergent-learning/.coordination -name "*.log" -mtime +7 -delete
```

Or use the built-in `LOG_RETENTION` setting (keeps last N entries in memory).

## Best Practices

### 1. Monitor Cost
Track API usage to ensure the tier system is providing expected savings:
```bash
# Check number of Haiku calls
grep "Starting check" ~/.claude/emergent-learning/.coordination/haiku_watcher.log | wc -l

# Check number of Opus calls
grep "Invoking Opus" ~/.claude/emergent-learning/.coordination/launcher.log | wc -l

# Expected ratio: 50:1 or higher (Haiku:Opus)
```

### 2. Tune Thresholds
If Opus is invoked too often:
- Make Haiku more autonomous (handle more cases)
- Increase intervention threshold
- Add more Haiku-level patterns

If Opus is rarely invoked:
- Lower intervention threshold
- Expand detection scope

### 3. Review Logs Regularly
Set up a weekly review:
```bash
# What issues did Haiku detect?
grep "ISSUE DETECTED" ~/.claude/emergent-learning/.coordination/haiku_watcher.log

# What decisions did Opus make?
grep "DECISION" ~/.claude/emergent-learning/.coordination/opus_handler.log
```

### 4. Backup Coordination State
The `.coordination/` directory contains valuable system state:
```bash
# Daily backup
tar -czf coordination-backup-$(date +%Y%m%d).tar.gz .coordination/
```

## Advanced Usage

### Run as System Service (Linux/macOS)

Create `/etc/systemd/system/watcher.service`:
```ini
[Unit]
Description=Tiered Watcher Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/.claude/emergent-learning
ExecStart=/usr/bin/python3 watcher/launcher.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable watcher
sudo systemctl start watcher
sudo systemctl status watcher
```

### Custom Integrations

The watcher can be extended to monitor any system. Modify `haiku_watcher.py` to:
- Check external APIs
- Monitor file systems
- Watch databases
- Track application metrics

The pattern remains the same: Haiku does fast checks, Opus handles complex decisions.

## Cost Analysis

### Example: 24-hour Operation

**Haiku Tier**:
- Checks per hour: 120 (every 30s)
- Checks per day: 2,880
- Cost per check: ~$0.001
- Daily cost: ~$2.88

**Opus Tier**:
- Interventions per day: ~10 (estimated)
- Cost per intervention: ~$0.10
- Daily cost: ~$1.00

**Total daily cost**: ~$3.88

**Comparison**:
- Running Opus every 30s: ~$288/day (75x more expensive)
- Savings: ~$284/day (~$8,500/month)

## Architecture Decisions

### Why Subprocess Instead of Threading?

The launcher uses `subprocess.Popen` to run Haiku rather than threading:

**Pros**:
- Clean process isolation
- Easy restart on failure
- Clear exit code communication
- No shared state issues

**Cons**:
- Slightly higher overhead
- Requires IPC via files

**Decision**: Subprocess chosen for reliability and simplicity.

### Why Exit Codes Instead of Exceptions?

Haiku signals intervention needs via exit code 1:

**Pros**:
- Works across languages (Python, Bash, Node)
- Standard Unix pattern
- No need for complex IPC

**Cons**:
- Limited to ~255 distinct codes
- Less expressive than structured data

**Decision**: Exit codes chosen for simplicity and portability.

## Future Enhancements

- [ ] Add metrics collection (Prometheus/StatsD)
- [ ] Web dashboard for monitoring
- [ ] Configurable intervention policies
- [ ] Multi-tier escalation (add Sonnet tier)
- [ ] Automatic cost optimization
- [ ] Pattern learning from interventions

## Contributing

When modifying the watcher system:

1. Test both tiers independently first
2. Verify graceful shutdown works
3. Check log output is useful
4. Document configuration changes
5. Update this README

## License

Part of the Emergent Learning Framework.
