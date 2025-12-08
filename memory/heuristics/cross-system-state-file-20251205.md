# Simple State Files for Cross-System Coordination

**Domain:** system-integration
**Confidence:** 0.9
**Created:** 2025-12-05

## Heuristic
Use simple text files to share state between independent systems (overlay, voice hooks, etc.) rather than complex IPC.

## Evidence
- Face overlay writes `current_face.txt` with "robot" or "female"
- Voice cache manager reads this file to select voice cache directory
- Works reliably, no socket/pipe complexity, survives restarts

## Application
When System A needs to inform System B of state:
1. System A writes state to a known file path
2. System B reads file when it needs the state
3. Use simple formats (single word, JSON for complex)
4. Handle file-not-found gracefully (use default)

## Tradeoffs
- Pro: Simple, debuggable, survives restarts
- Con: Not real-time (polling needed), race conditions possible
- Best for: Infrequent state changes, loose coupling
