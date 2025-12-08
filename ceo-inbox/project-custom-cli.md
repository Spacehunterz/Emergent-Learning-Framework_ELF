# Project: Custom AI CLI

**Priority:** HIGH
**Created:** 2025-12-02
**Status:** PLANNING

## Vision

Build a CLI that's better than all existing options. No compromises.

## Why This Exists

- Claude Code has terminal limitations (Windows/MSYS2 issues documented in Rule #9)
- No existing CLI meets the user's requirements
- Forced to build from scratch

## Technical Approach

**Must use:**
- Claude API / SDK directly (not Claude Code)
- Works in ANY terminal (PowerShell, Git Bash, CMD, etc.)

**Key advantages to build:**
- True Windows-native support
- No terminal compatibility hacks
- Full control over UX

## Resources

- Claude API: https://docs.anthropic.com/claude/reference
- Claude SDK (Python): `anthropic` package
- Claude SDK (TypeScript): `@anthropic-ai/sdk`
- Windows tool guide: `~/.claude/emergent-learning/references/windows-tool-guide.md`

## Questions to Answer

1. Python or TypeScript/Node?
2. What features matter most?
3. What do existing CLIs get wrong?
4. Agent capabilities needed?
5. Tool/MCP support?

## Next Steps

- [ ] Define must-have features
- [ ] Choose language/stack
- [ ] Prototype basic chat loop
- [ ] Add tool calling
- [ ] Build from there

---

*Ready to start when CEO returns.*

---

## Feasibility Research (2025-12-02)

**Verdict:** TECHNICALLY FEASIBLE

**Not blocked by:**
- Hardware differences
- Fundamental OS limitations
- Language constraints

**Blocked by (in other tools):**
- Poor implementation choices
- Unix-first assumptions
- Lack of abstraction layers

**Architecture approach:**
- Platform Abstraction Layer pattern
- Per-OS modules
- Detect and adapt, don't assume

**Recommended stack:** Python → Rust migration path
