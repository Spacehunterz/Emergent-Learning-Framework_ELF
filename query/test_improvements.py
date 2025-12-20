#!/usr/bin/env python3
"""
Test script for query.py improvements
Tests all edge cases and new features
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from query import QuerySystem, ValidationError, DatabaseError, ReadonlyDatabaseError

def test_readonly_database():
    """Test readonly database handling"""
    print("Test 1: Readonly database handling...")
    try:
        # This should handle gracefully
        qs = QuerySystem(debug=True)
        stats = qs.get_statistics()
        print("  ✓ Statistics retrieved successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_tag_count_limit():
    """Test tag count validation"""
    print("\nTest 2: Tag count limits...")
    qs = QuerySystem()
    
    # Test with 60 tags (should fail)
    try:
        many_tags = [f"tag{i}" for i in range(60)]
        qs.query_by_tags(many_tags)
        print("  ✗ Should have raised ValidationError for 60 tags")
        return False
    except ValidationError as e:
        print(f"  ✓ Correctly rejected 60 tags: {e}")
        return True
    except Exception as e:
        print(f"  ✗ Wrong exception: {e}")
        return False

def test_input_validation():
    """Test input validation"""
    print("\nTest 3: Input validation...")
    qs = QuerySystem()
    passed = 0
    total = 0
    
    # Test invalid domain
    total += 1
    try:
        qs.query_by_domain("", limit=10)
        print("  ✗ Should reject empty domain")
    except ValidationError:
        print("  ✓ Rejected empty domain")
        passed += 1
    
    # Test invalid limit
    total += 1
    try:
        qs.query_by_domain("test", limit=-5)
        print("  ✗ Should reject negative limit")
    except ValidationError:
        print("  ✓ Rejected negative limit")
        passed += 1
    
    # Test limit too large
    total += 1
    try:
        qs.query_by_domain("test", limit=99999)
        print("  ✗ Should reject limit > 1000")
    except ValidationError:
        print("  ✓ Rejected limit > 1000")
        passed += 1
    
    print(f"  Passed {passed}/{total} validation tests")
    return passed == total

def test_debug_mode():
    """Test debug mode"""
    print("\nTest 4: Debug mode...")
    try:
        qs = QuerySystem(debug=True)
        # Debug messages should print to stderr
        qs.query_recent(limit=1)
        print("  ✓ Debug mode works")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_timeout():
    """Test custom timeout"""
    print("\nTest 5: Custom timeout...")
    try:
        qs = QuerySystem(timeout=60)
        print("  ✓ Custom timeout set successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def main():
    print("="*60)
    print("Testing query.py improvements")
    print("="*60)
    
    tests = [
        test_readonly_database,
        test_tag_count_limit,
        test_input_validation,
        test_debug_mode,
        test_timeout,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
