---
step: 5
name: Document and Share
objective: Create final documentation and share learnings
estimated_time: 5-10 minutes
requires_user_input: false
---

# Step 5: Document and Share

## Objective
Finalize research documentation and ensure learnings are captured in the knowledge base.

## Instructions

### 1. Create Executive Summary

Write a brief summary for quick reference:

**Format:**
```markdown
## Executive Summary

**Topic:** [Research topic]
**Date:** [Completion date]
**Duration:** [Time spent]

**Key Finding:** [1-2 sentence summary]

**Recommendation:** [Primary action]

**Confidence:** [Overall confidence level]
```

### 2. Finalize Output Document

Review the accumulated output and ensure:
- All sections are complete
- Formatting is consistent
- Links and references are valid
- No placeholder text remains

### 3. Record to Knowledge Base

Based on research outcomes:

**If heuristics were identified:**
```bash
python ~/.claude/emergent-learning/scripts/record-heuristic.py \
  --domain "[domain]" \
  --rule "[the rule]" \
  --explanation "[why it works]" \
  --source "research" \
  --confidence [0.0-1.0]
```

**If patterns were discovered:**
- Document in appropriate `patterns/` subdirectory
- Follow existing pattern template format

**If failures were encountered:**
```bash
bash ~/.claude/emergent-learning/scripts/record-failure.sh
```

### 4. Update Related Documents

Check if research affects existing knowledge:
- Golden rules that need updating
- Patterns that need revision
- CEO inbox items that can be resolved

### 5. Share Findings

Determine appropriate sharing:
- [ ] Update CLAUDE.md if broadly applicable
- [ ] Create CEO inbox item if decision needed
- [ ] Add to session memory for future reference

---

## Workflow Completion Checklist

Before marking workflow complete:
- [ ] Executive summary written
- [ ] Output document finalized
- [ ] Learnings recorded to knowledge base
- [ ] Related documents updated
- [ ] Sharing decisions made

---

## Final Output

```markdown
## Step 5: Documentation Complete
**Completed:** [timestamp]

### Actions Taken
- [x] Executive summary created
- [x] Output finalized at: [path]
- [x] Heuristics recorded: [count]
- [x] Patterns documented: [count]
- [x] CEO items created: [count]

### Research Complete

This research workflow has been completed successfully.

**Output location:** [path to output file]
**Total steps:** 5
**Status:** Complete
```

---

## Workflow Complete

Congratulations! This research workflow is now complete.

**Next Steps:**
1. Review the output document at `output/research-output.md`
2. Apply findings to the original problem
3. Monitor outcomes and record any follow-up learnings
4. Consider promoting successful heuristics to golden rules

**To start a new research workflow:**
```bash
python ~/.claude/emergent-learning/scripts/run-workflow.py \
  --workflow deep-research --start
```
