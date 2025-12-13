# Teaching Claude to Remember
## Emergent Learning Framework for Claude Code

**A talk for developers who are tired of repeating themselves**

---

## The Problem: Claude Has Amnesia

```bash
# Session 1 - Monday 9am
You: "Write a React hook for data fetching with cleanup"
Claude: *creates useDataFetch with proper cleanup*
You: "Perfect!"

# Session 2 - Monday 11am
You: "Write another data fetching hook"
Claude: *creates hook WITHOUT cleanup* 🤦
You: "We literally just discussed cleanup 2 hours ago..."
Claude: "I have no memory of previous conversations"
```

**Every session = fresh start = zero institutional knowledge**

---

## The Cost of Amnesia

**What gets lost between sessions:**
- Lessons learned from failures
- Patterns that work in YOUR codebase
- Architecture decisions you've made
- Bugs you've already fixed
- Code style preferences
- Domain knowledge

**Reality check:**
- Average developer has ~8-12 Claude sessions/day
- Each session: 0% knowledge retention from previous ones
- You're teaching the same lessons repeatedly

---

## The Core Insight

```
┌─────────────────────────────────────────────────┐
│  WRONG MENTAL MODEL:                            │
│  "Claude" is persistent                         │
│                                                 │
│  CORRECT MENTAL MODEL:                          │
│  Claude instances are disposable workers       │
│  The building they work in is permanent        │
└─────────────────────────────────────────────────┘
```

**Separate the agent from the institution**

---

## Architecture: The Building Metaphor

```
          Session 1          Session 2          Session 3
             🧠                 🧠                 🧠
        (Claude temp)      (Claude temp)      (Claude temp)
             ↓                  ↓                  ↓
        ┌────────────────────────────────────────────┐
        │           THE BUILDING (Permanent)         │
        │  ┌──────────────────────────────────────┐ │
        │  │ SQLite: Failures, Patterns, Rules    │ │
        │  │ Heuristics: confidence scores 0→1    │ │
        │  │ Golden Rules: proven principles      │ │
        │  │ Pheromone Trails: file hotspots      │ │
        │  └──────────────────────────────────────┘ │
        └────────────────────────────────────────────┘
             ↑                  ↑                  ↑
          QUERY              APPLY              LEARN
```

---

## Technical Stack

**Backend:**
```python
FastAPI + Uvicorn      # Async REST + WebSocket
SQLite3 + aiosqlite    # Local persistent storage
Python 3.8+            # Core query/validation system
```

**Frontend:**
```javascript
React 18 + TypeScript  # Dashboard UI
Vite                   # Fast builds
D3.js                  # Visualizations
TailwindCSS            # Styling
```

**Data:**
```sql
-- Schema overview
workflows          # Multi-agent workflow definitions
workflow_runs      # Execution instances
node_executions    # Individual agent tasks
heuristics         # Learned patterns (confidence: 0.0→1.0)
golden_rules       # High-confidence principles
pheromone_trails   # File activity tracking
```

---

## The Learning Loop

```python
def emergent_learning_cycle():
    while True:
        # 1. TRY
        outcome = attempt_task(current_knowledge)

        # 2. BREAK (or succeed)
        result = evaluate(outcome)

        # 3. ANALYZE
        principle = extract_lesson(result)

        # 4. LEARN
        if principle.validated:
            heuristic = store_pattern(principle)
            heuristic.confidence += 0.1

            if heuristic.confidence > 0.9:
                promote_to_golden_rule(heuristic)

        # 5. NEXT
        current_knowledge = load_building()
```

---

## Database Schema Deep Dive

```sql
-- Heuristics: Patterns gain confidence through validation
CREATE TABLE heuristics (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,           -- "Always cleanup useEffect"
    domain TEXT,                      -- "react", "testing", "security"
    confidence REAL DEFAULT 0.0,     -- 0.0 → 1.0
    validation_count INTEGER,         -- Times pattern proved correct
    tags TEXT,                        -- JSON array for search
    created_at DATETIME,
    last_validated DATETIME
);

-- Node Executions: Every agent task recorded
CREATE TABLE node_executions (
    id INTEGER PRIMARY KEY,
    run_id INTEGER,
    node_id TEXT,                    -- Validated identifier
    prompt TEXT,                     -- Full context
    prompt_hash TEXT,                -- Deduplication
    result_json TEXT,                -- Structured output
    findings_json TEXT,              -- Extracted learnings
    files_modified TEXT,             -- Pheromone trail
    duration_ms INTEGER,
    status TEXT                      -- pending|completed|failed
);
```

---

## Security: Defense in Depth

**Layer 1: Input Validation**
```python
# conductor/validation.py
def validate_identifier(value: str, name: str, max_length=100):
    """Prevents command injection, path traversal"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValidationError(f"Invalid {name}")

    # Blocks: ; | & $ ` ../ quotes newlines wildcards
    return value

# Every node_id, workflow_id, agent_id validated before use
```

**Layer 2: Parameterized SQL**
```python
# NEVER string concatenation
cursor.execute("SELECT * FROM heuristics WHERE domain = ?", (domain,))
```

**Layer 3: Subprocess Lists**
```python
# NEVER shell=True
subprocess.run(["claude", "-p", prompt], env=validated_env)
```

---

## Security Audit Results

**Recent Audit (2025-12-10):**
- ✅ Comprehensive input validation
- ✅ All SQL queries parameterized
- ✅ No shell=True in subprocess calls
- ✅ CORS restricted to localhost
- ✅ Security headers (XSS, clickjacking, MIME sniffing)
- ✅ Test coverage: 86 subtests, all passing

**Attack patterns blocked:**
```bash
node; rm -rf /           # Command chaining
node$(whoami)            # Command substitution
../../../etc/passwd      # Path traversal
node | grep secrets      # Shell metacharacters
node'malicious'          # Quote injection
```

**Status: SECURE** (for local dev tool threat model)

---

## Demo Time: Watch It Learn

**Initial state:**
```bash
$ python query.py --stats
Total heuristics: 0
Golden rules: 0
Sessions: 0
```

**Let's make a mistake intentionally:**

---

## Demo: Failure Analysis

```javascript
// Session 1: Bad code
You: "Create a React component that polls an API every second"

Claude creates:
function PollComponent() {
  useEffect(() => {
    setInterval(() => {
      fetch('/api/data').then(r => r.json());
    }, 1000);
  }, []);
  // ⚠️ NO CLEANUP!
}

You: "This leaks memory! Record failure:
     'Always cleanup intervals in useEffect'"
```

---

## Demo: Learning Recorded

**Database after failure:**
```sql
INSERT INTO heuristics (
    pattern: "Always cleanup setInterval in useEffect return function",
    domain: "react",
    confidence: 0.3,  -- Initial confidence
    tags: ["react", "hooks", "cleanup", "memory-leak"]
);

INSERT INTO failure_analysis (
    what_went_wrong: "setInterval without cleanup causes memory leak",
    lesson: "useEffect must return cleanup function for subscriptions"
);
```

**Dashboard shows:**
- 🔴 New failure recorded
- 📊 Heuristic created: confidence 0.3
- 🎯 Suggested golden rule candidate

---

## Demo: Pattern Reinforcement

```javascript
// Session 2 (new Claude instance)
You: "check in"
Claude: *loads building knowledge*
       "I see we have a pattern about useEffect cleanup..."

You: "Create a component that fetches data on mount"

Claude creates:
function DataComponent() {
  useEffect(() => {
    let cancelled = false;

    fetch('/api/data')
      .then(r => r.json())
      .then(data => {
        if (!cancelled) setData(data);
      });

    return () => { cancelled = true; }; // ✅ CLEANUP!
  }, []);
}
```

**Confidence increases:** 0.3 → 0.6

---

## Demo: Promotion to Golden Rule

**After 3-4 successful applications:**
```sql
UPDATE heuristics
SET confidence = 0.95
WHERE pattern LIKE '%useEffect cleanup%';

-- Auto-promotion at confidence > 0.9
INSERT INTO golden_rules (
    rule: "useEffect cleanup pattern",
    principle: "Always return cleanup function for subscriptions",
    category: "react_fundamentals",
    auto_load: true  -- Loaded EVERY session
);
```

**Now:**
- ✅ Loaded automatically without query
- ✅ Applied to all future useEffect code
- ✅ Institutional knowledge established

---

## Cross-Session Continuity

**Natural language search over session history:**

```bash
# CLI
$ python session_integration.py search "what did we discuss about React?"

# Or in Claude session
You: "/search what was I working on with authentication last week?"

Claude: "Found 3 sessions:
  - 2025-12-06: JWT token refresh pattern
  - 2025-12-05: OAuth2 flow implementation
  - 2025-12-04: Password hashing with bcrypt

  Most relevant: JWT refresh pattern..."
```

**Token cost:** ~500 tokens (lightweight RAG)

---

## Dashboard: Visual Knowledge Explorer

**localhost:3001**

**Tabs:**
1. **Overview** - Stats, recent activity, golden rules count
2. **Heuristics** - All patterns with confidence scores
3. **Graph** - Interactive knowledge graph (D3.js force-directed)
4. **Hotspots** - Treemap of file activity
5. **Sessions** - Searchable conversation history
6. **Analytics** - Learning velocity over time

**Real-time updates via WebSocket**

---

## Hotspots: Pheromone Trails

```javascript
// Every file modification tracked
{
  "file_path": "src/components/Auth.tsx",
  "touch_count": 47,      // Modified 47 times across sessions
  "last_touched": "2025-12-13T10:30:00Z",
  "agents": ["architect", "skeptic"],
  "sessions": [...]
}

// Visualized as treemap
┌────────────────────────────────────────┐
│  src/                                  │
│  ┌─────────────────┬────────────────┐ │
│  │ Auth.tsx (47)   │ Dashboard (23) │ │
│  │ 🔥 HOT          │                │ │
│  ├─────────┬───────┴────────────────┤ │
│  │ API (12)│ Utils (8)              │ │
│  └─────────┴────────────────────────┘ │
└────────────────────────────────────────┘
```

**Use case:** "Why is Auth.tsx so hot? Is it a problem magnet?"

---

## Swarm: Multi-Agent Coordination

**Blackboard pattern for parallel execution:**

```bash
You: "/swarm investigate the authentication system"

# Spawns 4 specialized agents in parallel:
┌──────────────┬────────────────────────────────┐
│ RESEARCHER   │ "Gathering OAuth2 best        │
│              │  practices from docs..."       │
├──────────────┼────────────────────────────────┤
│ ARCHITECT    │ "Mapping token flow:           │
│              │  Login→JWT→Refresh→Logout"     │
├──────────────┼────────────────────────────────┤
│ SKEPTIC      │ "Found issue: No rate limiting │
│              │  on /auth/login endpoint"      │
├──────────────┼────────────────────────────────┤
│ CREATIVE     │ "Idea: Add biometric fallback  │
│              │  for passwordless auth"        │
└──────────────┴────────────────────────────────┘

# Results aggregated to shared blackboard
# Synthesized by conductor into final report
```

---

## Swarm Architecture

```python
# conductor/conductor.py
class Conductor:
    def execute_swarm(self, node: Node, context: dict):
        """Parallel agent execution with coordination"""

        # 1. Create blackboard
        blackboard = Blackboard(run_id=self.run_id)

        # 2. Spawn agents in parallel
        agents = ["researcher", "architect", "skeptic", "creative"]
        tasks = [
            self._spawn_agent(agent, node.prompt, blackboard)
            for agent in agents
        ]

        # 3. Wait for completion with timeout
        results = await asyncio.gather(*tasks, timeout=300)

        # 4. Synthesize findings
        synthesis = self._synthesize(results, blackboard)

        # 5. Record to database
        self._record_execution(node, synthesis)

        return synthesis
```

---

## Async Watcher: Tiered Monitoring

**Problem:** Constant Opus monitoring = expensive
**Solution:** Haiku watches, Opus escalates when needed

```python
# Tier 1: Haiku checks every 30s (~$0.001/check)
while coordination_active():
    status = haiku.check_blackboard()

    if status.needs_attention:
        # Tier 2: Escalate to Opus (~$0.10/call)
        opus.deep_analysis(status.context)

    time.sleep(30)

# 95% cost reduction vs constant Opus
```

**Runs in background, zero user interaction required**

---

## Token Economics

**Per session costs:**
```
Golden rules load:        ~500 tokens   ($0.0015)
Domain query:           ~2-5k tokens   ($0.006-$0.015)
Session search:          ~500 tokens   ($0.0015)
Heavy history review:   ~20k tokens   ($0.06)

Daily cost (10 sessions): ~$0.10-0.50
Monthly:                  ~$3-15

Compare to: Re-explaining context manually
            ~10k tokens/session × 10 = 100k tokens/day
            = $0.30/day just repeating yourself
            = $9/month wasted on repetition
```

**ROI: Positive after week 1**

---

## Installation: 2 Minutes

```bash
# Clone
git clone https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF
cd Emergent-Learning-Framework_ELF

# Install (Mac/Linux)
./install.sh

# Or Windows
./install.ps1

# Installs to ~/.claude/emergent-learning/
# Components:
#   - Core query system (Python + SQLite)
#   - Dashboard (React + FastAPI)
#   - Hooks (SessionStart, ToolUse)
#   - Slash commands (/search, /checkin, /swarm)
#   - Golden rules templates
```

**Requirements:** Python 3.8+, Bun/Node (for dashboard)

---

## First Session Workflow

```bash
# 1. Start Claude Code session
claude

# 2. Check in (most important command)
You: "check in"

# Auto-setup on first run:
# - Detects fresh install
# - Creates CLAUDE.md (global config)
# - Starts dashboard (localhost:3001)
# - Returns golden rules + stats

# 3. Work normally
You: "Help me debug this API endpoint"

# 4. Record learnings (manual or automatic via hooks)
You: "record failure: Don't use sync fs operations in async handlers"

# 5. Check dashboard
# See heuristics, confidence scores, session history
```

**After week 1:** Noticeable reduction in repeated explanations
**After month 1:** Institutional knowledge accumulates visibly

---

## Use Cases: When ELF Shines

**1. Onboarding new codebases**
- Record architecture decisions as you learn
- Build domain knowledge automatically
- Future sessions have context immediately

**2. Bug pattern recognition**
- "We fixed this type of bug before..."
- Heuristics prevent regression
- Pheromone trails show problem areas

**3. Code review automation**
- Golden rules encode team standards
- Auto-applied in every session
- Consistent enforcement

**4. Experiment tracking**
- Record what worked/didn't work
- Build evidence-based heuristics
- A/B test approaches systematically

---

## Technical Deep Dive: Query System

```python
# query/query.py
class QuerySystem:
    def query_context(self, domain: str = None,
                     tags: List[str] = None,
                     limit: int = 10):
        """Tiered retrieval system"""

        # Tier 1: Always load (cheap)
        golden_rules = self._load_golden_rules()

        # Tier 2: Domain-specific (moderate)
        if domain:
            heuristics = self._query_heuristics(
                domain=domain,
                confidence_threshold=0.5,
                limit=limit
            )

        # Tier 3: Tag-based search (on-demand)
        if tags:
            related = self._search_by_tags(tags)

        # Assemble context with token budget
        return self._assemble_context(
            golden_rules, heuristics, related,
            max_tokens=5000  # Configurable
        )
```

---

## Validation: Security-First Design

```python
# conductor/validation.py - Prevents all injection attacks
def validate_identifier(value: str, name: str, max_length=100):
    """
    Validates identifiers used in:
    - Subprocess execution
    - File operations
    - Environment variables
    - SQL queries (defense in depth)
    """
    if not value or not isinstance(value, str):
        raise ValidationError(f"Invalid {name}: empty or not string")

    if len(value) > max_length:
        raise ValidationError(f"Invalid {name}: too long")

    # Only alphanumeric + underscore + hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValidationError(
            f"Invalid {name}: must contain only [a-zA-Z0-9_-]"
        )

    # Prevent edge cases
    if value[0] in '-_' or value[-1] in '-_':
        raise ValidationError(f"Invalid {name}: bad start/end char")

    return value  # Safe to use in any context
```

---

## Testing: Comprehensive Coverage

```python
# conductor/tests/test_validation.py
class TestValidation(unittest.TestCase):
    def test_blocks_command_injection(self):
        malicious_inputs = [
            "node; rm -rf /",
            "node && malicious",
            "node || cat /etc/passwd",
            "node | grep secrets",
            "node$(whoami)",
            "node`cmd`",
            "node${PATH}"
        ]
        for inp in malicious_inputs:
            with self.assertRaises(ValidationError):
                validate_node_id(inp)

    def test_blocks_path_traversal(self):
        self.assertRaises(ValidationError,
                         validate_filename_safe,
                         "../../../etc/passwd")

    # ... 86 total subtests
```

**Result:** ✅ All tests pass

---

## Limitations & Tradeoffs

**What ELF does NOT do:**
- ❌ Fine-tune the Claude model (it's RAG, not training)
- ❌ Work across different AI providers (Claude Code specific)
- ❌ Replace version control (it's not git)
- ❌ Provide multi-user auth (single-user tool)
- ❌ Work without Claude Code installed

**Tradeoffs:**
- **Token overhead:** ~500-5k tokens/session for context loading
- **Storage:** SQLite grows over time (negligible for local SSD)
- **Complexity:** Adds infrastructure (Python + Node + SQLite)
- **Local-only:** No cloud sync (by design for privacy)

**Best fit:** Individual developers on trusted machines

---

## Comparison: Similar Systems

| System | Approach | Scope | Persistence |
|--------|----------|-------|-------------|
| **ELF** | Session-level RAG | Claude Code | SQLite local |
| LangChain Memory | Conversation memory | Any LLM | Various backends |
| Vector DBs (Pinecone) | Document embedding | Any data | Cloud |
| GitHub Copilot | Code completion | Editor-level | Model training |
| Cursor AI | Codebase context | IDE | Proprietary |

**ELF's niche:** Session-to-session learning specifically for Claude Code workflows

---

## Roadmap & Future Ideas

**Short-term (community PRs welcome):**
- [ ] WAL mode for better SQLite concurrency
- [ ] Dependency scanning in CI/CD
- [ ] Export/import knowledge bases
- [ ] Conflict resolution for heuristics

**Long-term (research territory):**
- [ ] Multi-user team collaboration
- [ ] Cross-agent knowledge sharing
- [ ] Automated pattern mining from codebases
- [ ] Confidence score ML optimization
- [ ] Integration with other AI code assistants

**Community requested:**
- [ ] VS Code extension for dashboard
- [ ] Slack/Discord notifications
- [ ] Git hooks for automatic tracking

---

## Live Demo: Full Cycle

**Let's do this live...**

1. Fresh install on new machine
2. First check-in → dashboard opens
3. Deliberately create buggy code
4. Record failure analysis
5. New session → pattern applied automatically
6. Show confidence increase in dashboard
7. Search session history
8. Visualize hotspots

**If demo gods smile upon us, you'll see learning happen in real-time**

---

## Key Takeaways (TL;DR)

**1. Separate agent from institution**
   - Claude = temporary worker (amnesia)
   - Building = permanent memory (SQLite)

**2. Learning is automatic**
   - Record failures → extract principles → gain confidence
   - No manual rule writing required

**3. Knowledge compounds**
   - Week 1: 5 heuristics
   - Month 1: 50 heuristics
   - Year 1: Institutional wisdom

**4. Local-first privacy**
   - No cloud, no APIs, no data exfiltration
   - You own your knowledge base completely

**5. Production-ready security**
   - Input validation, parameterized SQL, no shell injection
   - Audited, tested, documented

---

## Resources

**GitHub:**
[github.com/Spacehunterz/Emergent-Learning-Framework_ELF](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF)

**Documentation:**
- [Installation Guide](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Installation)
- [Security Audit](conductor/SECURITY_AUDIT_2025-12-10.md)
- [Architecture Decisions](adr/)
- [Dashboard Guide](dashboard-app/README.md)

**Quick Start:**
```bash
git clone <repo>
./install.sh
# In Claude Code:
"check in"
```

**License:** MIT
**Cost:** Free, local-only
**Requirements:** Python 3.8+, Claude Code

---

## Questions?

**Common questions:**
- How does this compare to RAG? *Session-level vs document-level*
- Can I use with GPT? *Not yet, Claude Code specific*
- Security concerns? *Comprehensive audit available*
- Team usage? *Single-user, could share SQLite*
- Token costs? *~500-5k tokens/session*

**Let's discuss:**
- Your use cases
- Integration ideas
- Contribution opportunities
- Edge cases you're worried about

---

## Thank You

**Remember:**
> "The agent is temporary. The building is permanent."

**Go build something that remembers.**

---

*Slide deck created for Emergent Learning Framework*
*License: MIT | Author: Spacehunterz | Date: 2025-12-13*
