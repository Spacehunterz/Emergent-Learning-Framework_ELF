# Emergent Learning Framework - Scale Limits

## Overview

This document describes the scalability characteristics and operational limits of the Emergent Learning Framework (ELF).

## Scale Limits by Subsystem

### 1. Query System

#### Connection Pool
- **Maximum pooled connections**: 5 (configurable via MAX_CONNECTION_POOL_SIZE)
- **Recommendation**: Increase to 10-20 for high-concurrency workloads
- **SQLite limit**: ~1000 concurrent connections (OS-dependent)

#### Database Size
- **Tested up to**: 10,000 learning records
- **Expected performance**: Up to 100,000 records
- **Degradation point**: 500,000+ records (consider archival)
- **Storage overhead**: ~1-5 KB per record

#### Concurrent Queries
- **Supported**: Up to 5 simultaneous queries (connection pool size)
- **Recommendation**: Batch writes, parallelize reads

### 2. Coordinator - Event Log

#### Event Log Size
- **Tested up to**: 1,000 events
- **Expected performance**: Up to 10,000 events
- **Degradation point**: 50,000+ events (O(n) scan performance)
- **Storage overhead**: ~200-500 bytes per event (JSON + checksum)

**Performance Characteristics**:
| Events | Append Time | Read All | Delta Query (10%) |
|--------|-------------|----------|-------------------|
| 100 | < 1ms | < 10ms | < 5ms |
| 1,000 | < 2ms | < 50ms | < 20ms |
| 10,000 | < 5ms | < 500ms | < 200ms |
| 50,000 | < 10ms | ~2s | ~1s |

**Recommendations**:
- **< 10k events**: Current implementation sufficient
- **10k-50k events**: Monitor query latency, consider compaction
- **> 50k events**: Migrate to SQLite-backed event storage

#### Concurrent Agents
- **File-based locking**: Up to 10 agents recommended
- **Lock contention**: Increases with agent count
- **Recommendation**: Use process-level coordination for >20 agents

### 3. Coordinator - Blackboard

#### JSON File Size
- **Tested up to**: 100 state entries
- **Expected performance**: Up to 1,000 entries
- **Degradation point**: 5,000+ entries (full rewrite on every update)

**Performance Characteristics**:
| State Size | Read Time | Write Time | File Size |
|------------|-----------|------------|-----------|
| 10 entries | < 1ms | < 5ms | ~1 KB |
| 100 entries | < 10ms | < 20ms | ~10 KB |
| 1,000 entries | < 50ms | < 100ms | ~100 KB |
| 5,000 entries | < 200ms | < 500ms | ~500 KB |

**Recommendations**:
- **< 1k entries**: Current implementation sufficient
- **> 1k entries**: Migrate to event log (Phase 2)

#### Concurrent Agents
- **Recommended max**: 20 agents per blackboard
- **Hard limit**: 100 agents (lock contention becomes severe)

### 4. Conductor - Workflow Orchestration

#### Workflows
- **Tested up to**: 50 workflows
- **Expected performance**: Up to 500 workflows
- **Recommendation**: Archive completed workflows after 90 days

#### Active Workflow Runs
- **Concurrent runs**: Up to 10 recommended
- **Maximum runs**: 100 (limited by executor resources)

#### Nodes per Workflow
- **Tested up to**: 20 nodes
- **Expected performance**: Up to 100 nodes
- **Recommendation**: Break complex workflows into sub-workflows

### 5. Storage - SQLite Databases

#### Database File Size
- **Maximum theoretical**: 281 TB (SQLite limit)
- **Practical limit**: 10 GB per database (performance)
- **Recommendation**: Split large datasets across multiple databases

#### Pragmas Configured
All ELF databases use these pragmas:
- PRAGMA journal_mode=WAL - Write-Ahead Logging
- PRAGMA synchronous=NORMAL - Balance durability/performance
- PRAGMA foreign_keys=ON - Referential integrity
- PRAGMA busy_timeout=10000 - 10s wait for locks

## Monitoring and Alerts

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Query latency | > 5s | > 30s |
| Event log size | > 5k events | > 50k events |
| Blackboard size | > 1k entries | > 5k entries |
| Database size | > 1 GB | > 5 GB |
| WAL file size | > 50 MB | > 500 MB |
| Disk space | < 1 GB free | < 100 MB free |
| Lock failures | > 10/min | > 50/min |

## Scaling Strategies

### Vertical Scaling
1. Increase connection pool size
2. Add database indices
3. Tune SQLite pragmas
4. Archive old data

### Horizontal Scaling
1. Shard by project
2. Read replicas
3. Event log partitioning

## Known Limitations

1. **Single-writer SQLite limitation**: Only one write transaction at a time
2. **File-based coordination**: Not suitable for 100+ concurrent agents
3. **O(n) event log scans**: Performance degrades with large logs
4. **No built-in sharding**: Single machine deployment
5. **No distributed coordination**: File-based locking limited to single machine

---

**Document Version**: 1.0
**Last Updated**: 2025-12-08
