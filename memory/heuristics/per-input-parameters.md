# Per-Input Parameters for Multi-Source Systems

**Domain:** image-processing, multi-source-systems
**Confidence:** 0.9
**Created:** 2025-12-05

## Heuristic
When a system processes multiple input sources (images, videos, data streams), parameters derived from one source (crop bounds, region coordinates, thresholds) should NOT be globally applied to other sources.

## General Principle
Each input source may have different:
- Dimensions and aspect ratios
- Content positioning (face higher/lower, centered/offset)
- Characteristics requiring different thresholds

## Application
1. Store parameters per-source in config/dict
2. Or calculate dynamically per-input
3. Check `current_source` before applying transforms
4. Test EACH source independently

## Code Pattern
```python
params = SOURCE_PARAMS.get(current_source, DEFAULT_PARAMS)
region = params['region']
```

## Symptoms of Violation
- Works for one source, breaks for others
- Features appear in wrong positions after switching
- "Something else is moving/changing" reports
