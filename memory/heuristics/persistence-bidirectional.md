# Persistence Requires Bidirectional Sync

**Heuristic:** Settings persistence needs both load_from_config on startup AND save_to_config on every change.

**Why:** Missing either direction causes settings to appear lost or not apply.

**Source:** claudex settings persistence implementation
**Confidence:** 0.75
**Created:** 2025-12-02
