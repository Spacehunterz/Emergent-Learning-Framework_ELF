# Blackboard to Event Log Migration Plan

## Overview

This document describes the phased migration from the legacy JSON-based Blackboard system to the new EventLog-based coordination system. The migration uses a dual-write adapter pattern to ensure zero downtime and safe rollback.

## Migration Phases

### Phase 1: Dual-Write Validation (CURRENT)

**Status**: In progress
**Implementation**: blackboard_v2.py

**Behavior**:
- Write to BOTH blackboard.json AND event_log.jsonl
- Read from blackboard.json (source of truth)
- Validate that event log produces same state

**Code Change**:
```python
# Before (Phase 0)
from blackboard import Blackboard

# After (Phase 1)
from blackboard_v2 import BlackboardV2 as Blackboard
```

**Validation Criteria**:
1. Event log successfully captures all operations
2. State derived from event log matches blackboard.json
3. No data loss or corruption observed
4. Performance acceptable (write latency < 50ms)

### Phase 2: Cutover (PLANNED)

**Status**: Not started
**Target**: After 30+ days of successful Phase 1 operation

**Behavior**:
- Write ONLY to event_log.jsonl
- Read from event_log.jsonl (rebuild state on load)
- Keep blackboard.json as backup (read-only)

**Prerequisites**:
1. Phase 1 validation successful for 30+ days
2. No critical bugs in event log implementation
3. Performance benchmarks met
4. Backup and recovery procedures tested

**Implementation Steps**:
1. Backup: Create snapshot of all coordination data
2. Deploy: Update imports to use EventLog directly
3. Verify: Confirm state consistency
4. Monitor: Watch for issues in first 7 days
5. Archive: After 30 days success, archive old blackboard.json

**Rollback Plan**:
If issues detected within 7 days:
1. Stop all agents
2. Revert to blackboard_v2.py (Phase 1)
3. Investigate and fix issues
4. Retry cutover after fixes validated

### Phase 3: Optimization (FUTURE)

**Status**: Not started
**Target**: 90+ days after Phase 2

**Enhancements**:
1. Compaction: Periodically compact event log
2. Indexing: Add SQLite index for fast queries
3. Sharding: Split by project for large deployments

## Performance Targets

| Metric | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|
| Write Latency (p50) | < 20ms | < 10ms | < 5ms |
| Write Latency (p99) | < 50ms | < 30ms | < 20ms |
| State Rebuild | N/A | < 500ms (10k events) | < 200ms |
| Delta Query | N/A | < 100ms | < 20ms |
| Storage Overhead | 2x (dual-write) | 1x | 0.5x (compacted) |

## Risk Assessment

### Phase 1 Risks
- **Low**: Dual-write increases latency slightly
- **Low**: Storage overhead (2x)

### Phase 2 Risks
- **Medium**: State rebuild on startup adds latency
- **Medium**: Bugs in event replay logic
- **Low**: Data loss during migration

### Phase 3 Risks
- **Medium**: Compaction algorithm complexity
- **Low**: SQLite migration issues

## Success Criteria

### Phase 1 Success
- No data inconsistencies for 30 consecutive days
- < 5 critical bugs per month
- Performance acceptable (write latency < 50ms p99)
- All validation tests passing

### Phase 2 Success
- No rollbacks needed within first 7 days
- State consistency verified across all agents
- Performance meets targets
- No critical bugs for 30 days

---

**Document Version**: 1.0
**Last Updated**: 2025-12-08
