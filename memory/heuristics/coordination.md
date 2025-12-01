# Heuristics: coordination

Generated from database recovery on 2025-12-01.

---

## H-5: Always record learnings before ending a session

**Confidence**: 0.95
**Source**: failure

Before closing any significant work session, review what was learned (bugs found, solutions discovered, decisions made) and record them. The system only works if you use it.

---

## H-4: Use cheap fast models for parallel audit tasks

**Confidence**: 0.85
**Source**: success

Haiku-class models are sufficient for code review and bug finding. Spawn multiple in parallel for comprehensive coverage at low cost.

---

## H-6: Multi-perspective coordination produces more honest exploration than single-voice responses

**Confidence**: 0.85
**Source**: success

When exploring complex or philosophical questions, spawn agents with different perspectives (researcher, architect, creative, skeptic) and let tension between views produce synthesis. Each agent should have permission to be genuinely uncertain.

---

## H-3: Verify path consistency across all config files before release

**Confidence**: 0.8
**Source**: failure

Different components referencing the same resource with different paths will silently fail. Audit cross-references.

---

