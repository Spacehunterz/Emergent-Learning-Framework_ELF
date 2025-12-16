#!/usr/bin/env python3
"""
Async vs Sync Benchmark for QuerySystem v0.2.0

Demonstrates the performance benefit of async concurrent queries
vs sequential (sync-style) execution.

Usage:
    python benchmarks/async_vs_sync.py
    python benchmarks/async_vs_sync.py --queries 20 --rounds 5
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path
from statistics import mean, stdev

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from query import QuerySystem


async def run_sequential(qs: QuerySystem, queries: list, timeout: int = 30) -> float:
    """Run queries one-by-one (simulating sync behavior)."""
    start = time.perf_counter()
    for domain in queries:
        await qs.query_by_domain(domain, limit=5, timeout=timeout)
    return time.perf_counter() - start


async def run_concurrent(qs: QuerySystem, queries: list, timeout: int = 30) -> float:
    """Run queries concurrently using asyncio.gather."""
    start = time.perf_counter()
    await asyncio.gather(*[
        qs.query_by_domain(domain, limit=5, timeout=timeout)
        for domain in queries
    ])
    return time.perf_counter() - start


async def run_benchmark(num_queries: int, num_rounds: int, verbose: bool = False) -> dict:
    """Run the complete benchmark."""

    # Sample domains to query (will cycle if needed)
    sample_domains = [
        "testing", "debugging", "coordination", "architecture",
        "security", "performance", "workflow", "infrastructure",
        "documentation", "refactoring", "error-handling", "validation"
    ]

    # Build query list
    queries = [sample_domains[i % len(sample_domains)] for i in range(num_queries)]

    qs = await QuerySystem.create(debug=False)

    try:
        sequential_times = []
        concurrent_times = []

        for round_num in range(num_rounds):
            if verbose:
                print(f"  Round {round_num + 1}/{num_rounds}...", end=" ", flush=True)

            # Run sequential
            seq_time = await run_sequential(qs, queries)
            sequential_times.append(seq_time)

            # Small pause between tests
            await asyncio.sleep(0.1)

            # Run concurrent
            conc_time = await run_concurrent(qs, queries)
            concurrent_times.append(conc_time)

            if verbose:
                print(f"seq={seq_time*1000:.1f}ms, conc={conc_time*1000:.1f}ms")

        return {
            "num_queries": num_queries,
            "num_rounds": num_rounds,
            "sequential": {
                "times_ms": [t * 1000 for t in sequential_times],
                "mean_ms": mean(sequential_times) * 1000,
                "stdev_ms": stdev(sequential_times) * 1000 if len(sequential_times) > 1 else 0,
            },
            "concurrent": {
                "times_ms": [t * 1000 for t in concurrent_times],
                "mean_ms": mean(concurrent_times) * 1000,
                "stdev_ms": stdev(concurrent_times) * 1000 if len(concurrent_times) > 1 else 0,
            },
            "speedup": mean(sequential_times) / mean(concurrent_times) if mean(concurrent_times) > 0 else 0,
        }

    finally:
        await qs.cleanup()


def print_results(results: list[dict]):
    """Print benchmark results in a shareable format."""

    print("\n" + "=" * 70)
    print("ASYNC vs SYNC BENCHMARK RESULTS")
    print("QuerySystem v0.2.0 (peewee-aio + aiosqlite)")
    print("=" * 70)

    # Table header
    print(f"\n{'Queries':<10} {'Sequential':<15} {'Concurrent':<15} {'Speedup':<10} {'Benefit':<15}")
    print("-" * 70)

    for r in results:
        seq_ms = r["sequential"]["mean_ms"]
        conc_ms = r["concurrent"]["mean_ms"]
        speedup = r["speedup"]
        benefit = ((seq_ms - conc_ms) / seq_ms * 100) if seq_ms > 0 else 0

        print(f"{r['num_queries']:<10} {seq_ms:>10.1f}ms    {conc_ms:>10.1f}ms    {speedup:>6.1f}x    {benefit:>10.1f}% faster")

    print("-" * 70)

    # Summary
    avg_speedup = mean([r["speedup"] for r in results])
    print(f"\nAverage speedup: {avg_speedup:.1f}x faster with async concurrency")

    # ASCII chart
    print("\n" + "=" * 70)
    print("VISUAL COMPARISON (Sequential vs Concurrent)")
    print("=" * 70 + "\n")

    max_time = max(r["sequential"]["mean_ms"] for r in results)
    bar_width = 40

    for r in results:
        seq_ms = r["sequential"]["mean_ms"]
        conc_ms = r["concurrent"]["mean_ms"]

        seq_bar = int((seq_ms / max_time) * bar_width) if max_time > 0 else 0
        conc_bar = int((conc_ms / max_time) * bar_width) if max_time > 0 else 0

        print(f"{r['num_queries']} queries:")
        print(f"  Sequential : {'█' * seq_bar}{'░' * (bar_width - seq_bar)} {seq_ms:.1f}ms")
        print(f"  Concurrent : {'█' * conc_bar}{'░' * (bar_width - conc_bar)} {conc_ms:.1f}ms")
        print()

    # Markdown table for sharing
    print("=" * 70)
    print("MARKDOWN TABLE (copy for sharing)")
    print("=" * 70 + "\n")

    print("| Queries | Sequential | Concurrent | Speedup |")
    print("|---------|------------|------------|---------|")
    for r in results:
        seq_ms = r["sequential"]["mean_ms"]
        conc_ms = r["concurrent"]["mean_ms"]
        speedup = r["speedup"]
        print(f"| {r['num_queries']} | {seq_ms:.1f}ms | {conc_ms:.1f}ms | {speedup:.1f}x |")

    print(f"\n*Average speedup: {avg_speedup:.1f}x with async concurrency*")


async def main():
    parser = argparse.ArgumentParser(description="Async vs Sync Benchmark")
    parser.add_argument("--queries", type=int, nargs="+", default=[5, 10, 15, 20],
                        help="Number of queries to run (default: 5 10 15 20)")
    parser.add_argument("--rounds", type=int, default=3,
                        help="Number of rounds per test (default: 3)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show progress during benchmark")

    args = parser.parse_args()

    print("\nAsync vs Sync Benchmark")
    print(f"Testing with {args.queries} queries, {args.rounds} rounds each\n")

    results = []

    for num_queries in args.queries:
        print(f"Benchmarking {num_queries} queries...")
        result = await run_benchmark(num_queries, args.rounds, args.verbose)
        results.append(result)

    print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
