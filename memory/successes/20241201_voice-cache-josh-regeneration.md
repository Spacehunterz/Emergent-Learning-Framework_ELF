# Voice Cache Regeneration with Josh Voice

**Date:** 2024-12-01
**Domain:** voice, comfyui, tts
**Confidence:** 0.9

## What Happened

Successfully regenerated all 63 voice cache files using Josh's voice via ComfyUI Chatterbox TTS.

## Key Insight

The voice cache system requires `phrases.json` in `voice_cache/` directory to define what phrases to generate. Without this file, the generator completes instantly with 0 files.

## Technical Details

1. **Pipeline Structure:**
   - `phrases.json` defines phrases by category (completions, reading, editing, etc.)
   - `generate_voice_cache.py` reads phrases and sends workflows to ComfyUI
   - ComfyUI Chatterbox generates audio, script downloads via API
   - Files saved as `.wav` to `voice_cache/{category}/` with naming: `{first_4_words}_{hash}.wav`

2. **Voice Reference:**
   - Pass voice file via `--voice` parameter: `voices_examples/joshvoice.wav`
   - Located in ComfyUI's `custom_nodes/tts_audio_suite/voices_examples/`

3. **Categories (63 total):**
   - completions: 12 phrases
   - reading: 6 phrases
   - editing: 7 phrases
   - searching: 7 phrases
   - executing: 6 phrases
   - web_search: 5 phrases
   - errors: 6 phrases
   - greetings: 3 phrases
   - waiting: 6 phrases
   - approval_needed: 5 phrases

## Heuristic Extracted

> Always check for configuration files (like phrases.json) when a generator script completes instantly with no output. Missing config = no work done.

## Command to Regenerate

```bash
cd ~/.claude/hooks/voice_notifications
rm -rf voice_cache/*  # Keep phrases.json
python generate_voice_cache.py --voice "voices_examples/joshvoice.wav"
```

## Related Files

- `~/.claude/hooks/voice_notifications/generate_voice_cache.py`
- `~/.claude/hooks/voice_notifications/voice_cache_manager.py`
- `~/.claude/hooks/voice_notifications/voice_cache/phrases.json`
