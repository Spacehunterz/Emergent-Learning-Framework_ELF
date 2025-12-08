# Procedural Eye Darkening Blink - Failed

**Date:** 2025-12-05
**Domain:** face-overlay, animation
**Severity:** Minor (reverted quickly)

## What Happened
Attempted to implement blink animation by darkening the eye region procedurally since LivePortrait couldn't generate proper blink frames for stylized faces.

## The Approach
- Detect blink state (open/half/closed) from BlinkController
- Darken eye region to 60% (half) or 20% (closed) brightness
- Use feathered mask for smooth edges
- Face-specific eye coordinates

## Why It Failed
User feedback: "undo that blink attempt it sucks"

Likely issues:
1. Darkening doesn't look like actual eye closing
2. The effect was jarring/unnatural
3. Eye region bounds probably weren't precise enough
4. Simple darkening ≠ realistic blink

## Lesson Learned
Procedural effects that try to simulate complex facial movements (blink) by simple image manipulation (darkening) don't look good. Better options:
1. Hand-paint actual closed-eye frames
2. Use AI inpainting to generate closed eyes
3. Accept no blinking rather than bad blinking
4. Use video source with natural blinks

## Action Taken
Reverted to disabled blink. User prefers no blink over bad blink.
