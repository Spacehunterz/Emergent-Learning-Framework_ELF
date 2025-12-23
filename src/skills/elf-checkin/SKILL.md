---
name: checkin
description: Load and review Emergent Learning Framework context, institutional knowledge, golden rules, and recent session history. Use this to query the building for relevant heuristics before starting tasks, to understand active experiments and decisions, and to maintain continuity across sessions.
license: MIT
---

# ELF Checkin Command

Load Emergent Learning Framework (ELF) context - institutional knowledge, golden rules, heuristics, and recent session history.

## Purpose

The `/checkin` command queries the ELF knowledge system to:

- **Load golden rules** - Constitutional principles and hard-won lessons
- **Get relevant heuristics** - Domain-specific knowledge and patterns
- **Review recent work** - Previous session summaries and context
- **Check active decisions** - Pending CEO review items
- **Understand experiments** - Active research and trials

## Usage

```
/checkin
/checkin architecture
/checkin debugging
```

## Implementation

When user invokes `/checkin`:

1. **Query ELF Context**
   ```bash
   python ~/.claude/emergent-learning/query/query.py --context
   ```

2. **Show Golden Rules** (TIER 1 - Always loaded)
   - Constitutional principles
   - Proven patterns
   - High-confidence rules

3. **Show Relevant Heuristics** (TIER 2 - Query-matched)
   - Domain-specific knowledge
   - Tag-based matches
   - Confidence scores

4. **Show Recent Sessions** (TIER 3 - Context)
   - Last session summary
   - What was accomplished
   - Where work left off

5. **Check Status**
   - Active experiments
   - Pending CEO decisions
   - Framework health

## Domain Queries

If user specifies a domain:
```bash
python ~/.claude/emergent-learning/query/query.py --domain [architecture|debugging|coordination|communication]
```

## What the Building Contains

- **Golden Rules** (`memory/golden-rules.md`) - Universal lessons
- **Heuristics** (`memory/heuristics/`) - Reusable patterns  
- **Failures** (`failure-analysis/`) - What went wrong and why
- **Successes** (`memory/successes/`) - What worked
- **Sessions** (`memory/sessions/`) - Previous work summaries
- **CEO Inbox** (`ceo-inbox/`) - Pending decisions

## Golden Rules (Always Loaded)

The system includes 12 golden rules. Key ones:
- **Query Before Acting** - Check existing knowledge first
- **Document Failures Immediately** - Record lessons while fresh
- **Trust User Reality Over Tool Metadata** - Believe user reports
- **No External APIs** - Subscription-only model
- **Always Use Async Subagents** - Never block on spawn

## Output Format

The checkin displays:
1. Building status and available models
2. Golden rules count and key rules
3. Relevant heuristics for your domains
4. Recent session summary
5. Active experiments/decisions summary

## Integration with ELF

The building is your external memory. Each Claude instance:
1. Queries context before working
2. Records failures as they happen
3. Documents successes and learnings
4. Proposes improvements to golden rules
5. Contributes to institutional knowledge

This creates a feedback loop where each iteration gets smarter.
