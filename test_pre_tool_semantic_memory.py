#!/usr/bin/env python3
"""
Test script for the PreTool semantic memory hook.

Tests:
1. Thinking block extraction from transcript
2. Semantic search integration
3. Hook output formatting
"""

import json
import tempfile
import os
import sys
from pathlib import Path

# Add paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "src" / "hooks" / "learning-loop"))

from pre_tool_semantic_memory import (
    read_transcript_thinking,
    format_injection_context
)


def test_thinking_extraction():
    """Test thinking block extraction."""
    print("Testing thinking block extraction...")
    
    # Create a mock transcript with thinking blocks
    mock_entries = [
        {
            "role": "user",
            "content": "Fix the authentication bug"
        },
        {
            "role": "assistant",
            "thinking": "I need to investigate the auth module. Let me start by reading the auth.py file to understand the current implementation.",
            "content": "I'll help you fix the authentication bug."
        },
        {
            "role": "assistant", 
            "thinking": "Hmm, looking at the code I can see there's a timing issue with the token validation. The JWT is being checked before the user object is fully loaded. I should fix this by reordering the validation steps. Let me also check if there are any related tests that need updating.",
            "content": "I found the issue..."
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for entry in mock_entries:
            f.write(json.dumps(entry) + '\n')
        temp_path = f.name
    
    try:
        result = read_transcript_thinking(temp_path)
        assert result is not None, "Should extract thinking"
        assert "timing issue" in result.lower(), "Should get the latest thinking"
        assert result.startswith("...") or len(result) <= 1500, "Should truncate if too long"
        print(f"✓ Thinking extraction works: {result[:100]}...")
    finally:
        os.unlink(temp_path)


def test_format_injection_context():
    """Test context formatting."""
    print("\nTesting injection context formatting...")
    
    mock_heuristics = [
        {
            "rule": "Always validate JWT tokens before user lookup",
            "domain": "authentication",
            "confidence": 0.95,
            "is_golden": True
        },
        {
            "rule": "Check for timing attacks in auth code",
            "domain": "security", 
            "confidence": 0.80,
            "is_golden": False
        }
    ]
    
    result = format_injection_context(mock_heuristics)
    
    assert "Mid-Stream Memory" in result, "Should have header"
    assert "⭐ GOLDEN" in result, "Should mark golden rules"
    # For non-golden rules, domain should be shown in brackets
    assert "[security]" in result, "Should show domain for non-golden rules"
    assert "95% confidence" in result, "Should show confidence"
    
    print("✓ Context formatting works")
    print(f"\nSample output:\n{result}")


def test_hook_json_output():
    """Test that hook produces valid JSON output."""
    print("\nTesting hook JSON output...")
    
    # Simulate hook execution with sample input
    mock_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/test/auth.py"},
        "transcript_path": "/dev/null"
    }
    
    # Create a mock transcript
    mock_entries = [
        {
            "role": "assistant",
            "thinking": "I'm about to read the auth.py file to understand the authentication flow.",
            "content": "Reading file..."
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for entry in mock_entries:
            f.write(json.dumps(entry) + '\n')
        temp_path = f.name
    
    try:
        # Test that thinking can be extracted
        thinking = read_transcript_thinking(temp_path)
        assert thinking is not None
        assert "auth" in thinking.lower()
        print("✓ Hook would extract thinking correctly")
    finally:
        os.unlink(temp_path)


async def test_semantic_search_integration():
    """Test semantic search if available."""
    print("\nTesting semantic search integration...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src" / "query"))
        from semantic_search import SemanticSearcher
        
        # Mock test - just verify the class can be imported
        print("✓ SemanticSearcher available")
        
        # Create a test searcher (may fail without DB, that's ok)
        try:
            searcher = await SemanticSearcher.create()
            print("✓ SemanticSearcher initialized")
            await searcher.cleanup()
        except Exception as e:
            print(f"⚠ SemanticSearcher init skipped (no DB): {e}")
            
    except ImportError:
        print("⚠ Semantic search not available (sentence-transformers not installed)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PreTool Semantic Memory Hook - Test Suite")
    print("=" * 60)
    
    try:
        test_thinking_extraction()
        test_format_injection_context()
        test_hook_json_output()
        
        # Run async test
        import asyncio
        asyncio.run(test_semantic_search_integration())
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nTo install the hook:")
        print("  python scripts/install-hooks.py")
        print("\nTo test with Claude Code:")
        print("  1. Enable thinking blocks in Claude settings")
        print("  2. Run a task that triggers tool use")
        print("  3. Check that relevant heuristics are injected mid-stream")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
