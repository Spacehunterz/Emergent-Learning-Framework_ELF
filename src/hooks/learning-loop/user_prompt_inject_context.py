#!/usr/bin/env python3
"""
UserPromptSubmit hook - injects ELF context into user prompts.

Currently a stub that passes through without modification.
Future enhancement: automatically inject relevant heuristics/context.
"""
import json
import sys


def main():
    """Pass through without modification."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # For now, just pass through unchanged
        # Future: inject relevant context based on prompt content
        result = {
            "continue": True
        }

        print(json.dumps(result))

    except Exception as e:
        # On error, allow to continue
        print(json.dumps({"continue": True}))
        sys.exit(0)


if __name__ == "__main__":
    main()
