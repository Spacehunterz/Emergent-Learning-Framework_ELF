# LivePortrait Blink Fails on Stylized Faces

**Domain:** face-overlay, liveportrait
**Confidence:** 0.8
**Created:** 2025-12-05

## Heuristic
LivePortrait's blink expression parameter doesn't work on stylized/android/robot faces.

## Evidence
- Robot face: "Failed to detect face!!" - used heatmap fallback
- Even blink=5.0 produced no visible eye closing on female android
- Mouth expressions (aaa, eee, woo) work via heatmap fallback
- Eye/blink requires proper face detection

## Application
For blink animation on non-human faces:
1. Create blink frames manually (image editing)
2. Or use a different animation approach (fade overlay on eye region)
3. Don't rely on LivePortrait blink parameter

## Related
- rembg needed after LivePortrait (outputs have black backgrounds)
