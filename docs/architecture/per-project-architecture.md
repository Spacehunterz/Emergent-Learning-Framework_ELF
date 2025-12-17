# ELF Per-Project Architecture

## Overview

ELF evolves from a system-wide learning framework to a hierarchical model where learnings exist at appropriate scope levels. Universal truths live globally; project-specific knowledge lives with the project.

---

## Directory Structure

### Global Layer (`~/.claude/emergent-learning/`)

The framework installation. Contains universal knowledge and infrastructure.

```
~/.claude/emergent-learning/
├── memory/
│   ├── global.db              # Universal learnings only
│   └── golden-rules.md        # Constitutional principles
├── query/                     # Framework code
├── scripts/                   # Recording tools
├── agents/                    # Personas
└── CLAUDE.md                  # Framework instructions
```

### Project Layer (`<project-root>/.elf/`)

Project-specific knowledge. Git-trackable. Travels with code.

```
<any-project>/
├── .elf/
│   ├── config.yaml            # Project configuration
│   ├── context.md             # "What is this project" (LLM-readable)
│   ├── learnings.db           # Project-specific database
│   ├── heuristics/            # Markdown heuristics (optional, for git diff)
│   │   └── *.md
│   ├── experiments/           # Active experiments
│   │   └── *.md
│   └── decisions/             # Project ADRs
│       └── *.md
├── .gitignore                 # Includes .elf/learnings.db if desired
└── ... (project files)
```

---

## What Lives Where

### Global (Universal Truths)

Knowledge that applies regardless of project:

| Type | Examples |
|------|----------|
| Golden Rules | "Query before acting", "Document failures immediately" |
| Language Patterns | "useEffect deps cause loops", "await every Promise" |
| Tool Behaviors | "Claude Code needs PowerShell on Windows" |
| Platform Quirks | "CRLF breaks bash scripts", "Unicode filenames crash JS engine" |
| Security Rules | "Never log secrets", "Validate at boundaries" |

**Criteria for global:** Would this help ANY project using this language/tool?

### Project-Specific (Contextual Knowledge)

Knowledge that only makes sense for THIS project:

| Type | Examples |
|------|----------|
| Architecture Decisions | "We use factory pattern for services" |
| API Conventions | "Backend returns snake_case, frontend uses camelCase" |
| Code Patterns | "All components extend BaseComponent" |
| Domain Knowledge | "Users can have multiple organizations" |
| Historical Context | "Auth was refactored in v2, old patterns in /legacy" |
| Team Preferences | "Prefer explicit over implicit" |
| Failure History | "The payment module is fragile, test thoroughly" |

**Criteria for project:** Would this confuse someone working on a DIFFERENT project?

### Promotion Path

```
Project heuristic (confidence 0.7)
    ↓ validated across 3+ projects
    ↓ CEO review
Global heuristic (confidence 0.9+)
    ↓ 10+ validations
    ↓ CEO promotion
Golden Rule
```

---

## Project Detection

### Initialization

When Claude starts in a directory:

```python
def detect_project_root(cwd):
    """Walk up until we find project markers."""
    markers = ['.elf', '.git', 'package.json', 'Cargo.toml',
               'pyproject.toml', 'go.mod', '.project-root']

    current = cwd
    while current != parent(current):
        for marker in markers:
            if exists(join(current, marker)):
                return current
        current = parent(current)

    return cwd  # Fallback to cwd if no markers
```

### Context Variables

Query system sets these for all operations:

```bash
ELF_PROJECT_ROOT=/path/to/project     # Detected root
ELF_PROJECT_NAME=my-project           # From config or dirname
ELF_PROJECT_DB=/path/to/.elf/learnings.db
ELF_GLOBAL_DB=~/.claude/emergent-learning/memory/global.db
```

---

## Query Behavior

### Context Query (`query.py --context`)

Merges both layers intelligently:

```
# TIER 0: Project Context (if .elf/context.md exists)
"This is a React dashboard for analytics..."

# TIER 1: Golden Rules (always, from global)
1. Query before acting
2. Document failures immediately
...

# TIER 2: Relevant Heuristics
## Global (high-confidence, domain-matched)
- "useEffect deps cause loops" (react, 0.95)

## Project-Specific
- "API endpoints live in /src/api/*.ts" (0.80)
- "Use TanStack Query for data fetching" (0.85)

# TIER 3: Recent Learnings
## Global (last 7 days, domain-matched)
...

## Project (last 30 days)
- "Fixed auth bug by clearing token on 401"
...
```

### Domain Filtering

```bash
# Global patterns for domain
query.py --domain react

# Project patterns only
query.py --project-only

# Both (default)
query.py --context
```

---

## Recording Behavior

### Heuristic Recording

Interactive prompt determines scope:

```bash
$ python record-heuristic.py

Rule: "Always null-check user.organization before accessing"

Where should this live?
  [1] Project - Only applies to this codebase
  [2] Global  - Universal pattern for any project

> 1

Recorded to: /path/to/project/.elf/learnings.db
```

Or explicit flag:

```bash
# Project-specific (default when in project)
record-heuristic.py --rule "..." --project

# Global (requires justification)
record-heuristic.py --rule "..." --global --justification "Universal React pattern"
```

### Automatic Scope Detection

Heuristics mentioning project-specific terms auto-suggest project scope:

```python
PROJECT_INDICATORS = [
    r'\b(this codebase|this project|our API|our backend)\b',
    r'\b(src/|components/|modules/)\b',  # Path references
    r'\bwe (use|prefer|always)\b',
]

GLOBAL_INDICATORS = [
    r'\b(always|never|every)\b.*\b(in React|in Python|on Windows)\b',
    r'\b(library|framework|language) (requires|needs)\b',
]
```

---

## Project Initialization

### New Project Setup

```bash
$ cd ~/my-new-project
$ elf init

Initializing ELF for: my-new-project
Created: .elf/config.yaml
Created: .elf/context.md (please edit)
Created: .elf/learnings.db

Add to .gitignore? [Y/n] y
Added: .elf/learnings.db

✓ ELF initialized. Edit .elf/context.md to describe your project.
```

### config.yaml

```yaml
project:
  name: my-new-project
  description: "React dashboard for analytics"

domains:
  - react
  - typescript
  - tanstack-query

inherit_global:
  golden_rules: true          # Always inherit
  heuristics:
    domains: [react, typescript]  # Only these domains
    min_confidence: 0.8       # Only high-confidence

team:
  share_heuristics: true      # Git-track heuristics as markdown
```

### context.md

```markdown
# Project Context

## What This Is
A React-based analytics dashboard for internal use.

## Tech Stack
- React 18 + TypeScript
- TanStack Query for data fetching
- Tailwind CSS
- Vite for bundling

## Key Architecture Decisions
- Feature-based folder structure (/features/auth, /features/dashboard)
- All API calls go through /src/api/client.ts
- State management via React Context (no Redux)

## Known Quirks
- Legacy auth code in /src/legacy - don't touch
- API returns snake_case, we transform to camelCase in client.ts

## Team Conventions
- Prefer explicit prop types over inference
- No barrel exports (index.ts re-exports)
```

---

## Database Schema Changes

### Global DB (`~/.claude/emergent-learning/memory/global.db`)

```sql
-- Existing tables, add source tracking
ALTER TABLE heuristics ADD COLUMN source_project TEXT;  -- Which project discovered this
ALTER TABLE heuristics ADD COLUMN promoted_from_project BOOLEAN DEFAULT FALSE;

-- Track cross-project validation
CREATE TABLE cross_project_validations (
    heuristic_id INTEGER,
    project_name TEXT,
    validated_at TIMESTAMP,
    outcome TEXT  -- 'confirmed' | 'contradicted'
);
```

### Project DB (`<project>/.elf/learnings.db`)

```sql
-- Lightweight schema, project-specific only
CREATE TABLE heuristics (
    id INTEGER PRIMARY KEY,
    rule TEXT NOT NULL,
    explanation TEXT,
    domain TEXT,
    confidence REAL DEFAULT 0.7,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_validated TIMESTAMP,
    validation_count INTEGER DEFAULT 0,
    promoted_to_global BOOLEAN DEFAULT FALSE
);

CREATE TABLE learnings (
    id INTEGER PRIMARY KEY,
    type TEXT,  -- 'success' | 'failure' | 'observation'
    summary TEXT,
    details TEXT,
    domain TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    name TEXT,
    hypothesis TEXT,
    status TEXT,  -- 'active' | 'concluded'
    outcome TEXT,
    created_at TIMESTAMP,
    concluded_at TIMESTAMP
);
```

---

## CLI Changes

### New Commands

```bash
# Initialize project
elf init

# Show current context
elf status
# Output:
# Project: my-dashboard (/home/user/my-dashboard)
# Global:  ~/.claude/emergent-learning
# Heuristics: 12 project, 847 global
# Last learning: 2 hours ago

# Query with explicit scope
elf query --project-only
elf query --global-only
elf query --context  # merged (default)

# Record with scope
elf record heuristic --project "..."
elf record heuristic --global "..." --justification "..."

# Promote project heuristic to global
elf promote <heuristic-id> --justification "Validated across 3 projects"

# Export project heuristics to markdown (for git)
elf export heuristics --format markdown --output .elf/heuristics/

# Import team heuristics from markdown
elf import heuristics .elf/heuristics/
```

### Updated CLAUDE.md Instructions

```markdown
## Project Context

ELF operates at two levels:

1. **Global** (`~/.claude/emergent-learning/`) - Universal truths
2. **Project** (`.elf/` in project root) - Project-specific knowledge

When you query the building, you get BOTH merged intelligently.

### Recording Learnings

Default scope is PROJECT when inside a project:

```bash
# Records to current project
python ~/.claude/emergent-learning/scripts/record-heuristic.py \
  --rule "Our API uses pagination tokens, not page numbers"

# Records to global (requires justification)
python ~/.claude/emergent-learning/scripts/record-heuristic.py \
  --rule "React StrictMode causes double renders" \
  --global \
  --justification "Universal React behavior"
```

### Project Initialization

When starting work on a new project:

```bash
cd /path/to/project
python ~/.claude/emergent-learning/scripts/init-project.py
# Then edit .elf/context.md to describe the project
```
```

---

## Migration Path

### Phase 1: Add Project Support (Non-Breaking)

1. Add `.elf/` detection to query.py
2. Add `--project` flag to recording scripts
3. Keep global as default
4. Projects opt-in via `elf init`

### Phase 2: Smart Defaults

1. If `.elf/` exists, default recordings to project
2. Query merges both automatically
3. Add promotion workflow

### Phase 3: Full Per-Project

1. New projects always have `.elf/`
2. Global becomes truly universal
3. Cross-project validation tracking

---

## Design Decisions

### 1. Database vs Markdown: Hybrid Approach

**Decision:** SQLite for operations, markdown export for git.

```
.elf/
├── learnings.db          # .gitignore'd - local working DB
├── heuristics/           # git-tracked - team knowledge
│   ├── api-patterns.md
│   └── auth-quirks.md
└── sync-manifest.json    # Tracks what's exported
```

**Why hybrid:**
- DB for fast queries, confidence scores, validation counts
- Markdown for human review, git diffs, team discussion
- No merge conflicts on binary files
- Team members import markdown → local DB on pull

**Workflow:**
```bash
# Before commit: export new heuristics to markdown
elf export --auto   # Only exports new/changed since last sync

# After pull: import team's new heuristics
elf import --auto   # Only imports new/changed markdown

# Or: git hook handles this automatically
```

**Export format:**
```markdown
---
id: h-api-001
confidence: 0.85
domain: api
created: 2025-12-16
validated: 3
---

# API returns cursor-based pagination

Our API uses `next_cursor` tokens, not page numbers. Always check for
`next_cursor` in response to know if more pages exist.

## Context
Discovered when implementing infinite scroll in dashboard.

## Validation History
- 2025-12-16: Confirmed in /features/users
- 2025-12-17: Confirmed in /features/analytics
- 2025-12-18: Confirmed in /features/reports
```

---

### 2. Monorepo Handling: Hierarchical Inheritance

**Decision:** Support nested `.elf/` with inheritance.

```
monorepo/
├── .elf/                          # Root config
│   ├── config.yaml
│   └── context.md                 # "This is our platform monorepo"
├── packages/
│   ├── web-app/
│   │   └── .elf/                  # Package-specific
│   │       ├── config.yaml        # inherits_from: ../..
│   │       └── context.md         # "React frontend"
│   ├── api/
│   │   └── .elf/
│   │       └── context.md         # "Node.js API"
│   └── shared/
│       └── .elf/
│           └── context.md         # "Shared utilities"
```

**Resolution order (closest wins):**
```
1. Current directory's .elf/
2. Parent .elf/ (if inherits_from set)
3. Root .elf/ (if inherits_from chains up)
4. Global ~/.claude/emergent-learning/
```

**config.yaml inheritance:**
```yaml
# packages/web-app/.elf/config.yaml
project:
  name: web-app
  inherits_from: ../..    # Inherit root monorepo config

domains:
  - react                  # Package-specific
  # Also gets parent domains via inheritance
```

**Query in monorepo:**
```bash
$ cd monorepo/packages/web-app
$ elf query --context

# Project Context Chain:
# 1. web-app: React frontend for analytics
# 2. monorepo: Our platform monorepo (shared conventions)

# Heuristics merged from:
# - web-app/.elf/ (12 heuristics)
# - monorepo/.elf/ (8 heuristics, inherited)
# - global (domain-filtered)
```

**Recording in monorepo:**
```bash
$ elf record heuristic "..."

Where should this live?
  [1] web-app - Only this package
  [2] monorepo - All packages in this repo
  [3] global - Universal pattern

> 2
Recorded to: monorepo/.elf/
```

---

### 3. Project Detection: Explicit `.elf/` Required

**Decision:** Only `.elf/` presence triggers project mode. Other markers just find root.

**Rationale:**
- `.git` is too common - not every repo wants ELF
- Explicit opt-in via `elf init` is cleaner
- Prevents accidental project-scoping in random directories
- User controls when a project "joins" ELF

**Detection logic:**
```python
def get_context():
    cwd = os.getcwd()

    # Find project root (for context, even without .elf/)
    project_root = find_root_by_markers(cwd, ['.git', 'package.json', ...])

    # Check if ELF is initialized
    elf_root = find_elf_root(cwd)  # Walks up looking for .elf/

    if elf_root:
        return ProjectContext(
            mode='project',
            project_root=elf_root,
            project_db=f'{elf_root}/.elf/learnings.db',
            global_db=GLOBAL_DB
        )
    else:
        return ProjectContext(
            mode='global-only',
            project_root=project_root,  # Still useful for context
            project_db=None,
            global_db=GLOBAL_DB
        )
```

**Behavior by mode:**

| Action | `.elf/` exists | No `.elf/` |
|--------|---------------|------------|
| Query | Merged global + project | Global only |
| Record heuristic | Default to project | Global only |
| Record failure | Default to project | Global only |
| `elf init` | Already initialized | Creates `.elf/` |

**First-run experience:**
```bash
$ cd ~/my-project
$ elf query --context

No .elf/ found. Showing global context only.
Run `elf init` to enable project-specific learnings.

# TIER 1: Golden Rules
...
```

---

### 4. context.md: Optional but Prompted

**Decision:** Optional, but `elf init` prompts and Claude nudges if missing.

**Rationale:**
- Low friction > enforcement
- Empty/missing context.md still works
- Value becomes obvious once used
- Claude can prompt: "I notice no context.md - want me to draft one?"

**Initialization flow:**
```bash
$ elf init

Initializing ELF for: my-project

Created: .elf/config.yaml
Created: .elf/learnings.db
Created: .elf/context.md (template)

📝 Describe your project in .elf/context.md
   This helps Claude understand your codebase.
   (Optional but recommended)

$ cat .elf/context.md
# Project Context

<!--
Describe your project for Claude. Include:
- What this project does
- Tech stack
- Key architectural decisions
- Team conventions
- Known quirks or gotchas
-->

## Overview
[Describe your project here]

## Tech Stack
-

## Architecture
-

## Conventions
-
```

**Claude behavior with missing context:**
```
# In query output when context.md is empty/missing:

⚠️ No project context found.

Consider creating .elf/context.md to help me understand:
- What this project does
- Tech stack and patterns
- Team conventions

Would you like me to draft one based on the codebase?
```

**Auto-generation option:**
```bash
$ elf init --auto-context

Analyzing codebase...
- Detected: React, TypeScript, Vite
- Found: /src/api/, /src/components/, /src/features/
- Package.json description: "Analytics dashboard"

Generated .elf/context.md (please review and edit)
```

---

## Implementation Priority

| Phase | Feature | Effort | Value |
|-------|---------|--------|-------|
| 1 | `.elf/` detection + project DB | Medium | High |
| 1 | `elf init` command | Low | High |
| 1 | Query merges global + project | Medium | High |
| 2 | Recording defaults to project | Low | Medium |
| 2 | Markdown export/import | Medium | High |
| 2 | context.md prompt in Claude | Low | Medium |
| 3 | Monorepo inheritance | High | Medium |
| 3 | Auto-context generation | Medium | Low |
| 3 | Git hooks for sync | Medium | Medium |

---

## Summary

| Aspect | Current (System-Wide) | Proposed (Per-Project) |
|--------|----------------------|------------------------|
| Database | One global DB | Global + per-project DBs |
| Scope | Everything mixed | Clear separation |
| Portability | None | Project travels with code |
| Team sharing | Not possible | Git-track project learnings |
| Query | All learnings | Merged intelligently |
| Recording | Always global | Default to project |
| Golden rules | Global | Global (unchanged) |
