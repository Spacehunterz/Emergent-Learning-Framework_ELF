# Voice & Audio Heuristics

**Domain:** voice, audio, tts, hooks
**Last Updated:** 2024-12-01
**Confidence:** 0.8

---

## 1. UDP is Fire-and-Forget
> `sendto()` always succeeds even when nothing listens. Never assume UDP delivery.

**Context:** Voice cache sent UDP to amplitude overlay, slept, returned "success" - but nothing played.
**Pattern:** Always have fallback when using UDP for critical functions.
**Validation:** Voice system audit 2024-12-01

---

## 2. Check File Magic Bytes, Not Extensions
> A .wav file might actually be FLAC. Verify format with magic bytes.

**Magic bytes:**
- `RIFF` = WAV
- `fLaC` = FLAC
- `ID3` or `\xff\xfb` = MP3
- `OggS` = OGG

**Check:** `head -c 4 file.wav | xxd`
**Validation:** ComfyUI returned FLAC saved as .wav - wouldn't play

---

## 3. Generators That Complete Instantly
> A generator completing with 0 output usually means missing config, not success.

**Pattern:** Check for required JSON/config files (phrases.json, schema.json, etc.)
**Validation:** Voice cache generator needed phrases.json to know what to generate

---

## 4. PortAudio Sample Format Compatibility
> PortAudio (sounddevice) may not support all sample formats/rates.

**Safe formats:**
- dtype: float32 (not float64)
- Sample rate: 44100 Hz most compatible (24000 Hz may fail on some devices)
- Channels: 1 or 2

**Fix:** Use `sf.read(path, dtype='float32')` when loading for playback

---

## 5. Windows Audio from CLI Environments
> Git Bash/MSYS can't access Windows audio devices reliably.

**Symptoms:** "WASAPI can't find requested audio endpoint", "Sample format not supported"
**Workaround:** Run from PowerShell, native Windows Python, or GUI applications
**Note:** Claude Code hooks use PowerShell so this doesn't affect production

---

## 6. Atomic State File Writes
> Use temp file + rename pattern for state files shared between processes.

**Bad:**
```python
with open(state_file, 'w') as f:
    json.dump(state, f)  # Crash mid-write = corrupted
```

**Good:**
```python
fd, tmp = tempfile.mkstemp(dir=state_file.parent)
with os.fdopen(fd, 'w') as f:
    json.dump(state, f)
Path(tmp).replace(state_file)  # Atomic on same filesystem
```

---

## 7. Voice Cache Regeneration Command
> Quick reference for regenerating voice cache with new voice.

```bash
# Clear old cache (keep phrases.json)
rm -rf ~/.claude/hooks/voice_notifications/voice_cache/*/*.wav

# Regenerate with new voice
cd ~/.claude/hooks/voice_notifications
python generate_voice_cache.py --voice "voices_examples/joshvoice.wav"
```

**Voices available:** `ls ComfyUI/custom_nodes/tts_audio_suite/voices_examples/`

---

## 8. Hook Silent Exit Points
> Voice hooks have many early exits. Check these when debugging silence.

| Condition | Location |
|-----------|----------|
| Hook not in active_voice_hooks | should_announce() |
| Rate limiting (3s per tool) | PreToolUse |
| Duplicate message (5s window) | deduplication.py |
| Speech lock timeout | speak() |
| initial_summary_announced=True | Stop hook |

---

## Related Files

- `~/.claude/hooks/voice_notifications/voice_handler.py` - Main hook handler
- `~/.claude/hooks/voice_notifications/voice_cache_manager.py` - Cache playback
- `~/.claude/hooks/voice_notifications/generate_voice_cache.py` - Cache generator
- `~/.claude/hooks/voice_notifications/voice_cache/phrases.json` - Phrase definitions
- `~/.claude/settings.json` - Hook configuration

---

## Cache-First Voice Architecture
**Domain:** voice, caching, TTS
**Confidence:** 0.8
**Recorded:** 2025-12-01

### Pattern
When building a voice notification system with pre-cached phrases, the system must use CATEGORY-BASED RANDOM SELECTION, not exact phrase matching.

### Anti-Pattern (What Went Wrong)
```
Hook fires → Extract Claude's actual response text → Try to exact-match against cached phrases → Fail → Generate new TTS audio
```
This caused:
1. Same phrase generated 5+ times via TTS engine's internal cache
2. No variety in responses (same text = same audio)
3. Wasted GPU cycles on repeated generation

### Correct Pattern
```
Hook fires → Determine category (completions, reading, editing, etc.) → Play RANDOM phrase from that category's cache → Done
```

### Implementation
- Add `cache_category` parameter to speak() method
- Use special markers like `__PLAY_RANDOM_COMPLETIONS__` 
- Map tools to categories: Read→reading, Edit→editing, Grep→searching, Bash→executing
- Never send dynamic Claude text to TTS - use cached phrases only

### Key Insight
The "CACHE HIT" in logs was the TTS engine's INTERNAL cache, not the pre-generated phrase cache. Two different caching layers - easy to confuse.
