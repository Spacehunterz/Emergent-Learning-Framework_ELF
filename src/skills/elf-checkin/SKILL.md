---
name: checkin
description: Load and review Emergent Learning Framework context, institutional knowledge, golden rules, and recent session history. Runs the checkin workflow interactively with banner, context loading, and dashboard/multi-model prompts.
license: MIT
---

# ELF Checkin Command

Interactive workflow to load the building context before starting work.

## What It Does

The `/checkin` command:
- Shows the ELF banner with ASCII art
- Queries the building for golden rules and heuristics
- Displays relevant context for your domains
- Asks if you want to launch the dashboard
- Asks if you want to see multi-model support options
- Loads recent session summary

## Usage

```
/checkin
/checkin architecture
/checkin debugging
```

## Execution

This skill runs the actual workflow engine:

```bash
python ~/.claude/emergent-learning/scripts/run-workflow.py --workflow checkin --start
```

The workflow engine handles:
- Step execution and progress tracking
- Banner display on first checkin
- Interactive Y/n prompts for dashboard and multi-model
- Dashboard launch on user request
- Context loading from the building
- Session summary display

## Workflow Steps

1. **Display Banner** - Show ELF ASCII art
2. **Load Context** - Query the building (`query.py --context`)
3. **Show Golden Rules** - Display active rules (TIER 1)
4. **Show Heuristics** - Display relevant knowledge (TIER 2)
5. **Show Session Summary** - Display recent work (TIER 3)
6. **Dashboard Question** - Ask "Start Dashboard? [Y/n]"
7. **Multi-Model Question** - Ask "Show multi-model setup? [Y/n]"
8. **Complete** - Print "Ready to work!" and exit

## Domain-Specific Context

Pass a domain to focus on that area:
- `checkin architecture` - Architecture-focused heuristics
- `checkin debugging` - Debugging techniques
- `checkin coordination` - Team coordination patterns
- `checkin communication` - Communication best practices

This will run `query.py --domain [domain]` to get focused context.

## Interactive Prompts

**Dashboard**: "Start ELF Dashboard? [Y/n]"
- Y/yes/enter: Launches `~/.claude/emergent-learning/dashboard-app/run-dashboard.sh`
- N/no: Skips dashboard

**Multi-Model**: "Show multi-model support options? [Y/n]"  
- Y/yes/enter: Shows available models and setup instructions
- N/no: Skips multi-model info

## Integration with Building

The checkin workflow is your gateway to the building's knowledge:
- **Golden Rules** - Constitutional principles (always loaded)
- **Heuristics** - Reusable patterns and knowledge
- **Failures** - What went wrong and lessons learned
- **Successes** - What worked and can be replicated
- **Sessions** - Previous work summaries for continuity

Running checkin at the start of each session ensures you're working with current institutional knowledge.
