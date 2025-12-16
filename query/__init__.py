"""
Emergent Learning Framework - Query System

This module provides the query interface for the Emergent Learning Framework,
allowing agents to query the knowledge base for golden rules, heuristics,
learnings, experiments, and more.

Usage:
    from query import QuerySystem

    qs = QuerySystem()
    context = qs.build_context("My task", domain="debugging")
    print(context)

CLI Usage:
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

__version__ = '2.1.0'
