# Agent Pool Integration Plan (KISS Version)

**Created:** 2026-01-01
**Purpose:** Add specialized agent pool to existing ELF system
**Status:** IMPLEMENTED (2026-01-01)
**Principle:** Keep It Simple Stupid

---

## Executive Summary

Add 99 specialized agents from wshobson/agents to your existing system. Keep everything else as-is.

| Component | Action |
|-----------|--------|
| wshobson/agents | INSTALL (99 agents) |
| claude-flow | SKIP (don't need it) |
| Your blackboard | KEEP |
| Your basic-memory | KEEP |
| Your ELF | KEEP |
| Your hooks | KEEP |

---

## What You're Adding

### wshobson/agents

**Source:** https://github.com/wshobson/agents

**What it provides:**
- 99 specialized agents across domains
- 107 progressive-disclosure skills
- 67 plugins (install only what you need)
- Model tiering (Opus/Sonnet/Haiku)

**Model Distribution:**
- Tier 1 (Opus): 42 agents - architecture, security, code review
- Tier 2 (Inherit): 42 agents - flexible specialists
- Tier 3 (Sonnet): 51 agents - docs, testing, debugging
- Tier 4 (Haiku): 18 agents - fast operational tasks

---

## What You're Keeping (Everything)

| Component | Location | Status |
|-----------|----------|--------|
| Blackboard coordination | `.coordination/blackboard.json` | KEEP |
| basic-memory | MCP server | KEEP |
| ELF learning | `~/.claude/emergent-learning/` | KEEP |
| Golden Rules | `memory/golden-rules.md` | KEEP |
| 40+ Hooks | `~/.claude/hooks/` | KEEP |
| Your swarm skill | `~/.claude/commands/swarm.md` | UPDATE |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         /swarm                                   │
│                                                                  │
│   1. Parse task                                                 │
│   2. Show agent picker (NEW)                                    │
│   3. Spawn selected agents                                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                v
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT POOL (wshobson/agents)                   │
│                                                                  │
│   backend-development plugin:                                   │
│   ├─ api-architect (Opus)                                       │
│   ├─ backend-developer (Sonnet)                                 │
│   └─ database-specialist (Sonnet)                               │
│                                                                  │
│   security-hardening plugin:                                    │
│   ├─ security-specialist (Opus)                                 │
│   ├─ vulnerability-analyst (Opus)                               │
│   └─ penetration-tester (Sonnet)                                │
│                                                                  │
│   code-quality plugin:                                          │
│   ├─ code-reviewer (Opus)                                       │
│   ├─ refactoring-specialist (Sonnet)                            │
│   └─ performance-analyst (Sonnet)                               │
│                                                                  │
│   infrastructure plugin:                                        │
│   ├─ devops-engineer (Sonnet)                                   │
│   ├─ kubernetes-specialist (Sonnet)                             │
│   └─ cloud-architect (Opus)                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                v
┌─────────────────────────────────────────────────────────────────┐
│                   YOUR BLACKBOARD (unchanged)                    │
│                                                                  │
│   .coordination/blackboard.json                                 │
│   ├─ agents: [spawned agents register here]                     │
│   ├─ findings: [results aggregate here]                         │
│   ├─ task_queue: [work distribution]                            │
│   └─ messages: [inter-agent communication]                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                v
┌─────────────────────────────────────────────────────────────────┐
│                   YOUR MEMORY (unchanged)                        │
│                                                                  │
│   ELF            │  basic-memory                                │
│   ├─ Golden Rules │  ├─ ChromaDB                                │
│   ├─ Heuristics   │  └─ Semantic search                         │
│   └─ Learnings    │                                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                v
┌─────────────────────────────────────────────────────────────────┐
│                   YOUR HOOKS (unchanged)                         │
│                                                                  │
│   PreToolUse: context injection, golden rule enforcement        │
│   PostToolUse: learning capture                                 │
│   SessionEnd: heuristic consolidation                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Install wshobson/agents

### Step 1.1: Add Marketplace

```bash
/plugin marketplace add wshobson/agents
```

### Step 1.2: Install Core Plugins (4 to start)

```bash
/plugin install backend-development    # API, backend, database agents
/plugin install code-quality           # Review, refactoring, performance agents
/plugin install security-hardening     # Security, vulnerability, pentest agents
/plugin install infrastructure         # DevOps, K8s, cloud agents
```

### Step 1.3: Verify Installation

After install, check that new agents appear in available subagent types.

---

## Phase 2: Update /swarm Skill

### Current Behavior

Your swarm spawns generic agents without selection.

### New Behavior

```
User: /swarm "build authentication system"

Swarm: Analyzing task... Recommended agents:

  SECURITY (required for auth):
  [x] security-specialist (Opus) - Auth patterns, threat modeling
  [x] vulnerability-analyst (Opus) - Security review

  BACKEND (core implementation):
  [x] api-architect (Opus) - API design
  [x] backend-developer (Sonnet) - Implementation
  [x] database-specialist (Sonnet) - Schema design

  QUALITY (verification):
  [ ] code-reviewer (Opus) - Code review
  [ ] test-writer (Haiku) - Test coverage

  [Start] [Auto-select all] [Cancel]
```

### Implementation

Update `~/.claude/commands/swarm.md` to:
1. Parse the task description
2. Match against agent capabilities
3. Present agent picker
4. Spawn selected agents with Task tool
5. Feed to blackboard coordination

---

## Phase 3: Test

1. Run `/swarm "simple task"`
2. Verify agent picker appears
3. Select agents
4. Verify they spawn and register with blackboard
5. Verify coordination works as before

---

## Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `~/.claude/commands/swarm.md` | UPDATE | Add agent picker logic |
| Nothing else | - | Everything else unchanged |

---

## Verification Checklist

After installation:

- [x] wshobson/agents repository cloned to ~/.claude/agents/
- [x] 100 unique agent definitions available
- [x] Agent catalog created at ~/.claude/agents/agent-catalog.json
- [x] `/swarm` updated with agent picker instructions
- [ ] Selected agents spawn correctly (test pending)
- [ ] Blackboard coordination still works (test pending)
- [ ] ELF hooks still fire (test pending)
- [ ] basic-memory still works (test pending)
- [ ] `/checkin` still works (test pending)

---

## Rollback Plan

If it breaks:

```bash
# Remove wshobson plugins
/plugin uninstall backend-development
/plugin uninstall code-quality
/plugin uninstall security-hardening
/plugin uninstall infrastructure

# Revert swarm.md to previous version
git checkout ~/.claude/commands/swarm.md

# Everything else was never touched
```

---

## What We Decided NOT to Do

| Skipped | Why |
|---------|-----|
| claude-flow | Don't need it - adds complexity, risk |
| Hive-Mind | Your blackboard works fine |
| AgentDB | basic-memory + ELF sufficient |
| 100 MCP tools | Mostly redundant |

**KISS principle applied.**

---

## Success Criteria

1. 99 agents available to choose from
2. Agent picker in `/swarm` works
3. Everything else unchanged
4. No new dependencies beyond wshobson plugins
5. Rollback is trivial if needed

---

## Notes for New Session

1. **Read this file first**
2. **Install wshobson plugins** (Phase 1)
3. **Update swarm skill** (Phase 2)
4. **Test** (Phase 3)
5. **Don't overcomplicate** - KISS

---

## Installation Details

- **Repository:** `~/.claude/agents/` (cloned from wshobson/agents)
- **Agent catalog:** `~/.claude/agents/agent-catalog.json`
- **Unique agents:** 100
- **Plugins:** 67 categories
- **Updated skill:** `~/.claude/commands/swarm.md`

## Source Reference

- **wshobson/agents:** https://github.com/wshobson/agents
