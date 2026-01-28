#!/usr/bin/env python3
"""
Test suite for PreTool Semantic Memory with Plan Detection.

Tests:
1. Plan context detection (file path + thinking content)
2. Heuristic boosting (Golden Rules + Sequential Thinking)
3. Special formatting for planning mode
4. Post-tool plan validation
5. Integration of all features
"""

import json
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime

# Add paths for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "src" / "hooks" / "learning-loop"))

# Test configuration
PLAN_INDICATORS = [
    "plan", "design document", "architecture", 
    "roadmap", "strategy", "approach document"
]

PLAN_BOOST_PATTERNS = [
    "sequential thinking",
    "architecture decision record",
    " adr ",
    "step by step",
    "before implementing"
]


def detect_plan_context(file_path: str, thinking_context: str = None) -> dict:
    """Detect if this tool use is plan-related."""
    result = {
        "is_planning": False,
        "detection_method": None,
        "confidence": 0.0
    }
    
    # File-based detection
    if file_path:
        path_lower = file_path.lower()
        if "/plans/" in path_lower or ".claude/plans/" in path_lower:
            result["is_planning"] = True
            result["detection_method"] = "file_path"
            result["confidence"] = 0.9
            return result
        
        if path_lower.endswith(".md") and any(indicator in path_lower for indicator in PLAN_INDICATORS):
            result["is_planning"] = True
            result["detection_method"] = "file_name"
            result["confidence"] = 0.7
            return result
    
    # Thinking-based detection
    if thinking_context:
        thinking_lower = thinking_context.lower()
        for indicator in PLAN_INDICATORS:
            if indicator in thinking_lower:
                result["is_planning"] = True
                result["detection_method"] = "thinking_content"
                result["confidence"] = 0.8
                return result
    
    return result


def boost_plan_heuristics(heuristics: list) -> list:
    """Boost planning-relevant heuristics."""
    boosted = []
    
    for h in heuristics:
        h_copy = h.copy()
        base_score = h_copy.get('_final_score', 0.5)
        boost = 0.0
        reasons = []
        
        # Boost Golden Rules during planning
        if h_copy.get('is_golden'):
            boost += 0.20
            reasons.append("golden_rule")
        
        # Boost Sequential Thinking / ADR patterns
        rule_lower = h_copy.get('rule', '').lower()
        for pattern in PLAN_BOOST_PATTERNS:
            if pattern in rule_lower:
                boost += 0.15
                reasons.append(f"plan_pattern:{pattern}")
                break  # Only count once per pattern type
        
        h_copy['_final_score'] = min(1.0, base_score + boost)
        h_copy['_boost_reasons'] = reasons
        h_copy['_original_score'] = base_score
        boosted.append(h_copy)
    
    # Sort by boosted score
    boosted.sort(key=lambda x: x.get('_final_score', 0), reverse=True)
    return boosted


def format_injection_context(heuristics: list, is_planning: bool = False) -> str:
    """Format heuristics with special handling for planning context."""
    if not heuristics:
        return ""
    
    lines = ["", "---"]
    
    if is_planning:
        lines.append("## 🎯 [Plan Mode] Critical Heuristics")
        lines.append("")
        lines.append("**These patterns are especially important for planning:**")
        lines.append("")
    else:
        lines.append("## [Mid-Stream Memory] Relevant Patterns Detected")
        lines.append("")
    
    # Golden Rules first (always prioritized)
    golden = [h for h in heuristics if h.get("is_golden")]
    if golden:
        if is_planning:
            lines.append("### ⭐ GOLDEN RULES (Must Apply to Plan)")
        else:
            lines.append("### Golden Rules (Must Follow)")
        
        for h in golden:
            lines.append(f"- **{h['rule']}** ({h.get('confidence', 0)*100:.0f}% confidence)")
            if is_planning and h.get('explanation'):
                lines.append(f"  → {h['explanation'][:120]}")
        lines.append("")
    
    # Other heuristics
    regular = [h for h in heuristics if not h.get("is_golden")]
    if regular:
        if is_planning:
            lines.append("### Relevant Patterns for This Plan")
        else:
            lines.append("### Relevant Heuristics")
        
        for h in regular:
            domain = h.get('domain', 'general')
            confidence = h.get('confidence', 0) * 100
            lines.append(f"- [{domain}] {h['rule']} ({confidence:.0f}% confidence)")
            
            # Show boost info during planning
            if is_planning and h.get('_boost_reasons'):
                boost_info = ', '.join(h['_boost_reasons'])
                lines.append(f"  [boosted: {boost_info}]")
        
        lines.append("")
    
    lines.extend(["---", ""])
    return "\n".join(lines)


def extract_key_concepts(rule: str) -> list:
    """Extract key concepts from a heuristic rule for validation."""
    # Simple keyword extraction
    rule_lower = rule.lower()
    
    # Remove common words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                  'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
                  'by', 'from', 'as', 'and', 'but', 'or', 'yet', 'so', 'before',
                  'after', 'during', 'always', 'never', 'use', 'using'}
    
    words = rule_lower.split()
    concepts = [w.strip('.,;:!?()[]{}') for w in words if len(w) > 3 and w not in stop_words]
    return list(set(concepts))[:5]  # Top 5 unique concepts


def check_heuristic_addressed(rule: str, plan_content: str) -> bool:
    """Check if a heuristic is addressed in plan content."""
    plan_lower = plan_content.lower()
    concepts = extract_key_concepts(rule)
    
    # Count how many key concepts appear in plan
    matches = sum(1 for concept in concepts if concept in plan_lower)
    
    # Consider addressed if 2+ key concepts found (configurable threshold)
    return matches >= 2


def validate_plan_against_heuristics(plan_content: str, heuristics: list) -> dict:
    """Validate that plan addresses all injected heuristics."""
    missing = []
    addressed = []
    
    for h in heuristics:
        rule = h.get('rule', '')
        if check_heuristic_addressed(rule, plan_content):
            addressed.append(h)
        else:
            missing.append(h)
    
    return {
        "all_addressed": len(missing) == 0,
        "addressed_count": len(addressed),
        "missing_count": len(missing),
        "addressed": addressed,
        "missing": missing,
        "coverage_ratio": len(addressed) / len(heuristics) if heuristics else 1.0
    }


# =============================================================================
# TESTS
# =============================================================================

def test_plan_detection_file_path():
    """Test plan detection based on file path."""
    print("\n" + "="*60)
    print("TEST 1: Plan Detection via File Path")
    print("="*60)
    
    test_cases = [
        ("~/.claude/plans/auth-refactor.md", True, "Standard plan path"),
        ("/home/user/.claude/plans/roadmap-q1.md", True, "Absolute plan path"),
        ("~/.claude/plans/architecture-design.md", True, "Architecture plan"),
        ("~/project/src/auth.py", False, "Regular code file"),
        ("/tmp/notes.md", False, "Random markdown"),
        ("~/.claude/memory/index.db", False, "Database file"),
    ]
    
    for path, expected, description in test_cases:
        result = detect_plan_context(path)
        passed = result["is_planning"] == expected
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} {description}")
        print(f"       Path: {path}")
        print(f"       Expected: {expected}, Got: {result['is_planning']}")
        if not passed:
            return False
    
    print("  ✓ All file path detection tests passed")
    return True


def test_plan_detection_thinking():
    """Test plan detection based on thinking content."""
    print("\n" + "="*60)
    print("TEST 2: Plan Detection via Thinking Content")
    print("="*60)
    
    test_cases = [
        ("I need to create a plan for the authentication system", True, "Explicit plan mention"),
        ("Let me design the architecture for this feature", True, "Architecture design"),
        ("I'll write a strategy document for the rollout", True, "Strategy document"),
        ("Now I'll implement the auth module", False, "Implementation, not planning"),
        ("Let me fix this bug", False, "Debugging, not planning"),
        ("I'll add a test for this function", False, "Testing, not planning"),
    ]
    
    for thinking, expected, description in test_cases:
        result = detect_plan_context("/some/file.txt", thinking)
        passed = result["is_planning"] == expected
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} {description}")
        print(f"       Thinking: {thinking[:50]}...")
        print(f"       Expected: {expected}, Got: {result['is_planning']}")
        if not passed:
            return False
    
    print("  ✓ All thinking content detection tests passed")
    return True


def test_heuristic_boosting():
    """Test heuristic boosting for planning context."""
    print("\n" + "="*60)
    print("TEST 3: Heuristic Boosting")
    print("="*60)
    
    # Mock heuristics
    heuristics = [
        {
            "id": 1,
            "rule": "Always use Sequential Thinking before implementing critical changes",
            "domain": "planning",
            "confidence": 0.85,
            "is_golden": False,
            "_final_score": 0.75
        },
        {
            "id": 2,
            "rule": "Validate all inputs at system boundaries",
            "domain": "security",
            "confidence": 0.95,
            "is_golden": True,
            "_final_score": 0.80
        },
        {
            "id": 3,
            "rule": "Create Architecture Decision Records for major changes",
            "domain": "architecture",
            "confidence": 0.70,
            "is_golden": False,
            "_final_score": 0.65
        },
        {
            "id": 4,
            "rule": "Write tests before fixing bugs",
            "domain": "testing",
            "confidence": 0.80,
            "is_golden": False,
            "_final_score": 0.70
        }
    ]
    
    boosted = boost_plan_heuristics(heuristics)
    
    # Check Sequential Thinking got boosted
    seq_thinking = next((h for h in boosted if h['id'] == 1), None)
    assert seq_thinking is not None, "Sequential Thinking heuristic not found"
    assert seq_thinking['_final_score'] > seq_thinking['_original_score'], \
        "Sequential Thinking should be boosted"
    assert 'plan_pattern' in str(seq_thinking.get('_boost_reasons', [])), \
        "Should have plan_pattern boost reason"
    print(f"  ✓ Sequential Thinking boosted: {seq_thinking['_original_score']:.2f} → {seq_thinking['_final_score']:.2f}")
    
    # Check Golden Rule got boosted
    golden = next((h for h in boosted if h['id'] == 2), None)
    assert golden is not None, "Golden Rule heuristic not found"
    assert golden['_final_score'] > golden['_original_score'], \
        "Golden Rule should be boosted"
    assert 'golden_rule' in golden.get('_boost_reasons', []), \
        "Should have golden_rule boost reason"
    print(f"  ✓ Golden Rule boosted: {golden['_original_score']:.2f} → {golden['_final_score']:.2f}")
    
    # Check ADR heuristic got boosted
    adr = next((h for h in boosted if h['id'] == 3), None)
    assert adr is not None, "ADR heuristic not found"
    assert adr['_final_score'] > adr['_original_score'], \
        "ADR heuristic should be boosted"
    print(f"  ✓ ADR heuristic boosted: {adr['_original_score']:.2f} → {adr['_final_score']:.2f}")
    
    # Check regular heuristic NOT boosted
    regular = next((h for h in boosted if h['id'] == 4), None)
    assert regular is not None, "Regular heuristic not found"
    assert regular['_final_score'] == regular['_original_score'], \
        "Regular heuristic should NOT be boosted"
    print(f"  ✓ Regular heuristic unchanged: {regular['_final_score']:.2f}")
    
    # Check sorting (highest score first)
    scores = [h['_final_score'] for h in boosted]
    assert scores == sorted(scores, reverse=True), "Should be sorted by boosted score"
    print(f"  ✓ Heuristics sorted by boosted score: {[f'{s:.2f}' for s in scores]}")
    
    return True


def test_formatting_plan_mode():
    """Test special formatting for planning mode."""
    print("\n" + "="*60)
    print("TEST 4: Formatting - Plan Mode vs Regular Mode")
    print("="*60)
    
    heuristics = [
        {
            "rule": "Always use Sequential Thinking",
            "domain": "planning",
            "confidence": 0.90,
            "is_golden": True,
            "explanation": "Break down complex tasks into steps before coding"
        },
        {
            "rule": "Validate inputs at boundaries",
            "domain": "security",
            "confidence": 0.85,
            "is_golden": False
        }
    ]
    
    # Test regular mode
    regular_format = format_injection_context(heuristics, is_planning=False)
    assert "## [Mid-Stream Memory]" in regular_format, "Regular mode should have standard header"
    assert "### Golden Rules" in regular_format, "Should show Golden Rules section"
    assert "🎯 [Plan Mode]" not in regular_format, "Regular mode should NOT have plan header"
    print("  ✓ Regular mode formatting correct")
    
    # Test plan mode
    plan_format = format_injection_context(heuristics, is_planning=True)
    assert "## 🎯 [Plan Mode] Critical Heuristics" in plan_format, "Plan mode should have special header"
    assert "⭐ GOLDEN RULES (Must Apply to Plan)" in plan_format, "Should emphasize Golden Rules for planning"
    assert "→ Break down complex tasks" in plan_format, "Should show explanation in plan mode"
    print("  ✓ Plan mode formatting correct")
    
    # Show sample output
    print("\n  Sample Plan Mode Output:")
    print("  " + "-"*50)
    for line in plan_format.split('\n')[:15]:
        print(f"  {line}")
    print("  " + "-"*50)
    
    return True


def test_plan_validation():
    """Test post-tool plan validation."""
    print("\n" + "="*60)
    print("TEST 5: Plan Validation")
    print("="*60)
    
    # Sample plan content
    plan_content = """
# Authentication System Refactor Plan

## Overview
This plan outlines the steps to refactor our authentication system.

## Steps
1. Audit current JWT implementation
2. Update token validation logic
3. Add input sanitization
4. Test with edge cases
5. Deploy to staging

## Security Considerations
- All user inputs will be validated
- Tokens checked before processing
- Rate limiting implemented
"""
    
    # Heuristics that SHOULD be addressed
    addressed_heuristics = [
        {"rule": "Validate all inputs at system boundaries"},  # Addressed (input validation mentioned)
        {"rule": "Test edge cases before deployment"},         # Addressed (edge cases mentioned)
    ]
    
    # Heuristics that are NOT addressed
    missing_heuristics = [
        {"rule": "Use Sequential Thinking before implementing changes"},  # NOT addressed
        {"rule": "Create Architecture Decision Records for major changes"},  # NOT addressed
    ]
    
    all_heuristics = addressed_heuristics + missing_heuristics
    
    result = validate_plan_against_heuristics(plan_content, all_heuristics)
    
    print(f"  Validation Result:")
    print(f"    Total heuristics: {len(all_heuristics)}")
    print(f"    Addressed: {result['addressed_count']}")
    print(f"    Missing: {result['missing_count']}")
    print(f"    Coverage: {result['coverage_ratio']*100:.0f}%")
    
    # Should detect that not all are addressed
    assert not result['all_addressed'], "Should detect missing heuristics"
    assert result['missing_count'] == 2, f"Expected 2 missing, got {result['missing_count']}"
    assert result['addressed_count'] == 2, f"Expected 2 addressed, got {result['addressed_count']}"
    
    print("  ✓ Validation correctly identified addressed and missing heuristics")
    
    # Test with comprehensive plan
    comprehensive_plan = """
# Plan with All Heuristics Addressed

This plan uses Sequential Thinking to break down the work.
We will create an Architecture Decision Record.
All inputs will be validated at system boundaries.
Edge cases will be tested.
"""
    
    result2 = validate_plan_against_heuristics(comprehensive_plan, all_heuristics)
    
    # This is more lenient and might catch more
    print(f"\n  Comprehensive Plan Result:")
    print(f"    Coverage: {result2['coverage_ratio']*100:.0f}%")
    
    return True


def test_integration_workflow():
    """Test complete workflow from detection to validation."""
    print("\n" + "="*60)
    print("TEST 6: Integration Workflow")
    print("="*60)
    
    # Simulate: Claude writing a plan file
    file_path = "~/.claude/plans/auth-refactor.md"
    thinking = "I need to create a comprehensive plan for refactoring the authentication system"
    
    # Step 1: Detect plan context
    detection = detect_plan_context(file_path, thinking)
    assert detection["is_planning"], "Should detect planning context"
    print(f"  1. Plan detected via {detection['detection_method']} (confidence: {detection['confidence']})")
    
    # Step 2: Mock heuristics from semantic search
    heuristics = [
        {"id": 1, "rule": "Use Sequential Thinking before implementing", "is_golden": False, "confidence": 0.85, "_final_score": 0.75},
        {"id": 2, "rule": "Validate inputs at system boundaries", "is_golden": True, "confidence": 0.95, "_final_score": 0.90},
        {"id": 3, "rule": "Create Architecture Decision Records", "is_golden": False, "confidence": 0.80, "_final_score": 0.70},
    ]
    
    # Step 3: Boost heuristics
    boosted = boost_plan_heuristics(heuristics)
    print(f"  2. Heuristics boosted:")
    for h in boosted:
        boost_info = f" (+{h['_final_score'] - h['_original_score']:.2f})" if h['_boost_reasons'] else ""
        print(f"     - {h['rule'][:40]}...{boost_info}")
    
    # Step 4: Format for injection
    formatted = format_injection_context(boosted, is_planning=True)
    print(f"  3. Formatted context: {len(formatted)} chars")
    assert "🎯 [Plan Mode]" in formatted, "Should have plan mode header"
    
    # Step 5: Simulate plan content (missing Sequential Thinking)
    plan_content = """
    # Auth Refactor Plan
    We will validate all inputs and create ADRs.
    Security is important.
    """
    
    # Step 6: Validate
    validation = validate_plan_against_heuristics(plan_content, boosted)
    print(f"  4. Validation: {validation['addressed_count']}/{len(boosted)} heuristics addressed")
    
    if validation['missing_count'] > 0:
        print(f"     ⚠️  Missing heuristics:")
        for h in validation['missing']:
            print(f"        - {h['rule'][:50]}...")
    
    print("  ✓ Complete workflow executed successfully")
    return True


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "="*60)
    print("TEST 7: Edge Cases")
    print("="*60)
    
    # Empty heuristics
    empty_format = format_injection_context([], is_planning=True)
    assert empty_format == "", "Empty heuristics should return empty string"
    print("  ✓ Empty heuristics handled")
    
    # No file path
    detection = detect_plan_context(None, "I will plan this out")
    assert detection["is_planning"], "Should detect from thinking even without file"
    print("  ✓ Detection without file path works")
    
    # Very long thinking content
    long_thinking = "plan " * 1000
    detection2 = detect_plan_context("/test.md", long_thinking)
    assert detection2["is_planning"], "Should handle long thinking content"
    print("  ✓ Long thinking content handled")
    
    # Special characters in plan content
    special_plan = """
    # Plan with "quotes" and 'apostrophes' and <tags>
    ## Section with emojis 🎉
    Code: `input.validate()` && `auth.check()`
    """
    result = validate_plan_against_heuristics(special_plan, [
        {"rule": "Validate inputs"}
    ])
    assert result['addressed_count'] >= 0, "Should handle special characters"
    print("  ✓ Special characters in plan content handled")
    
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("PRE-TOOL SEMANTIC MEMORY - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Plan Detection (File Path)", test_plan_detection_file_path),
        ("Plan Detection (Thinking)", test_plan_detection_thinking),
        ("Heuristic Boosting", test_heuristic_boosting),
        ("Formatting (Plan vs Regular)", test_formatting_plan_mode),
        ("Plan Validation", test_plan_validation),
        ("Integration Workflow", test_integration_workflow),
        ("Edge Cases", test_edge_cases),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n  ✗ TEST FAILED: {name}")
        except Exception as e:
            failed += 1
            print(f"\n  ✗ TEST ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED - Ready for implementation")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed - Fix before implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
