# Voice System: Conversation Detection & Phrase Cycling

**Date:** 2025-12-01
**Domain:** voice-audio, claude-code-hooks
**Confidence:** 0.85

## What Was Built

Enhanced Claude Code voice notification system with:

1. **Conversation vs Coding Detection**
   - Added `tools_used_this_cycle` counter in state_manager.py
   - Reset on UserPromptSubmit, increment on PreToolUse
   - Stop hook checks: 0 tools = conversation, >0 = coding task
   - Different phrase categories for each mode

2. **Weighted Phrase Cycling (No Repeats)**
   - Changed from `deque(maxlen=5)` to `set()` tracking ALL used phrases
   - Only repeats when entire category exhausted, then resets
   - Prevents "same phrase 3x in a row" problem

3. **New Config Flags**
   - `subagent_voice_enabled: false` - silences Task tool subagents
   - `approval_announcements_enabled: false` - stops permission spam

4. **New Phrase Category**
   - `conversation_complete` - 8 phrases for pure Q&A responses
   - Generated audio cache via ComfyUI Chatterbox

## Key Files Modified
- `~/.claude/hooks/voice_notifications/state_manager.py`
- `~/.claude/hooks/voice_notifications/voice_cache_manager.py`
- `~/.claude/hooks/voice_notifications/voice_handler.py`
- `~/.claude/hooks/voice_notifications/config.json`
- `~/.claude/hooks/voice_notifications/voice_cache/phrases.json`

## Transferable Pattern
Track state across hook invocations using persistent JSON files with atomic writes (temp + rename). Reset counters on "cycle start" events (UserPromptSubmit), aggregate during cycle, evaluate on "cycle end" events (Stop).

## Tags
voice, hooks, state-management, phrase-cycling, conversation-detection
