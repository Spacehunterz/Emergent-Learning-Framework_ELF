"""
Entry point for running query module as a script.

Usage:
    python -m query --context
    python -m query --validate
"""

from query.cli import main

if __name__ == '__main__':
    exit(main())
