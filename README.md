<p align="center">
  <img src="assets/header.jpg" alt="Emergent Learning Framework" width="100%">
</p>

# Emergent Learning Framework

> Persistent memory and pattern tracking for Claude Code sessions.

## TL;DR

Claude Code learns from your failures and successes, building institutional knowledge that persists across sessions. Instead of re-explaining the same project quirks every time, patterns strengthen automatically. Install once, watch knowledge compound over weeks.

**30-Second Quick Start:**
```bash
./install.sh              # Mac/Linux
# or
./install.ps1             # Windows

# Use Claude Code normally - learning happens automatically
claude

# Check what's been learned
python ~/.claude/emergent-learning/query/query.py --stats
```

## Quick Navigation

| Section | Description |
|---------|-------------|
| [The Problem](#the-problem) | Why this exists |
| [The Solution](#the-solution) | How it works |
| [What This Enables](#what-this-actually-enables) | Before/after comparison |
| [A Real Example](#a-real-example) | Week-by-week walkthrough |
| [Plan Compatibility](#plan-compatibility) | Free/Pro/Max + model support |
| [Quick Start](#quick-start) | Installation guide |
| [Using the Dashboard](#using-the-dashboard) | Visual monitoring |
| [Golden Rules](#golden-rules) | Core principles |
| [Key Phrases](#key-phrases-claude-understands) | "check in", "query the building" |
| [Swarm: Multi-Agent](#swarm-multi-agent-coordination) | /swarm command + coordinated agents |
| [CLI Commands](#cli-commands) | Command reference |
| [The Bigger Picture](#the-bigger-picture) | Why this matters |

---

## The Problem

Claude Code is powerful, but every session starts from zero. Close the terminal and everything learned is gone:

- That bug you debugged for an hour? Claude might make the same mistake tomorrow.
- Your project's quirks and patterns? Re-explain them every session.
- The approach that finally worked? Lost in a scrolled-past conversation.

You're not building on past work. You're starting over. Every. Single. Time.

## The Solution

This framework gives Claude Code a persistent memory - a "building" of institutional knowledge that survives across sessions.

**Before each task**, Claude queries the building:
```
"Have we seen this before? What worked? What failed? What should I watch out for?"
```

**After each task**, outcomes are recorded:
```
"This approach worked because X" or "This failed - avoid Y in the future"
```

**Over time**, patterns emerge:
- Heuristics gain confidence through repeated validation
- Proven patterns get promoted to "golden rules"
- Your project develops its own institutional memory

## What This Actually Enables

| Without Framework | With Framework |
|-------------------|----------------|
| Same mistakes repeated across sessions | Known failures are surfaced before you hit them again |
| Re-explaining project context every time | Project patterns persist and strengthen |
| Knowledge dies when context window resets | Knowledge compounds across sessions |
| No visibility into what Claude "learned" | Dashboard shows patterns, confidence scores, history |

## What It's NOT

Let's be clear about limitations:
- **Not AI training** - Claude's model doesn't change. This is structured context injection.
- **Not magic** - It's systematic note-taking with automatic retrieval.
- **Not instant value** - It compounds over time. Day one won't feel different.
- **Not guaranteed** - Value depends on how consistently you use Claude Code.

## A Real Example

**Week 1:** You're working on an API. Claude suggests using `fetch` without error handling. The call fails silently in production. You fix it, and the framework records: *"API calls need explicit error handling - silent failures caused production bug."*

**Week 2:** Different part of the codebase, similar situation. Before Claude writes the code, it queries the building and sees the heuristic. The generated code includes error handling from the start.

**Week 3:** The heuristic has been validated 5 times. Confidence is now 0.8. It's automatically injected into relevant prompts.

**Month 2:** The pattern has 15 validations, 0 violations, confidence 0.95. It gets promoted to a golden rule - a constitutional principle Claude follows for your project.

**The compound effect:** You didn't have to re-explain "always handle API errors" fifteen times. You explained it once, the framework learned, and now it's institutional knowledge.

## How It's Different

| Alternative | Problem |
|-------------|---------|
| **Chat history** | Truncated, not searchable, not structured |
| **CLAUDE.md alone** | Static, manual updates, no confidence tracking |
| **Memory features** | Platform-dependent, not portable, limited control |
| **Taking notes yourself** | Manual effort, easy to forget, not injected automatically |

This framework: **Automatic capture + Structured storage + Confidence scoring + Automatic injection**

## Plan Compatibility

| Plan | Core + Dashboard | Swarm (Multi-Agent) |
|------|------------------|---------------------|
| **Free** | Yes | No (Task tool restricted) |
| **Pro ($20)** | Yes | Yes |
| **Max ($100+)** | Yes | Yes |

**Model compatibility:** Works with Haiku, Sonnet, and Opus. The framework doesn't require a specific model - it operates through hooks and CLAUDE.md instructions that any model can follow.

**Haiku users:** Everything works the same. You may want to keep CLAUDE.md instructions concise for best results.

**Free plan users:** Install with `--no-swarm` to skip multi-agent features:
```bash
./install.sh --no-swarm    # Core + Dashboard only
```

## Token Cost (Be Informed)

This adds tokens to your usage. Here's the breakdown:

### Per-Session Costs
- **CLAUDE.md load:** ~1,500 tokens (happens once per session start)
- **Golden rules injection:** ~500 tokens (included in context every session)

### Per-Task Costs
- **Pre-hook query:** 200-500 tokens (fetches relevant heuristics before Task execution)
- **Heuristic injection:** 50-200 tokens per heuristic (varies by how many are relevant)
- **Post-hook recording:** Minimal (writes to database, doesn't use API tokens)

### Typical Usage Patterns

| Scenario | Token Overhead | Notes |
|----------|----------------|-------|
| Simple task, no heuristics yet | ~1,500 (session) + ~200 (query) = 1,700 tokens | First week when database is empty |
| Task with 3 relevant heuristics | ~1,500 + ~500 (query + inject) = 2,000 tokens | After patterns emerge |
| Complex task, 10+ heuristics | ~1,500 + ~1,000 = 2,500 tokens | Mature project with many patterns |
| Swarm multi-agent task | 2,500 × N agents | N = number of spawned subagents |

### Cost-Benefit Analysis

**The tradeoff:** Slightly higher token use per task, but potentially fewer wasted attempts from repeating known mistakes. Whether this saves tokens overall depends on how often you'd otherwise repeat errors.

**Example:**
- Without ELF: Repeat file-handling bug 5 times, 10 messages per debug session = 50 messages wasted
- With ELF: Pay 500 extra tokens per task, but avoid 50 wasted messages
- Break-even: If you avoid just 1-2 repeated bugs, the token cost pays for itself

### Reducing Token Costs

If token usage is a concern:

1. **Prune low-value heuristics** - Archive patterns with confidence < 0.3 via dashboard
2. **Use domain-specific queries** - `--domain testing` instead of `--context` for narrower injection
3. **Disable for trivial tasks** - Create a settings profile without hooks for quick one-offs
4. **Periodic cleanup** - Review and archive outdated heuristics monthly

**Dashboard monitoring:** The Metrics tab shows token estimates per heuristic so you can identify high-cost, low-value patterns.


## Features

- **Automatic Recording** - Pre/post hooks capture task outcomes without manual effort
- **Pattern Tracking** - Heuristics gain/lose confidence based on real results
- **Local Dashboard** - Visual interface for browsing knowledge (uses no API tokens)
- **Query System** - Search past learnings by domain, tags, or free text
- **Swarm Coordination** - Multi-agent workflows with specialized personas

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+ or Bun (recommended)
- Claude Code CLI installed

**Verify you have the prerequisites:**

```bash
# Check Python version
python --version
# Expected: Python 3.8.0 or higher
# Example output: Python 3.11.5

# Check Node.js version
node --version
# Expected: v18.0.0 or higher
# Example output: v20.10.0

# Or check Bun (faster alternative)
bun --version
# Expected: 1.0.0 or higher
# Example output: 1.0.23

# Check Claude Code is installed
claude --version
# Expected: Should show version number without error
# Example output: @anthropic-ai/claude-code version 1.2.0
```

**If any command is not found, install the missing prerequisite before continuing.**

### Installation

The installer has three components you can mix and match:

| Component | What it does |
|-----------|-------------|
| **Core** | Query system, hooks, golden rules, CLAUDE.md (always installed) |
| **Dashboard** | React UI for monitoring patterns (localhost:3000) |
| **Swarm** | Multi-agent conductor, agent personas (researcher, architect, skeptic, creative) |

**Install everything (default):**
```bash
./install.sh              # Mac/Linux
./install.ps1             # Windows
```

**Install options:**
```bash
./install.sh --core-only      # Just core, no dashboard or swarm
./install.sh --no-dashboard   # Core + swarm, skip dashboard
./install.sh --no-swarm       # Core + dashboard, skip swarm
./install.sh --help           # Show all options
```

### What Gets Installed

```
~/.claude/
├── CLAUDE.md                    # Agent instructions (queries the building)
├── settings.json                # Hook configurations
├── emergent-learning/
│   ├── query/query.py          # Query system for retrieving knowledge
│   ├── memory/
│   │   ├── index.db            # SQLite database
│   │   ├── golden-rules.md     # Constitutional principles
│   │   ├── failures/           # Recorded failure logs
│   │   └── successes/          # Recorded success logs
│   ├── scripts/                # Utility scripts
│   │   ├── record-failure.sh   # Record a failure
│   │   ├── record-heuristic.sh # Record a heuristic
│   │   └── start-experiment.sh # Start an experiment
│   ├── dashboard-app/          # Real-time monitoring UI (if installed)
│   ├── conductor/              # Workflow orchestration (if swarm installed)
│   ├── agents/                 # Agent personas (if swarm installed)
│   │   ├── researcher/
│   │   ├── architect/
│   │   ├── skeptic/
│   │   └── creative/
│   └── ceo-inbox/              # Escalated decisions
└── hooks/
    └── learning-loop/          # Automatic learning hooks
```

## Using the Dashboard

**Auto-Start (Recommended):** The dashboard starts automatically when you launch Claude Code via a startup hook. The hook starts both the FastAPI backend (port 8888) and React frontend (port 3001) in the background.

**Manual Start:** If you need to start it manually:

```bash
cd ~/.claude/emergent-learning/dashboard-app
./run-dashboard.ps1  # Windows
./run-dashboard.sh   # Mac/Linux
```

Then open http://localhost:3001 (or http://localhost:3000 if using manual start)

![Cosmic Dashboard - Heuristics View](docs/images/cosmic-dashboard-heuristics.png)

### Dashboard Tabs

| Tab | What It Shows |
|-----|---------------|
| **Overview** | Hotspot treemap (D3.js), anomalies, active golden rules |
| **Heuristics** | All learned patterns with confidence scores, promote/demote to golden |
| **Runs** | Agent execution history with status filtering, retry failed runs |
| **Timeline** | Event-by-event history with playback controls |
| **Query** | Natural language search across all knowledge |

### Stats Bar

The top bar shows real-time metrics with drill-down capability:
- **Total Runs** - Click to see run history
- **Success Rate** - Percentage of successful executions
- **Heuristics** - Total patterns learned (84 in screenshot)
- **Golden Rules** - Constitutional principles (8 active)
- **Hotspots** - High-activity code locations
- **Queries** - Building queries made (177 in screenshot)

### Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI (Python) with WebSocket real-time updates
- **Visualization**: D3.js for treemaps
- **Database**: Reads from `~/.claude/emergent-learning/memory/index.db`
- **Themes**: 10 cosmic themes (black-hole, nebula, aurora, etc.)

The dashboard operates **without consuming API tokens** - it reads directly from your local SQLite database.

## How It Works


### The Learning Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    The Learning Loop                        │
└─────────────────────────────────────────────────────────────┘

    ┌──────────┐
    │  QUERY   │  ← Check building for relevant knowledge
    │  ↓       │
    │  APPLY   │  ← Use heuristics during task execution  
    │  ↓       │
    │  RECORD  │  ← Capture outcome (success/failure)
    │  ↓       │
    │  PERSIST │  ← Update confidence scores
    └────┬─────┘
         │
         └──→ (cycle repeats with stronger patterns)

Every task strengthens the loop. Every loop builds the building.
```

### The Learning Loop

1. **Before Task**: Pre-hook injects relevant heuristics into agent prompts
2. **Task Executes**: Agent works with building knowledge
3. **After Task**: Post-hook records outcomes, validates/violates heuristics
4. **Promotion**: High-confidence heuristics become golden rules

### Golden Rules

These are constitutional principles that all agents follow:

1. **Query Before Acting** - Always check the building first
   - *Why:* Prevents repeating known mistakes and leverages accumulated wisdom

2. **Document Failures Immediately** - Record while context is fresh
   - *Why:* Details fade quickly; immediate documentation captures root causes

3. **Extract Heuristics** - Document the WHY, not just outcomes
   - *Why:* Outcomes are specific to one instance; heuristics apply broadly across similar situations

4. **Break It Before Shipping** - Test destructively before release
   - *Why:* You will find bugs now or users will find them later. Better you than them.

5. **Escalate Uncertainty** - Ask when unsure about big decisions
   - *Why:* Better to ask than to assume incorrectly on important matters

**Note on "Break It Before Shipping":** This means QA testing - deliberately trying edge cases and failure modes *before* shipping to find bugs. It does NOT mean making artificial mistakes to populate the database. The framework learns from natural failures that occur during real development work.


### Heuristics

Heuristics are learned patterns with:
- **Domain** - Area of applicability (testing, api, security, etc.)
- **Confidence** - 0.0 to 1.0, increases with validations
- **Validations** - Times the heuristic led to success
- **Violations** - Times it was present during failure

When confidence > 0.9 and validations > 10, a heuristic can be promoted to golden.

## Customizing Golden Rules

Golden Rules are the constitutional principles that guide all agents. Here's how to customize them for your project:

### Understanding Rule Priority

1. **Built-in Golden Rules** (in `~/.claude/emergent-learning/memory/golden-rules.md`)
   - Universal principles like "Query Before Acting"
   - Loaded in every agent context
   - High confidence, many validations

2. **Project-Specific Rules** (in your CLAUDE.md)
   - Custom rules for your specific codebase
   - Can override or extend built-in rules
   - You define and maintain them

### Adding a Project-Specific Golden Rule

**Step 1: Identify the pattern**
- It should be a principle you've validated 10+ times
- It should apply broadly to your project
- It should save significant time/errors when followed

**Step 2: Add to CLAUDE.md**
```bash
# Edit your project's CLAUDE.md
nano ~/.claude/CLAUDE.md

# Add under Golden Rules section:
## 6. [Your Custom Rule Name]
> [One-line description]

**Why:** [Explain the rationale]
**Promoted:** [Date you added it]
**Validations:** [How many times you've confirmed it works]
```

**Example:**
```markdown
## 6. Always Use Retry Logic for External APIs
> Any call to external services must include exponential backoff retry

**Why:** Our third-party APIs are unreliable. Silent failures caused 3 production incidents.
**Promoted:** 2025-12-01
**Validations:** 15 (prevented failures in payment, auth, and notification services)
```

### Promoting a Heuristic to Golden

When a heuristic has proven itself repeatedly:

```bash
# 1. Check heuristic confidence
python ~/.claude/emergent-learning/query/query.py --context | grep "Your pattern"

# 2. If confidence > 0.9 and validations > 10, promote it
# Edit golden-rules.md
nano ~/.claude/emergent-learning/memory/golden-rules.md

# 3. Move the heuristic from database to golden-rules.md
# 4. Update CLAUDE.md to reference it
```

### Removing or Modifying Rules

**To remove a built-in rule:**
```bash
# Edit golden-rules.md
nano ~/.claude/emergent-learning/memory/golden-rules.md

# Comment out or delete the rule
# Add a note explaining why you removed it
```

**To modify a rule:**
```bash
# Edit the description in golden-rules.md
# Update CLAUDE.md if the rule is referenced there
# Consider recording the modification as a CEO decision:
nano ~/.claude/emergent-learning/ceo-inbox/modified-rule-X.md
```

### Rule Validation Workflow

1. **Start as hypothesis** - Add to CLAUDE.md as "Experimental Rule"
2. **Track validations** - Manually note each time it prevents an error
3. **Promote at 10 validations** - Move to golden-rules.md
4. **Monitor effectiveness** - Dashboard shows if rule is being followed

### Best Practices

- **Don't over-specify** - Rules should be principles, not implementation details
  - Good: "Validate user input before processing"
  - Bad: "Use Joi schema validation with these exact fields: name, email, age"

- **Make rules actionable** - Agent should know what to do
  - Good: "Check file existence before reading"
  - Bad: "Be careful with files"

- **Include the Why** - Helps agents understand context
  - Good: "Hash passwords (Why: plaintext passwords caused security breach)"
  - Bad: "Hash passwords"

### Example: Complete Custom Rule Set

```markdown
# Project Golden Rules (in CLAUDE.md)

## Custom Rules for [Project Name]

### 6. All Database Queries Must Be Parameterized
> Never use string concatenation for SQL - always use parameterized queries

**Why:** SQL injection vulnerability found in production (2025-11-15)
**Validations:** 20+

### 7. Log Before External Calls
> Always log request/response for external API calls

**Why:** Debugging production issues requires audit trail
**Validations:** 12

### 8. Feature Flags for Experimental Code
> New features must be behind a feature flag for 1 week

**Why:** Allows quick rollback without deployment
**Validations:** 8
```

### Testing Custom Rules

After adding a custom rule:

1. **Start new Claude session**
   ```bash
   claude
   ```

2. **Check rule is loaded**
   ```
   You: check in
   [Look for your custom rule in output]
   ```

3. **Test with relevant task**
   ```
   You: Write a function that queries the users table
   [Claude should follow your "parameterized queries" rule]
   ```

4. **Validate it's working**
   - If Claude follows the rule: Record as validation
   - If Claude ignores it: Make the rule more explicit or check CLAUDE.md loaded correctly

## Configuration

### CLAUDE.md

The `~/.claude/CLAUDE.md` file contains instructions that Claude Code follows. The framework installs a template that:
- Requires querying the building before tasks
- Lists the golden rules
- Explains how to record learnings

### settings.json

Hook configuration in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/learning-loop/pre_tool_learning.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/learning-loop/post_tool_learning.py"
      }]
    }]
  }
}
```

## Key Phrases Claude Understands

The CLAUDE.md template teaches Claude to respond to these phrases:

| Phrase | What It Does |
|--------|--------------|
| `check in` | Queries the building and reports relevant context |
| `query the building` | Same as check in - shows golden rules, heuristics, recent learnings |
| `what does the building know about X` | Searches for knowledge on topic X |

**Example:**
```
You: check in

Claude: [Queries building, returns:]

        ## Golden Rules (8 active)
        1. Query Before Acting
        2. Document Failures Immediately
        ...

        ## Relevant Heuristics
        - [0.85] API calls need error handling
        - [0.72] Test database queries separately

        ## Recent Context
        - Fixed auth bug yesterday
        - Dashboard WebSocket issue resolved
```

This works because CLAUDE.md instructs Claude to run the query system whenever you say "check in" or similar phrases.

## Automatic vs Manual Learning

Understanding when learning happens automatically vs when you need to manually record:

### Automatic (via Hooks)

These happen without any action from you:

- **Pre-task query:** Before each Task tool use, relevant heuristics are automatically injected
- **Post-task recording:** After Task completion, outcome is logged with metadata
- **Confidence updates:** Heuristics gain/lose confidence based on task success/failure
- **Pattern detection:** System identifies which heuristics were present during successes/failures

**You just use Claude Code normally. The framework watches and learns.**

### Manual (via Key Phrases)

These require you to explicitly say something:

| When to Use | What to Say | What Happens |
|-------------|-------------|--------------|
| Check current knowledge | `check in` or `query the building` | Claude queries and reports golden rules, heuristics, recent context |
| Search for specific topic | `what does the building know about X` | Searches knowledge base for topic X |
| Record a significant failure | `record this failure: [lesson]` | Creates detailed failure log with lesson extracted |
| Record a significant success | `record this success: [pattern]` | Documents what worked and why |
| Start an experiment | `start experiment: [hypothesis]` | Tracks a hypothesis you're testing |

### Best Practice

**Week 1-2:** Just use Claude Code. Let automatic learning do its job. Don't overthink it.

**Week 3+:** Occasionally `check in` before complex tasks to see what the building knows. Manually record major insights that the automatic system might miss.

**Advanced:** Use manual recording for project-specific patterns that aren't obvious from task success/failure alone (e.g., "This API is rate-limited to 100 req/min").

## CLI Commands

Query the building from command line:

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
```

## Architecture

```
+---------------------------------------------------------------+
|                      Claude Code Session                      |
+---------------------------------------------------------------+
|                                                               |
|   +--------------+    +--------------+    +--------------+    |
|   |   Pre-Hook   |--->|  Task Tool   |--->|  Post-Hook   |    |
|   |   (inject)   |    |  (execute)   |    |   (record)   |    |
|   +------+-------+    +--------------+    +-------+------+    |
|          |                                        |           |
|          v                                        v           |
|   +-------------------------------------------------------+   |
|   |                    SQLite Database                    |   |
|   |  +----------+ +----------+ +---------+ +----------+   |   |
|   |  |Heuristics| |Learnings | | Metrics | |Violations|   |   |
|   |  +----------+ +----------+ +---------+ +----------+   |   |
|   +-------------------------------------------------------+   |
|          ^                                        ^           |
|          |                                        |           |
|   +------+-------+                        +-------+------+    |
|   | Query System |                        |  Dashboard   |    |
|   |  (query.py)  |                        | (React+API)  |    |
|   +--------------+                        +--------------+    |
|                                                               |
+---------------------------------------------------------------+
```

## Swarm: Multi-Agent Coordination

**Real-world use case:** You're debugging a production incident. The API is slow, but you don't know if it's the database, caching layer, or network. A single agent would investigate serially - checking one thing at a time. Swarm spawns multiple agents in parallel: one profiles endpoints, one analyzes database queries, one checks cache hit rates. They coordinate via a shared "blackboard," leaving trails for each other. In 5 minutes, you have a complete picture from multiple perspectives.

### What It Does

The conductor coordinates multiple Claude Code subagents, each with a distinct persona:

| Agent | Role | When to Use |
|-------|------|-------------|
| **Researcher** | Deep investigation, gathering evidence | "We need to understand X" |
| **Architect** | System design, big picture planning | "How should we structure X?" |
| **Skeptic** | Breaking things, finding edge cases | "Is this robust?" |
| **Creative** | Novel solutions, alternative approaches | "We're stuck on X" |

### How to Use Swarm

**Use the `/swarm` slash command:**

```bash
/swarm investigate the authentication system    # Start a coordinated task
/swarm show                                     # View current swarm state
/swarm reset                                    # Clear blackboard and start fresh
/swarm stop                                     # Stop all agents
/swarm                                          # Continue/iterate on pending tasks
```

**Example session:**
```
You: /swarm investigate why the API is slow

Claude: ## Swarm Plan
        **Task:** Investigate API performance
        **Agents:** 3

        | # | Subtask | Scope |
        |---|---------|-------|
        | 1 | Profile endpoints | src/api/ |
        | 2 | Check database queries | src/db/ |
        | 3 | Review caching | src/cache/ |

        Proceed? [Y/n]

You: Y

[Agents execute in parallel, share findings via blackboard]

You: /swarm show

Claude: ## Swarm Status
        **Agents:** 3 (all completed)
        **Findings:** 7
        - [fact] N+1 query in /users endpoint
        - [blocker] No index on created_at column
        - [hypothesis] Redis cache miss rate high
```

**The agents will:**
1. Query the building for relevant context
2. Do their specialized work
3. Record findings to the blackboard
4. Pass context to the next agent (if sequential)

### The Blackboard Pattern

Agents coordinate through a shared "blackboard" - the SQLite database. This enables:

**Pheromone Trails:**
Agents leave signals for each other:
- `discovery` - "Found something interesting here"
- `warning` - "Be careful with this area"
- `blocker` - "This is broken/blocked"
- `hot` - "High activity, important area"
- `cold` - "Already explored, nothing here"

**Example flow:**
1. Researcher explores codebase, leaves `discovery` trails on relevant files
2. Architect sees trails, focuses design on those areas
3. Skeptic sees the plan, leaves `warning` trails on risky parts
4. All findings recorded to building for future sessions

### How It Works Internally

1. **Conductor** receives a complex task
2. Spawns appropriate agent personas as subagents
3. Agents work in parallel or sequence depending on task
4. Each agent queries the building before acting
5. Results are aggregated and conflicts resolved
6. Findings recorded back to the building

### Conductor Database

The swarm adds these tables to track multi-agent work:

| Table | Purpose |
|-------|---------|
| `workflow_runs` | Individual execution instances |
| `node_executions` | Each subagent's work with prompts and results |
| `trails` | Pheromone signals for swarm coordination |
| `conductor_decisions` | Audit log of orchestration choices |

### Query Conductor

```bash
# List recent workflow runs
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflows

# Show details for a specific run
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflow 123

# Show failed executions with prompts
python ~/.claude/emergent-learning/conductor/query_conductor.py --failures

# Show hot spots (most active locations)
python ~/.claude/emergent-learning/conductor/query_conductor.py --hotspots

# Show trail activity
python ~/.claude/emergent-learning/conductor/query_conductor.py --trails --scent blocker

# Show statistics
python ~/.claude/emergent-learning/conductor/query_conductor.py --stats
```

### Agent Personalities

Each agent has a distinct thinking style defined in `~/.claude/emergent-learning/agents/`:

**Researcher** (`agents/researcher/personality.md`)
- Thorough and methodical
- Asks "what else should we consider?"
- Documents everything found
- Prefers breadth before depth

**Architect** (`agents/architect/personality.md`)
- Top-down, structural thinking
- Asks "how does this fit together?"
- Draws diagrams, defines interfaces
- Considers future extensions

**Skeptic** (`agents/skeptic/personality.md`)
- Adversarial thinking
- Asks "what could go wrong?"
- Tests edge cases
- Assumes things will break

**Creative** (`agents/creative/personality.md`)
- Lateral thinking
- Asks "what if we tried something different?"
- Challenges assumptions
- Proposes unconventional solutions

### When to Use Swarm vs Single Agent

**Use single agent (default) for:**
- Straightforward tasks
- Quick fixes
- Simple questions

**Use swarm for:**
- Complex investigations with multiple angles
- Architecture decisions needing critique
- Debugging that requires both exploration and testing
- Tasks where you'd naturally want a second opinion

### Limitations of Swarm

- **Pro/Max plan required** - Free plan can't use Task tool for subagents
- Uses more tokens (multiple agents = multiple prompts)
- Adds coordination overhead
- Overkill for simple tasks
- Experimental - workflow graphs may need tuning

## Migration Guide

### Migrating from Plain Claude Code

If you've been using Claude Code without ELF, here's how to migrate:

**Step 1: Backup Your Current Setup**
```bash
# Backup existing CLAUDE.md (if you have custom instructions)
cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.backup

# Backup settings.json
cp ~/.claude/settings.json ~/.claude/settings.json.backup
```

**Step 2: Install ELF**
```bash
./install.sh
```

**Step 3: Merge Custom Instructions**
```bash
# If you had custom CLAUDE.md instructions:
# 1. Open your backup
cat ~/.claude/CLAUDE.md.backup

# 2. Open new CLAUDE.md
nano ~/.claude/CLAUDE.md

# 3. Add your custom instructions AFTER the ELF section
# Keep ELF's instructions at the top, add yours below
```

**Step 4: Test Integration**
```bash
# Start Claude Code
claude

# Verify hooks work
# Use a Task and check that learning is recorded:
python ~/.claude/emergent-learning/query/query.py --stats
```

**What Changes:**
- CLAUDE.md gets ELF instructions prepended
- settings.json gets hook configurations added
- New `~/.claude/emergent-learning/` directory created
- Everything else stays the same

**What Stays the Same:**
- Your projects and code
- Existing Claude Code workflows
- Command history and preferences

### Migrating from Early ELF Version

If you installed ELF before version 1.0:

**Check Your Version:**
```bash
cd ~/.claude/emergent-learning
git log -1 --format="%H %s %ai" 2>/dev/null || echo "No git history found"
```

**Migration Path:**

**From pre-1.0 to 1.0+:**
```bash
# 1. Export existing learnings
python ~/.claude/emergent-learning/query/query.py --export > ~/elf-export.json

# 2. Backup database
cp ~/.claude/emergent-learning/memory/index.db ~/elf-backup.db

# 3. Reinstall latest version
cd /path/to/ELF-repo
git pull
./install.sh

# 4. Import learnings (if schema compatible)
python ~/.claude/emergent-learning/query/query.py --import ~/elf-export.json
```

**Breaking Changes in 1.0:**
- Database schema changed (added conductor tables)
- Swarm feature added (requires Pro/Max plan)
- Dashboard rewritten (new tech stack)

**If import fails:**
```bash
# Start fresh, keep backup for reference
# Old database at ~/elf-backup.db
# Manually re-create important heuristics if needed
```

### Upgrading Between Versions

**Safe upgrade process:**

```bash
# 1. Check current status
python ~/.claude/emergent-learning/query/query.py --validate

# 2. Backup before upgrade
cp ~/.claude/emergent-learning/memory/index.db ~/elf-backup-$(date +%Y%m%d).db

# 3. Pull latest changes
cd /path/to/ELF-repo
git pull

# 4. Reinstall
./install.sh

# 5. Validate database migrated correctly
python ~/.claude/emergent-learning/query/query.py --validate

# 6. Check stats match expectations
python ~/.claude/emergent-learning/query/query.py --stats
```

**If something breaks:**
```bash
# Restore backup
cp ~/elf-backup-YYYYMMDD.db ~/.claude/emergent-learning/memory/index.db

# Revert to previous version
cd /path/to/ELF-repo
git checkout <previous-version-tag>
./install.sh
```

### Preserving Data During Reinstall

The installer is designed to preserve your data:

**What Gets Preserved:**
- `memory/index.db` - Your database
- `memory/failures/` - Failure logs
- `memory/successes/` - Success logs
- `ceo-inbox/` - Pending decisions

**What Gets Overwritten:**
- Hook scripts (updated to latest)
- Query system (updated to latest)
- Dashboard app (updated to latest)
- CLAUDE.md (updated, custom instructions need merge)

**To preserve custom CLAUDE.md:**
```bash
# Before reinstall
cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.custom

# After reinstall
# Manually merge your custom sections back in
```

### Team Migration

If multiple team members use ELF:

**Option 1: Shared Database (Advanced)**
```bash
# Set up network-accessible SQLite or PostgreSQL
# Modify query.py database path
# Requires coordination and locking strategy
# Not recommended for most teams
```

**Option 2: Individual Instances (Recommended)**
```bash
# Each developer runs their own ELF instance
# Share learnings via exported heuristics:

# Developer A exports valuable heuristics
python ~/.claude/emergent-learning/query/query.py --export-heuristics > team-heuristics.json

# Developer B imports them
python ~/.claude/emergent-learning/query/query.py --import-heuristics team-heuristics.json

# Add to team repo for onboarding
# Commit team-heuristics.json to project repo
```

**Option 3: Project-Specific Golden Rules**
```bash
# Create project CLAUDE.md with team rules
# Add to project repo: .claude/CLAUDE.md

# Each developer's global CLAUDE.md includes:
# "Also load project rules from: <project-path>/.claude/CLAUDE.md"
```

### Rollback Plan

If ELF isn't working for you:

**Full Uninstall:**
```bash
# See UNINSTALL.md for complete instructions

# Quick version:
# 1. Remove hooks from settings.json
# 2. Delete ~/.claude/emergent-learning/
# 3. Restore CLAUDE.md.backup if needed
```

**Partial Disable (Keep Data):**
```bash
# Remove hooks from settings.json but keep database
# Edit ~/.claude/settings.json, remove learning-loop entries

# Can re-enable later by running ./install.sh again
```

## Limitations

- **Requires consistent use** - The more you use it, the more valuable it becomes
- **Manual curation helps** - Auto-captured patterns can be noisy; reviewing the dashboard helps
- **Not instant** - Day one won't feel different. Week four will.
- **Early stage** - Experimental, expect rough edges

## The Bigger Picture

AI assistants are stateless by design. Every conversation is isolated. This isn't a bug - it's how they work.

But you're not stateless. Your projects aren't stateless. The mistakes you made last month still matter. The patterns that work for your codebase are real. The quirks of your stack don't disappear between sessions.

**The gap:** AI has no continuity. You do.

This framework bridges that gap. Not by changing the AI, but by giving it access to something it never had: your project's history.

Every failure recorded. Every pattern validated. Every hard-won lesson preserved.

The AI is still stateless. But now it wakes up in a building full of notes from every session that came before.

That's not artificial intelligence getting smarter. That's *your* intelligence, persisted.

## API Documentation & Resources

### Official Claude Documentation
- **Claude Code CLI:** https://docs.anthropic.com/en/docs/claude-code
- **Claude API Reference:** https://docs.anthropic.com/en/api
- **Hooks System:** https://docs.anthropic.com/en/docs/claude-code/hooks
- **Task Tool:** https://docs.anthropic.com/en/docs/claude-code/tools#task

### ELF-Specific Resources
- **Query System API:** `python ~/.claude/emergent-learning/query/query.py --help`
- **Database Schema:** `sqlite3 ~/.claude/emergent-learning/memory/index.db ".schema"`
- **Dashboard API:** http://localhost:5173/api/docs (when dashboard running)
- **Conductor API:** `python ~/.claude/emergent-learning/conductor/query_conductor.py --help`

### Python Dependencies
The framework uses these main libraries:
- **anthropic** - Claude API client
- **sqlite3** - Database (built-in to Python)
- **fastapi** - Dashboard backend API
- **websockets** - Real-time dashboard updates

### File Locations Reference

| Path | Purpose |
|------|---------|
| `~/.claude/CLAUDE.md` | Agent instructions loaded at session start |
| `~/.claude/settings.json` | Hook configurations |
| `~/.claude/emergent-learning/memory/index.db` | SQLite database with all learnings |
| `~/.claude/emergent-learning/query/query.py` | Query system for retrieving knowledge |
| `~/.claude/hooks/learning-loop/` | Pre/post hook scripts |
| `~/.claude/emergent-learning/dashboard-app/` | React dashboard application |
| `~/.claude/emergent-learning/conductor/` | Multi-agent orchestration system |
| `~/.claude/emergent-learning/agents/` | Agent personality definitions |

### Community & Support
- **Issues:** GitHub Issues (report bugs, request features)
- **Discussions:** GitHub Discussions (ask questions, share learnings)
- **Troubleshooting:** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## Git Workflow (Keep It Clean)

**Stay on `main`. Don't create random branches.**

```bash
# Before working - always pull latest
git pull

# After making changes - commit and push immediately
git add -A
git commit -m "description of what you did"
git push

# Check you're clean
git status
```

**Rules:**
- Always work on `main` branch
- Pull before you start, push when you're done
- Don't let commits pile up locally
- Never force push unless you know what you're doing

**If things get weird:**
```bash
# See what branch you're on
git branch

# If you're not on main, get back there
git checkout main
git pull

# Delete stray branches
git branch -D branch-name
```

**What NOT to commit:**
- `memory/index.db` - Your live database (changes constantly)
- `.vite/` - Build cache
- `desktop.ini` - Windows junk
- `node_modules/` - Dependencies (already gitignored)
- `.env` files - API keys, secrets, credentials
- Personal paths or usernames hardcoded in code
- Tokens, passwords, or API keys
- Anything with your real name/email if you want privacy

**Before pushing, ask yourself:**
- Does this contain any secrets or credentials?
- Does this expose personal information?
- Would I be okay if a stranger saw this?

## Contributing

Contributions welcome - bug fixes, improvements, documentation.

## License

MIT License

<a href="https://www.buymeacoffee.com/Spacehunterz">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>
