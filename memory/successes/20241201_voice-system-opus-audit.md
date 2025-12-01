# Voice System Deep Audit with 4 Opus Subagents

**Date:** 2024-12-01
**Domain:** voice, hooks, audio, architecture
**Confidence:** 0.95

## What Happened

Coordinated 4 Opus subagents to perform deep analysis of the voice notification system. Discovered and fixed multiple critical issues preventing voice playback.

## Critical Issues Found

### Issue 1: play_cached() Never Played Audio (CRITICAL)
**Location:** `voice_cache_manager.py:play_cached()`
**Root Cause:** Method sent UDP to amplitude overlay (port 5112), then just slept for audio duration without actually playing. UDP is fire-and-forget so "success" returned even when nothing listened.
**Fix:** Added direct `sd.play()` fallback when overlay isn't running.

### Issue 2: FLAC Files Saved as .wav (CRITICAL)
**Root Cause:** ComfyUI returns FLAC format audio, but generator saved raw bytes with .wav extension. Files weren't playable as WAV.
**Fix:** Generator now converts FLAC → WAV (PCM_16) using soundfile before saving.

### Issue 3: phrases.json Missing
**Impact:** Generator completed instantly with 0 output
**Fix:** Created phrases.json with 63 Data-style phrases across 10 categories

### Issue 4: StateManager Non-Atomic Writes
**Root Cause:** `json.dump()` directly to file - crash mid-write corrupts state
**Fix:** Now uses temp file + atomic rename pattern

### Issue 5: UserPromptSubmit Hook Escaping
**Root Cause:** Triple-escaped quotes `\\\"` vs single `\"` in settings.json
**Fix:** Normalized escaping to match other hooks

## Heuristics Extracted

1. **UDP is fire-and-forget** - `sendto()` always succeeds even when nothing listens. Always have fallback for UDP-based communication.

2. **Check file magic bytes not extensions** - A .wav file might actually be FLAC. Use `head -c 4` to verify: RIFF=WAV, fLaC=FLAC

3. **Generators that complete instantly with 0 output** - Usually means missing config file, not success

4. **Atomic file writes for state** - Use temp file + rename pattern, not direct json.dump()

5. **Coordinated subagents find more issues** - 4 agents examining different aspects (hooks, TTS, state, integration) found issues none would have found alone

## Architecture Issues Noted (Future Fix)

- Dual state management: StateManager and TranscriptReader both manage same state file
- Race conditions possible between hooks
- Notification hook disabled entirely (may miss permission requests)
- System TTS fallback disabled (complete silence on TTS failure)

## Files Modified

1. `voice_cache_manager.py` - Direct audio playback fallback
2. `state_manager.py` - Atomic writes
3. `generate_voice_cache.py` - FLAC to WAV conversion
4. `voice_cache/phrases.json` - Created with 63 phrases
5. `~/.claude/settings.json` - Fixed escaping

## Command to Regenerate

```bash
rm -rf ~/.claude/hooks/voice_notifications/voice_cache/*/*.wav
cd ~/.claude/hooks/voice_notifications
python generate_voice_cache.py --voice "voices_examples/joshvoice.wav"
```

## Agent Coordination Pattern Used

```
Main Agent (Coordinator)
    |
    +-- Agent 1: Hook Execution Flow Analysis
    +-- Agent 2: TTS/Cache System Analysis
    +-- Agent 3: Message/State Management Analysis
    +-- Agent 4: Integration Testing
```

All agents ran in parallel with Opus model for deep reasoning.
