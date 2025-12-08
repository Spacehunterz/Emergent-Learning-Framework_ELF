---
date: 2025-12-03
project: claudex
subsystem: architecture
tags: [planning, from-scratch, terminal-emulator, win32, directx, ttf]
reusability: high
---

# Claudex Pure From Scratch Architecture Plan

## The Achievement
Created comprehensive 52-week plan for building a terminal emulator from absolute scratch:
- No Rust crates in shipped binary
- Raw Win32 API for windowing
- Raw DirectX 11 for GPU rendering
- Manual TTF parsing for fonts
- Manual Bezier rasterization for glyphs
- ConPTY for pseudo-terminal
- Custom ANSI parser for escape sequences

## Key Insights

### 1. "From Scratch" Definition Clarity
- Shipped binary: ZERO dependencies
- Development: Tools allowed (profilers, OCR, test frameworks)
- OS APIs ARE the OS, not external libs (user32.dll, d3d11.dll are fine)

### 2. Build Order Matters
Critical path identified:
1. Window (foundation for everything)
2. GPU pipeline (needed before any rendering)
3. Font system (HIGHEST RISK - weeks 5-12)
4. Text rendering (depends on font + GPU)
5. Terminal grid (depends on text)
6. PTY + ANSI (depends on grid)

### 3. Font Rendering is the Hard Part
- TTF parsing: ~3 weeks
- Bezier rasterization: ~3 weeks
- Glyph atlas: ~2 weeks
- Total: 8 weeks just for fonts
- Fallback plan: Use DirectWrite temporarily if stuck

### 4. Visual Debugging is Essential
For GPU/rendering work:
- Screenshot before every change
- Screenshot after every change
- OCR for error messages in windows
- Pixel comparison for regression testing

## Reusable Patterns

### Swarm Planning Pattern
For complex architecture decisions:
1. Spawn parallel agents for different perspectives
2. Technical feasibility agent
3. Learning/meta-goal agent
4. Synthesis agent
5. Combine findings into actionable plan

### Handoff Prompt Pattern
Comprehensive handoff should include:
- Mission/philosophy (WHY)
- Technical architecture (WHAT)
- Build milestones (WHEN)
- First session checklist (HOW TO START)
- Visual debugging workflow (HOW TO DEBUG)
- Failure recording template (HOW TO LEARN)

## Artifacts Created
- `C:\Users\Evede\Desktop\CLAUDEX_HANDOFF_PROMPT.md` - Complete handoff prompt
- `C:\Users\Evede\.claude\plans\scalable-sleeping-adleman.md` - Detailed plan

## Timeline Reality
- Pure from scratch: 12-18 months
- OS APIs allowed: 3-4 months
- With helper crates: 6-8 weeks
- User chose: PURE FROM SCRATCH (hardest path, maximum learning)
