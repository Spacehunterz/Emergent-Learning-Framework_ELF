"""
Tiered Watcher Pattern Implementation

This package implements a two-tier watching system:
- Tier 1 (Haiku): Fast, frequent checks for basic issues
- Tier 2 (Opus): Deep analysis when intervention is needed

The launcher orchestrates both tiers and manages escalation.
"""

__version__ = "0.1.0"
