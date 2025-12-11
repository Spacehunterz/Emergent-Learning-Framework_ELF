#!/usr/bin/env python3
"""
Demonstration of the Advisory Verification System

This script simulates what happens when risky code is added.
Run this to see the advisory system in action.
"""

import json
import sys
from pathlib import Path

# Add the hook directory to path
sys.path.insert(0, str(Path(__file__).parent))

from post_tool_learning import AdvisoryVerifier


def demo_safe_code():
    """Demonstrate safe code - no warnings."""
    print("\n" + "="*60)
    print("DEMO 1: Safe Code")
    print("="*60)

    verifier = AdvisoryVerifier()

    old_content = """
def calculate_sum(a, b):
    return a + b
"""

    new_content = """
def calculate_sum(a, b):
    return a + b

def calculate_product(a, b):
    return a * b
"""

    result = verifier.analyze_edit("math_utils.py", old_content, new_content)

    print(f"\nFile: math_utils.py")
    print(f"Has Warnings: {result['has_warnings']}")
    print(f"Recommendation: {result['recommendation']}")
    print("\nResult: All clear! No risky patterns detected.")


def demo_single_warning():
    """Demonstrate single warning."""
    print("\n" + "="*60)
    print("DEMO 2: Single Warning (eval usage)")
    print("="*60)

    verifier = AdvisoryVerifier()

    old_content = "# Calculator"

    new_content = """
# Calculator
def evaluate_expression(expr):
    result = eval(expr)  # User input evaluated
    return result
"""

    result = verifier.analyze_edit("calculator.py", old_content, new_content)

    print(f"\nFile: calculator.py")
    print(f"Has Warnings: {result['has_warnings']}")
    print(f"Warning Count: {len(result['warnings'])}")

    for warning in result['warnings']:
        print(f"\n  Category: {warning['category']}")
        print(f"  Message: {warning['message']}")
        print(f"  Line: {warning['line_preview']}")

    print(f"\nRecommendation: {result['recommendation']}")
    print("\nResult: Operation would PROCEED with advisory warning.")


def demo_multiple_warnings():
    """Demonstrate multiple warnings triggering escalation."""
    print("\n" + "="*60)
    print("DEMO 3: Multiple Warnings (escalation recommended)")
    print("="*60)

    verifier = AdvisoryVerifier()

    old_content = "# Database config"

    new_content = """
# Database config
import subprocess

def get_database_config():
    password = "hardcoded_secret123"
    api_key = "sk-1234567890abcdef"

    # Execute user command
    result = subprocess.run(user_cmd, shell=True)

    # Build SQL query
    query = "SELECT * FROM users WHERE name = " + user_input

    return eval(config_string)
"""

    result = verifier.analyze_edit("db_config.py", old_content, new_content)

    print(f"\nFile: db_config.py")
    print(f"Has Warnings: {result['has_warnings']}")
    print(f"Warning Count: {len(result['warnings'])}")

    print("\nDetected Issues:")
    for i, warning in enumerate(result['warnings'], 1):
        print(f"\n  {i}. Category: {warning['category']}")
        print(f"     Message: {warning['message']}")
        print(f"     Line: {warning['line_preview'][:60]}...")

    print(f"\nRecommendation: {result['recommendation']}")
    print("\nResult: Operation would PROCEED, but CEO escalation recommended.")


def demo_existing_code_not_flagged():
    """Demonstrate that existing risky code is not flagged."""
    print("\n" + "="*60)
    print("DEMO 4: Existing Risky Code (not flagged)")
    print("="*60)

    verifier = AdvisoryVerifier()

    old_content = """
# Legacy code - already has eval()
def legacy_function():
    return eval(user_input)
"""

    new_content = """
# Legacy code - already has eval()
def legacy_function():
    return eval(user_input)

# New safe function
def new_function():
    return json.loads(user_input)  # Safe alternative
"""

    result = verifier.analyze_edit("legacy.py", old_content, new_content)

    print(f"\nFile: legacy.py")
    print(f"Old code contains: eval() usage (legacy)")
    print(f"New code adds: Safe JSON parsing")
    print(f"\nHas Warnings: {result['has_warnings']}")
    print(f"Recommendation: {result['recommendation']}")
    print("\nResult: No warnings! Only NEW risky code is flagged.")


def demo_json_output():
    """Show what gets returned to the hook system."""
    print("\n" + "="*60)
    print("DEMO 5: Hook Output Format")
    print("="*60)

    verifier = AdvisoryVerifier()

    new_content = """
password = "secret"
api_key = "key123"
"""

    result = verifier.analyze_edit("config.py", "", new_content)

    # This is what the hook would output
    hook_output = {
        "decision": "approve",  # ALWAYS approve
        "advisory": result if result['has_warnings'] else None
    }

    print("\nHook Output (JSON):")
    print(json.dumps(hook_output, indent=2))

    print("\nKey Points:")
    print("  - decision: ALWAYS 'approve' (never blocks)")
    print("  - advisory: Attached if warnings exist")
    print("  - Warnings logged to building for analysis")


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# Advisory Verification System - Live Demonstration")
    print("#"*60)

    demo_safe_code()
    demo_single_warning()
    demo_multiple_warnings()
    demo_existing_code_not_flagged()
    demo_json_output()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
The Advisory Verification System:

1. Analyzes Edit/Write operations for risky patterns
2. Checks ONLY newly added lines (not existing code)
3. Provides warnings via stderr and building logs
4. NEVER blocks operations (always returns "approve")
5. Recommends CEO escalation for multiple warnings
6. Trusts humans to make the final decision

Philosophy: Advisory only. Human decides. Always.
    """)
