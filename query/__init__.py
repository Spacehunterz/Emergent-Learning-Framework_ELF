"""
Emergent Learning Framework - Query System (v0.2.0 - Async)

This module provides the async query interface for the Emergent Learning Framework,
allowing agents to query the knowledge base for golden rules, heuristics,
learnings, experiments, and more.

Usage (async):
    import asyncio
    from query import QuerySystem

    async def main():
        qs = await QuerySystem.create()
        try:
            context = await qs.build_context("My task", domain="debugging")
            print(context)
        finally:
            await qs.cleanup()

    asyncio.run(main())

CLI Usage (unchanged):
    python -m query --context --domain debugging
    python query/query.py --validate
"""

# Public API exports
from .core import QuerySystem
from .exceptions import (
    QuerySystemError,
    ValidationError,
    DatabaseError,
    TimeoutError,
    ConfigurationError,
)
from .cli import main

__all__ = [
    'QuerySystem',
    'QuerySystemError',
    'ValidationError',
    'DatabaseError',
    'TimeoutError',
    'ConfigurationError',
    'main',
]

__version__ = '0.2.0'
