---
step: 1
name: Define Research Scope
objective: Clearly define the research question and boundaries
estimated_time: 5-10 minutes
requires_user_input: true
---

# Step 1: Define Research Scope

## Objective
Establish clear boundaries for the research to prevent scope creep and ensure focused investigation.

## Instructions

### 1. Identify the Core Question
- What specific question needs answering?
- What problem is being solved?
- What decision will this research inform?

**Output format:**
```markdown
## Core Research Question
[Single, specific question to answer]

## Problem Context
[2-3 sentences on why this matters]

## Decision to Inform
[What action will be taken based on findings]
```

### 2. Define Boundaries
- What is IN scope?
- What is explicitly OUT of scope?
- What constraints exist (time, resources, access)?

**Output format:**
```markdown
## In Scope
- [Topic/area 1]
- [Topic/area 2]

## Out of Scope
- [Excluded topic 1]
- [Excluded topic 2]

## Constraints
- [Constraint 1]
- [Constraint 2]
```

### 3. Identify Success Criteria
- What does a successful research outcome look like?
- What quality bar must be met?
- How will we know we have enough?

**Output format:**
```markdown
## Success Criteria
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]
```

---

## Decision Gate

Before proceeding to Step 2, confirm:
- [ ] Core question is specific and answerable
- [ ] Boundaries are clearly defined
- [ ] Success criteria are measurable

**Options:**
- [C] Continue to Step 2 (Evidence Gathering)
- [R] Refine scope (iterate on this step)
- [P] Pause workflow (need CEO input)

---

## Checkpoint Output

When completing this step, append the following to the output file:

```markdown
# Research: [Topic]

## Step 1: Scope Definition
**Completed:** [timestamp]

### Core Question
[question]

### Boundaries
**In Scope:** [list]
**Out of Scope:** [list]

### Success Criteria
[criteria list]

---
```
