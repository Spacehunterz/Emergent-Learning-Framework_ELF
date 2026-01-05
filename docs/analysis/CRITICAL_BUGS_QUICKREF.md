# Critical Bugs - Quick Reference

**Priority:** Fix these FIRST before deploying to production.

---

## 🔴 CRITICAL #1: WebSocket Reconnect Race Condition

**File:** `apps/dashboard/frontend/src/hooks/useWebSocket.ts:75`

**Problem:** Multiple concurrent reconnection timeouts can be scheduled.

**Fix:**
```typescript
if (reconnectAttempts.current < maxReconnectAttempts && mountedRef.current) {
  // Add this check:
  if (reconnectTimeout.current) {
    clearTimeout(reconnectTimeout.current)
  }

  const delay = Math.min(baseReconnectDelay * Math.pow(2, reconnectAttempts.current), 10000)
  reconnectAttempts.current++
  reconnectTimeout.current = setTimeout(connect, delay)
}
```

---

## 🔴 CRITICAL #2: Database Corruption in Auto-Capture

**File:** `apps/dashboard/backend/utils/auto_capture.py:176-182`

**Problem:** Partial updates if second query fails.

**Fix:**
```python
try:
    new_output = json.dumps({"outcome": new_outcome, "reason": new_reason})
    cursor.execute("UPDATE workflow_runs SET output_json = ? WHERE id = ?", (new_output, run_id))
    cursor.execute("UPDATE node_executions SET result_json = ? WHERE run_id = ?", (new_output, run_id))
    conn.commit()  # Add explicit commit here
    updated += 1
except Exception as e:
    conn.rollback()  # Add rollback
    logger.error(f"Failed to update run {run_id}: {e}")
    # Don't increment 'updated' counter
```

---

## 🔴 CRITICAL #3: Division by Zero in Fraud Detector

**File:** `src/query/fraud_detector.py:136-144`

**Problem:** Guard check is unreachable.

**Fix:**
```python
total_apps = row['times_validated'] + row['times_violated'] + row['times_contradicted']

# Fix: Check zero FIRST, then min threshold
if total_apps == 0:
    return None

if total_apps < self.config.min_applications:
    return None

success_rate = row['times_validated'] / total_apps
```

---

## 🔴 CRITICAL #4: Blocking I/O in Async Event Loop

**File:** `apps/dashboard/backend/main.py:280`

**Problem:** `get_db()` is synchronous, blocks WebSocket handling.

**Fix:**
```python
async def monitor_changes():
    # ... existing code ...
    while True:
        try:
            # Wrap blocking DB operations in thread
            await asyncio.to_thread(_monitor_db_changes)
        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)
        await asyncio.sleep(2)

def _monitor_db_changes():
    """Synchronous DB operations in dedicated thread."""
    with get_db() as conn:
        # ... all the cursor.execute calls ...
```

---

## 🔴 CRITICAL #5: Memory Leak in Session Truncation

**File:** `apps/dashboard/backend/session_index.py:93-128`

**Problem:** Nested structures bypass truncation limits.

**Fix:**
```python
def _truncate_tool_input(self, tool_name: str, raw_input: Any, depth: int = 0) -> Any:
    # Add depth limit
    if depth > 3:
        return "[nested object truncated]"

    if not isinstance(raw_input, dict):
        if isinstance(raw_input, str) and len(raw_input) > self.MAX_INPUT_CHARS:
            return raw_input[:self.MAX_INPUT_CHARS] + "... [truncated]"
        return raw_input

    truncated = {}
    for key, value in raw_input.items():
        if key in ("file_path", "path", "filepath", "notebook_path"):
            truncated[key] = value
        elif key in ("content", "new_source", "old_string", "new_string"):
            if isinstance(value, str):
                if len(value) > 100:
                    truncated[key] = value[:100] + f"... [{len(value)} chars truncated]"
                else:
                    truncated[key] = value
            else:
                truncated[key] = value
        elif isinstance(value, dict):
            # Recursively truncate nested dicts
            truncated[key] = self._truncate_tool_input(tool_name, value, depth + 1)
        elif isinstance(value, list):
            # Truncate lists
            truncated[key] = [self._truncate_tool_input(tool_name, item, depth + 1) for item in value[:10]]
            if len(value) > 10:
                truncated[key].append(f"[{len(value) - 10} more items truncated]")
        elif isinstance(value, str) and len(value) > self.MAX_INPUT_CHARS:
            truncated[key] = value[:self.MAX_INPUT_CHARS] + "... [truncated]"
        else:
            truncated[key] = value

    if tool_name in self.LARGE_INPUT_TOOLS:
        truncated["_truncated"] = True

    return truncated
```

---

## 🔴 CRITICAL #6: Broadcast List Modification Race

**File:** `apps/dashboard/backend/utils/broadcast.py:29-40`

**Problem:** Concurrent disconnect can cause `ValueError`.

**Fix:**
```python
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Create snapshot under lock
        async with self._lock:
            connections = list(self.active_connections)

        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to client: {e}")
                dead_connections.append(connection)

        # Remove dead connections
        if dead_connections:
            async with self._lock:
                for conn in dead_connections:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
```

---

## 🔴 CRITICAL #7: Context Manager Connection Leak

**File:** `apps/dashboard/backend/utils/database.py:155-166`

**Problem:** Exception before `yield` leaves connection open.

**Fix:**
```python
@contextmanager
def get_db(scope: str = "global"):
    # ... path resolution ...

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    try:
        # Move init inside try block
        init_game_tables(conn)
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## 🔴 CRITICAL #8: Missing Error Feedback in UI

**File:** `apps/dashboard/frontend/src/App.tsx:165-186`

**Problem:** API failures silent to user, stale closure on deps.

**Fix:**
```typescript
useEffect(() => {
  const performCheckIn = async () => {
    try {
      console.log('[Check-in] Initiating startup handshake...')
      const response = await api.post('/api/sessions/check-in')

      if (response?.status === 'initiated') {
        notifications.info(
          'Session Check-in',
          'Summarizing your last session in the background...'
        )
      } else if (response?.status === 'ready') {
        console.log('[Check-in] Last session summary ready:', response.session_id)
      }
    } catch (err) {
      console.error('[Check-in] Handshake failed:', err)
      // FIX: Add user notification
      notifications.error(
        'Check-in Failed',
        'Could not connect to session history. Some features may be unavailable.'
      )
    }
  }

  performCheckIn()
}, [api, notifications])  // FIX: Add missing deps
```

---

## Testing Commands

After applying fixes, run these tests:

```bash
# Backend: Test WebSocket under load
python -m pytest apps/dashboard/backend/tests/test_websocket_stress.py

# Backend: Test auto-capture rollback
python -m pytest apps/dashboard/backend/tests/test_auto_capture_rollback.py

# Frontend: Test reconnection logic
npm test -- useWebSocket.test.ts

# Integration: Test concurrent broadcast
npm run test:integration -- broadcast-race.test.ts
```

---

## Deployment Checklist

- [ ] Apply all 8 critical fixes
- [ ] Run full test suite
- [ ] Test WebSocket reconnection manually (disconnect WiFi during session)
- [ ] Test database rollback (kill process during workflow run)
- [ ] Verify fraud detector with edge case data (zero applications)
- [ ] Load test with 100+ concurrent WebSocket clients
- [ ] Monitor memory usage during 1000+ session scan
- [ ] Verify error notifications appear in UI

---

**Last Updated:** 2026-01-04
**Next Review:** After critical fixes deployed
