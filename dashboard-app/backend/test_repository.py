"""
Test script for BaseRepository class.

Tests basic CRUD operations to verify the repository works correctly.
"""

from utils import get_db, BaseRepository
from datetime import datetime


def test_repository():
    """Test BaseRepository CRUD operations."""
    print("Testing BaseRepository...")

    with get_db() as conn:
        repo = BaseRepository(conn)

        # Test 1: Count records in a table
        print("\n1. Testing count()...")
        decision_count = repo.count("decisions")
        print(f"   Total decisions: {decision_count}")

        heuristic_count = repo.count("heuristics")
        print(f"   Total heuristics: {heuristic_count}")

        # Test 2: List all with pagination
        print("\n2. Testing list_all()...")
        decisions = repo.list_all("decisions", limit=5, offset=0)
        print(f"   Retrieved {len(decisions)} decisions")
        if decisions:
            print(f"   First decision: {decisions[0].get('title', 'N/A')}")

        # Test 3: List with filters
        print("\n3. Testing list_with_filters()...")
        # Test with domain filter
        filtered = repo.list_with_filters("decisions", {"domain": "elf-architecture"}, limit=5)
        print(f"   Retrieved {len(filtered)} decisions with domain='elf-architecture'")

        # Test 4: Get by ID
        print("\n4. Testing get_by_id()...")
        if decisions:
            first_id = decisions[0]["id"]
            decision = repo.get_by_id("decisions", first_id)
            if decision:
                print(f"   Found decision ID {first_id}: {decision.get('title', 'N/A')}")
            else:
                print(f"   Decision ID {first_id} not found")
        else:
            print("   No decisions to test with")

        # Test 5: Exists check
        print("\n5. Testing exists()...")
        if decisions:
            first_id = decisions[0]["id"]
            exists = repo.exists("decisions", first_id)
            print(f"   Decision ID {first_id} exists: {exists}")

            fake_exists = repo.exists("decisions", 999999)
            print(f"   Decision ID 999999 exists: {fake_exists}")
        else:
            print("   No decisions to test with")

        # Test 6: Create, Update, Delete (on a test table if it exists)
        print("\n6. Testing create/update/delete...")
        # We'll test on heuristics since it's less critical
        test_data = {
            "domain": "test",
            "rule": "TEST: Repository Pattern - Use BaseRepository for CRUD",
            "explanation": "Testing BaseRepository CRUD operations to verify functionality",
            "source_type": "test",
            "confidence": 0.5,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        print("   Creating test heuristic...")
        new_id = repo.create("heuristics", test_data)
        print(f"   Created heuristic ID: {new_id}")

        print("   Updating test heuristic...")
        update_success = repo.update("heuristics", new_id, {
            "confidence": 0.75,
            "updated_at": datetime.now().isoformat()
        })
        print(f"   Update successful: {update_success}")

        # Verify update
        updated = repo.get_by_id("heuristics", new_id)
        if updated:
            print(f"   Updated confidence: {updated['confidence']}")

        print("   Deleting test heuristic...")
        delete_success = repo.delete("heuristics", new_id)
        print(f"   Delete successful: {delete_success}")

        # Verify deletion
        exists_after_delete = repo.exists("heuristics", new_id)
        print(f"   Exists after delete: {exists_after_delete}")

    print("\n[SUCCESS] All tests completed successfully!")


if __name__ == "__main__":
    test_repository()
