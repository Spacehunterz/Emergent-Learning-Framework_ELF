# Heuristic: Bypass Broken Accessibility Pipelines with Direct TTS

**Created:** 2025-12-05
**Domain:** accessibility, windows, screen-readers
**Confidence:** 0.7
**Validations:** 1

## Heuristic

> When a framework (like Ink.js) breaks the normal accessibility event pipeline, bypass it entirely by using direct text-to-speech (SAPI on Windows).

## Context

Ink.js uses "raw mode" for terminal input, which bypasses the standard terminal character echo that screen readers like NVDA rely on. Even with `INK_SCREEN_READER=true`, backspace announcements don't work because Ink does full-line redraws instead of character-level events.

## Solution

Instead of trying to fix the broken event chain:
1. Detect character deletions at the terminal emulator level
2. Directly speak the deleted character via Windows SAPI
3. Use PowerShell as a quick SAPI wrapper:

```rust
Command::new("powershell")
    .args(["-WindowStyle", "Hidden", "-Command", 
           "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('deleted char')"])
    .spawn();
```

## Trade-offs

- Adds PowerShell process spawn overhead (acceptable for occasional events)
- May conflict with screen reader's own speech (test with NVDA)
- Platform-specific (Windows only)

## Tags

#accessibility #nvda #sapi #windows #ink
