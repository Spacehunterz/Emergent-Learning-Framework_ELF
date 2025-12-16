---
step: 2
name: Gather Evidence
objective: Collect relevant information from multiple sources
estimated_time: 15-30 minutes
requires_user_input: false
---

# Step 2: Gather Evidence

## Objective
Systematically collect information from diverse sources to build a comprehensive evidence base.

## Instructions

### 1. Source Identification
Identify relevant sources for this research:

**Primary Sources:**
- Codebase (existing implementations)
- Documentation (README, wikis, comments)
- Git history (decisions, changes)

**Secondary Sources:**
- Web search (articles, docs, discussions)
- Knowledge base (ELF learnings, heuristics)
- External APIs/tools documentation

**Tertiary Sources:**
- Community discussions (GitHub issues, forums)
- Expert opinions (blog posts, talks)

### 2. Evidence Collection

For each source, document:
- **Source:** Where it came from
- **Claim:** What it says
- **Relevance:** How it relates to research question
- **Confidence:** How reliable is this source? (high/medium/low)

**Evidence Template:**
```markdown
### Evidence [N]
- **Source:** [URL or file path]
- **Claim:** [What this source asserts]
- **Relevance:** [Connection to research question]
- **Confidence:** [high/medium/low]
- **Notes:** [Additional context]
```

### 3. Source Diversity Check

Ensure evidence comes from multiple perspectives:
- [ ] Technical implementation details
- [ ] Conceptual/theoretical background
- [ ] Practical usage examples
- [ ] Known issues or limitations
- [ ] Alternative approaches

### 4. Gap Identification

Note any gaps in available evidence:
- What questions remain unanswered?
- What sources were unavailable?
- What would strengthen the evidence base?

---

## Quality Checklist

Before proceeding:
- [ ] Minimum 3 distinct sources consulted
- [ ] Evidence covers multiple perspectives
- [ ] Confidence levels assigned to all claims
- [ ] Gaps explicitly documented

---

## Decision Gate

**Options:**
- [C] Continue to Step 3 (Analysis)
- [M] More evidence needed (continue gathering)
- [P] Pause (need access to additional resources)

---

## Checkpoint Output

```markdown
## Step 2: Evidence Gathered
**Completed:** [timestamp]
**Sources consulted:** [count]

### Evidence Summary

#### Evidence 1
- Source: [source]
- Claim: [claim]
- Confidence: [level]

#### Evidence 2
[...]

### Gaps Identified
- [Gap 1]
- [Gap 2]

---
```
