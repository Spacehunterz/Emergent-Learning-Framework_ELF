# Data Overlay: New Face Integration

**Date:** 2025-11-30
**Project:** data_overlay
**Domain:** computer-vision, pyqt, real-time-video

## What Was Accomplished

1. **New face video integration** - Replaced data_idle_512.mp4 with NewFaceFixed.mp4 (green screen)
2. **Generated 6 animated mouth videos** via LivePortrait (176 frames × 6 positions)
3. **Alt+drag resize with UX improvements:**
   - White silhouette outline preview during drag (Canny edge detection on alpha)
   - "Loading..." indicator during frame reload
   - Reversed direction (up=bigger, down=smaller)
4. **Green chroma key system** - HSV-based with erode→dilate→blur + despill

## Key Technical Decisions

- Resize preview uses scaled outline, actual reload on mouse release (not during drag)
- Chroma key uses HSV (hue 35-85, sat/val 50+) for better green detection than RGB
- Despill reduces green channel where it exceeds avg(red, blue)

## What Worked Well

- Silhouette outline using Canny edge detection on alpha channel - clean visual
- Deferring heavy operations (frame reload) to mouse release prevents UI freeze
- LivePortrait for mouth frame generation - good quality

## What Needs More Work

- Green fringe on ear/neck edges - chroma key still not perfect
- May need to pre-process source video to remove green spill before using

## Heuristics Extracted

1. **Heavy operations on release, not during drag** - Live reload of 2000+ frames during mouse move causes crashes
2. **Visual feedback during long operations** - Loading indicator + preview outline improves UX
