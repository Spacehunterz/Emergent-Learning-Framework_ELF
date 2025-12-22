#!/usr/bin/env python3
"""
Async Real-World Benefit Benchmark

Shows where async actually helps: mixed workloads where
DB queries can overlap with other I/O operations.

SQLite itself doesn't parallelize, but async lets other
work happen while waiting for queries.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from query import QuerySystem


async def simulate_io_work(ms: int = 50):
    """Simulate other async I/O (network call, file read, etc.)."""
    await asyncio.sleep(ms / 1000)


async def sync_style_workflow(qs: QuerySystem) -> float:
    """
    Sync-style: Do everything sequentially.
    DB query -> wait -> Other I/O -> wait -> DB query -> wait
    """
    start = time.perf_counter()

    # Query 1
    await qs.query_by_domain("testing", limit=5)

    # Simulated network/file I/O
    await simulate_io_work(50)

    # Query 2
    await qs.get_statistics()

    # More I/O
    await simulate_io_work(50)

    # Query 3
    await qs.query_recent(limit=10)

    return time.perf_counter() - start


async def async_style_workflow(qs: QuerySystem) -> float:
    """
    Async-style: Overlap DB queries with other I/O.
    Start DB query -> Do other I/O while waiting -> Gather results
    """
    start = time.perf_counter()

    # Start all operations concurrently
    results = await asyncio.gather(
        qs.query_by_domain("testing", limit=5),
        simulate_io_work(50),
        qs.get_statistics(),
        simulate_io_work(50),
        qs.query_recent(limit=10),
    )

    return time.perf_counter() - start


async def benchmark_context_building(qs: QuerySystem, rounds: int = 5):
    """
    Real-world scenario: Building agent context.
    Needs: golden rules + domain heuristics + recent learnings + stats
    """

    sync_times = []
    async_times = []

    for _ in range(rounds):
        # Sync style - one at a time
        start = time.perf_counter()
        await qs.get_golden_rules()
        await qs.query_by_domain("testing", limit=10)
        await qs.query_recent(limit=5)
        await qs.get_statistics()
        sync_times.append(time.perf_counter() - start)

        await asyncio.sleep(0.05)  # Brief pause

        # Async style - all at once
        start = time.perf_counter()
        await asyncio.gather(
            qs.get_golden_rules(),
            qs.query_by_domain("testing", limit=10),
            qs.query_recent(limit=5),
            qs.get_statistics(),
        )
        async_times.append(time.perf_counter() - start)

    sync_mean = sum(sync_times) / len(sync_times) * 1000 if len(sync_times) > 0 else 0.0
    async_mean = sum(async_times) / len(async_times) * 1000 if len(async_times) > 0 else 0.0
    return {
        "sync_mean_ms": sync_mean,
        "async_mean_ms": async_mean,
    }


async def main():
    print("=" * 70)
    print("ASYNC REAL-WORLD BENEFIT BENCHMARK")
    print("=" * 70)

    qs = await QuerySystem.create(debug=False)

    try:
        # Test 1: Mixed I/O workflow
        print("\n[Test 1] Mixed Workload (DB + simulated network I/O)")
        print("-" * 50)

        sync_times = []
        async_times = []

        for i in range(5):
            sync_time = await sync_style_workflow(qs)
            sync_times.append(sync_time)
            await asyncio.sleep(0.05)
            async_time = await async_style_workflow(qs)
            async_times.append(async_time)
            print(f"  Round {i+1}: sync={sync_time*1000:.1f}ms, async={async_time*1000:.1f}ms")

        sync_mean = sum(sync_times) / len(sync_times) * 1000 if len(sync_times) > 0 else 0.0
        async_mean = sum(async_times) / len(async_times) * 1000 if len(async_times) > 0 else 0.0
        speedup = sync_mean / async_mean if async_mean > 0 else 0.0

        print(f"\n  Sequential mean: {sync_mean:.1f}ms")
        print(f"  Concurrent mean: {async_mean:.1f}ms")
        print(f"  Speedup: {speedup:.1f}x faster")

        # Test 2: Context building (pure DB)
        print("\n[Test 2] Context Building (4 DB queries)")
        print("-" * 50)

        results = await benchmark_context_building(qs, rounds=5)

        print(f"  Sequential: {results['sync_mean_ms']:.1f}ms")
        print(f"  Concurrent: {results['async_mean_ms']:.1f}ms")

        ctx_speedup = results['sync_mean_ms'] / results['async_mean_ms'] if results['async_mean_ms'] > 0 else 0.0
        print(f"  Speedup: {ctx_speedup:.1f}x")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        print("""
For SQLite specifically:
  - Pure DB queries: Minimal speedup (SQLite serializes writes)
  - Mixed workloads: Significant speedup (I/O can overlap)

The REAL benefits of async QuerySystem:
  1. Non-blocking: Event loop free for other tasks
  2. Framework ready: Works with FastAPI/aiohttp without blocking
  3. Future-proof: Easy to switch to PostgreSQL/MySQL (true parallelism)
  4. Concurrent file I/O: Can read files while querying DB
""")

        # Markdown summary
        print("=" * 70)
        print("SHAREABLE SUMMARY")
        print("=" * 70)
        print(f"""
## QuerySystem v0.2.0 Async Benchmark Results

### Mixed Workload (DB + Network I/O)
| Approach | Time | Speedup |
|----------|------|---------|
| Sequential | {sync_mean:.1f}ms | baseline |
| Concurrent | {async_mean:.1f}ms | **{speedup:.1f}x faster** |

### Pure DB Context Building
| Approach | Time | Speedup |
|----------|------|---------|
| Sequential | {results['sync_mean_ms']:.1f}ms | baseline |
| Concurrent | {results['async_mean_ms']:.1f}ms | {ctx_speedup:.1f}x |

### Key Takeaway
Async shines when DB queries overlap with other I/O operations.
For pure SQLite queries, benefit is architectural (non-blocking),
not raw speed.
""")

    finally:
        await qs.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
