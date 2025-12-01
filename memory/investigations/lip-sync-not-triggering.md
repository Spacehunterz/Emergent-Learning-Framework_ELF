# Investigation: Lip Sync Not Triggering

**Status:** ACTIVE  
**Started:** 2025-12-01

## The Problem
Mouth doesn't move when voice plays, despite all components existing.

## Quick Debug Commands
```bash
# 1. Check overlay console for "Received play_sync" when voice triggers
# 2. Send test: python -c "import socket; s=socket.socket(2,2); s.sendto(b'test',('127.0.0.1',5112))"
# 3. Check if audio plays through overlay or direct sounddevice
```
