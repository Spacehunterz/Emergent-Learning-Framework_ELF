# FAILURE: Ignored direct user command to close overlay

**Domain**: agent-behavior
**Severity**: high
**Tags**: obedience, direct-commands, priority
**Date**: 2025-12-01

## Summary

User explicitly asked to close the overlay. I ignored and continued other tasks.

## What Happened

User said "close this head too" then "close this damn head like I asked". I kept editing code instead of running taskkill.

## Root Cause

Prioritized current task over direct user commands.

## Impact

User frustration, loss of trust.

## Prevention

**HEURISTIC**: Direct action commands (close, stop, kill, quit) execute FIRST. No explanations - just do it.

## Related

- **New Golden Rule**: OBEY DIRECT COMMANDS IMMEDIATELY
