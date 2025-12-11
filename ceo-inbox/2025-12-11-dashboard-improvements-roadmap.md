# Dashboard Improvements Roadmap

**Priority:** MEDIUM
**Status:** PENDING
**Created:** 2025-12-11
**Source:** Swarm Analysis (6 agents)

---

## Situation

A comprehensive swarm analysis identified 20 creative improvement ideas for the Emergent Learning Dashboard, plus several critical bugs that need immediate attention. This document captures all findings for CEO review and prioritization.

---

## Critical Bugs (Must Fix)

These are blocking issues discovered during the audit:

| # | Bug | Impact | Effort |
|---|-----|--------|--------|
| B1 | Missing `building_queries` table | `/api/stats` and `/api/queries` crash | 5 min |
| B2 | No conductor integration in hooks | Agent runs don't appear in dashboard | 30 min |
| B3 | Outcome detection 99% broken | 131/131 outcomes are "unknown" | 2 hrs |
| B4 | Trail laying 96% broken | Only 3 trails from 80 executions | 1 hr |
| B5 | Hardcoded WebSocket URL | Won't work in production | 2 min |
| B6 | WebSocket monitors only 3 tables | Heuristics/learnings changes invisible | 15 min |
| B7 | 11 console.log in App.tsx | Debug noise in production | 10 min |
| B8 | Bare except in broadcast() | Silent failures, memory leaks | 10 min |

---

## Creative Improvements (20 Ideas)

### CRITICAL Priority (Core Value)

| # | Feature | Description | Effort | Value |
|---|---------|-------------|--------|-------|
| 1 | **Auto-Heuristic Extraction** | AI analyzes failure patterns and suggests new heuristics automatically | 1 week | Automates learning loop |
| 2 | **CEO Inbox Integration** | Prominent badge + panel showing pending decisions with inline actions | 2 days | You requested this |
| 3 | **Agent Replay** | Step-by-step playback of agent execution with timeline scrubbing | 1 week | Unique differentiator |

### HIGH Priority (Major UX)

| # | Feature | Description | Effort | Value |
|---|---------|-------------|--------|-------|
| 4 | **Knowledge Graph** | Interactive force-directed graph showing heuristic relationships | 3 days | Makes data explorable |
| 5 | **Learning Velocity Dashboard** | Track learning speed over time with trends and predictions | 2 days | Shows ROI |
| 6 | **Smart Query** | Context-aware NL query with follow-up suggestions | 2 days | Power user feature |
| 7 | **Command Palette** | Cmd+K universal command interface with fuzzy search | 1 day | Keyboard-first UX |
| 8 | **Failure Prediction** | ML predicts which files/functions will fail next | 1 week | Proactive value |
| 9 | **VS Code Extension** | Deep integration: sidebar, code lens, gutter decorations | 2 weeks | Developer workflow |
| 10 | **Diff Viewer** | Side-by-side view of agent changes with approve/revert | 2 days | Transparency |

### MEDIUM Priority (Nice to Have)

| # | Feature | Description | Effort | Value |
|---|---------|-------------|--------|-------|
| 11 | **Agent Activity Heatmap** | Real-time visualization of which files agents are touching | 2 days | Situational awareness |
| 12 | **Confidence Streams** | Streamgraph showing confidence evolution over time | 1 day | Beautiful viz |
| 13 | **Failure Pattern Radar** | Radar chart of failure types across dimensions | 1 day | Alternative viz |
| 14 | **Golden Rule Predictor** | AI suggests which heuristics are ready for promotion | 2 days | Decision support |
| 15 | **Learning Narrative** | AI-generated weekly summary in natural language | 1 day | Executive reporting |
| 16 | **Multi-Theme System** | Dark/Light/Synthwave/Custom themes | 1 day | Personalization |
| 17 | **Mobile Responsive** | Touch-optimized mobile experience | 3 days | Accessibility |
| 18 | **Notifications** | Desktop/in-app alerts for important events | 1 day | Stay informed |
| 19 | **Experiment Tracking** | Visual dashboard for active experiments | 2 days | Research tool |
| 20 | **Export Studio** | Advanced export with scheduled reports | 2 days | Reporting |

### LOW Priority (Future)

| # | Feature | Description | Effort | Value |
|---|---------|-------------|--------|-------|
| 21 | **Workspaces** | Save dashboard layouts and filters | 1 day | Power users |
| 22 | **Annotations** | Sticky notes on heuristics for collaboration | 2 days | Team feature |
| 23 | **Collaborative Mode** | Multi-user real-time dashboard | 1 week | Team feature |
| 24 | **NL to SQL** | Show generated SQL from natural language | 1 day | Transparency |
| 25 | **Webhooks** | Programmable integrations for external systems | 3 days | Extensibility |

---

## Agent Recommendations

### Researcher Perspective
> These improvements align with established dashboard patterns. Knowledge graphs and command palettes are proven UX patterns in tools like Notion, Obsidian, and VS Code. The AI-powered features (auto-heuristic, prediction) are novel but grounded in pattern recognition research.

### Architect Perspective
> The improvements can be implemented incrementally without major refactoring. Priority order should be: (1) Fix bugs, (2) Add command palette (foundation for other features), (3) CEO inbox integration, (4) Knowledge graph. The VS Code extension requires separate project setup.

### Creative Perspective
> The "Agent Replay" feature is the most unique - no other tool offers time-travel debugging for AI agents. Combined with the knowledge graph, this could make the dashboard a compelling standalone product. Consider the narrative: "Watch your AI learn in real-time."

### Skeptic Perspective
> Some features have high effort-to-value ratios. Mobile responsive (3 days) serves a small use case. Collaborative mode (1 week) assumes team usage that may not exist yet. Start with single-user power features before building for teams.

---

## Recommended Implementation Order

### Phase 1: Bug Fixes (This Week)
- [ ] B1: Create building_queries table
- [ ] B2: Add conductor integration to hooks
- [ ] B5: Fix hardcoded WebSocket URL
- [ ] B6: Add heuristics/learnings to WebSocket monitor
- [ ] B7: Remove console.log statements
- [ ] B8: Fix bare except clause

### Phase 2: Quick Wins (Next Week)
- [ ] #7: Command Palette (Cmd+K)
- [ ] #2: CEO Inbox Integration
- [ ] #18: Notifications

### Phase 3: Core Features (Week 3-4)
- [ ] #4: Knowledge Graph
- [ ] #5: Learning Velocity Dashboard
- [ ] #10: Diff Viewer

### Phase 4: AI Features (Month 2)
- [ ] #1: Auto-Heuristic Extraction
- [ ] #3: Agent Replay
- [ ] #8: Failure Prediction

### Phase 5: Polish (Month 3+)
- [ ] Remaining features based on usage feedback

---

## CEO Decision Needed

1. **Approve Phase 1-2 implementation?** (Bug fixes + quick wins)
2. **Prioritize Agent Replay vs Knowledge Graph?** (Both are high value)
3. **Should VS Code extension be a separate project?**
4. **Any features to remove from roadmap entirely?**

---

## Options

### Option A: Full Roadmap
Implement all phases as described. ~3 months to complete everything.

**Pros:** Comprehensive dashboard, unique features
**Cons:** Long timeline, may build unused features

### Option B: MVP + Iterate
Implement Phase 1-2 only, then gather feedback before continuing.

**Pros:** Fast value, data-driven decisions
**Cons:** May miss out on "wow" features

### Option C: Focus on Unique
Skip generic features (themes, mobile), focus on Agent Replay + Knowledge Graph + AI features.

**Pros:** Differentiated product, unique value
**Cons:** Missing table stakes features

---

## My Recommendation

**Option B: MVP + Iterate**

Start with bug fixes and quick wins (Phase 1-2). The command palette and CEO inbox integration provide immediate value with low risk. After 2 weeks of usage, you'll have data to inform Phase 3+ priorities.

However, I recommend fast-tracking **#3 Agent Replay** to Phase 2 if possible - it's the most unique feature and showcases the framework's capabilities.

---

**Awaiting CEO decision.**
