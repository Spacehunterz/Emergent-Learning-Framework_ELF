# Robot Face Avatar: GrabCut Background Removal

**Date:** 2025-12-01
**Domain:** computer-vision, face-overlay
**Confidence:** 0.80

## What Was Built

New robot/android avatar for Data overlay system from Grok-generated video.

### Challenges Solved

1. **Non-Green-Screen Background Removal**
   - Source video had gray gradient background (not chroma key)
   - `rembg` failed to install (Python 3.14 + scikit-image build issues)
   - Solution: OpenCV GrabCut algorithm with bounding box hint
   
2. **Video Processing Pipeline**
   - GrabCut on first frame to generate mask
   - Applied same mask to all 145 frames (static camera = consistent mask)
   - Composited onto green background for existing chroma key pipeline
   
3. **Mouth Frame Generation**
   - Robot face has no mouth movement in source video
   - SDXL inpainting too slow (timeout)
   - Solution: OpenCV geometric shapes (ellipses/circles) with dark robot interior
   - 6 variants: closed, slight, medium, wide, eee, ooo

### Key Heuristic
**GrabCut for uniform backgrounds**: When background is solid/gradient (not green screen), use `cv2.grabCut()` with `GC_INIT_WITH_RECT`. Process first frame, reuse mask for video (if camera static).

```python
rect = (margin_x, margin_top, w - 2*margin_x, h - margin_top - margin_bottom)
cv2.grabCut(img, mask, rect, bgModel, fgModel, 5, cv2.GC_INIT_WITH_RECT)
fg_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype('uint8')
```

### Debug Tip
Overlay config stores window position. If `x` value exceeds screen width, window is off-screen. Reset to `{"x": 100, "y": 100, ...}`.

## Files Created
- `GrokFace.mp4` - 145 frames, 928x1376, green background
- `mouth_frames/mouth_*.png` - 6 mouth position variants

## Tags
grabcut, background-removal, opencv, face-overlay, video-processing
