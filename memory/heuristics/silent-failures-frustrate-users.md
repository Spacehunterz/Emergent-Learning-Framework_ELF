# Silent Failures Frustrate Users

**Domain:** UI/UX, Game Development
**Confidence:** 0.7
**Created:** 2025-12-03
**Source:** spaceshooter shield upgrade bug

## Pattern
When an action fails validation (e.g., insufficient resources, invalid state), always provide visible feedback.

## Why
Users interpret "no visible change" as "broken code" even when the code works correctly. The shield upgrade button worked fine - it just silently did nothing when resources were insufficient.

## Apply When
- Form submissions with validation
- Purchase/upgrade systems with costs
- Any user action that can fail silently

## Solution
Add error messages, animations, color changes, or sounds for failed actions. Even a brief flash or shake indicates "I heard you, but no."
