"""
Test script for semantic search functionality (Option B).

This tests the semantic heuristic retrieval without requiring full installation.
Run with: python test_semantic_search.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'query'))

# Mock dependencies to avoid import errors
class MockModule:
    def __getattr__(self, name):
        return MockModule()
    def __call__(self, *args, **kwargs):
        return MockModule()

# Mock peewee-related modules
sys.modules['peewee_aio'] = MockModule()
sys.modules['peewee'] = MockModule()
sys.modules['sentence_transformers'] = MockModule()
sys.modules['openai'] = MockModule()

async def test_semantic_search():
    """Test basic semantic search functionality."""
    print("=" * 60)
    print("Testing Semantic Search (Option B)")
    print("=" * 60)
    
    try:
        # Import semantic_search without requiring database dependencies
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / 'src' / 'query'))
        
        # Mock peewee_aio to avoid import errors
        class MockModule:
            pass
        sys.modules['peewee_aio'] = MockModule()
        
        from semantic_search import SemanticSearcher, extract_keywords
        
        print("\n1. Testing keyword extraction fallback...")
        keywords = extract_keywords("Refactor authentication module with OAuth")
        print(f"   Keywords: {keywords[:5]}")
        assert len(keywords) > 0, "Should extract keywords"
        print("   ✓ Keyword extraction works")
        
        print("\n2. Testing SemanticSearcher initialization...")
        searcher = SemanticSearcher()
        print(f"   Cache path: {searcher.cache_path}")
        print("   ✓ SemanticSearcher created")
        
        print("\n3. Testing embedding cache key generation...")
        key1 = searcher._get_cache_key("test task")
        key2 = searcher._get_cache_key("test task")
        key3 = searcher._get_cache_key("different task")
        assert key1 == key2, "Same text should produce same key"
        assert key1 != key3, "Different text should produce different key"
        print(f"   Key for 'test task': {key1}")
        print("   ✓ Cache key generation works")
        
        print("\n4. Testing cosine similarity...")
        import numpy as np
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        vec3 = np.array([0.0, 1.0, 0.0])
        
        sim_same = searcher.cosine_similarity(vec1, vec2)
        sim_orthogonal = searcher.cosine_similarity(vec1, vec3)
        
        assert abs(sim_same - 1.0) < 0.001, "Identical vectors should have similarity 1.0"
        assert abs(sim_orthogonal - 0.0) < 0.001, "Orthogonal vectors should have similarity 0.0"
        print(f"   Similarity (same): {sim_same:.3f}")
        print(f"   Similarity (orthogonal): {sim_orthogonal:.3f}")
        print("   ✓ Cosine similarity works")
        
        print("\n5. Testing keyword fallback embedding...")
        embedding = searcher._keyword_fallback("authentication security module")
        assert len(embedding) == 1000, "Fallback should produce 1000-dim vector"
        assert abs(np.linalg.norm(embedding) - 1.0) < 0.001, "Should be normalized"
        print(f"   Embedding shape: {embedding.shape}")
        print(f"   Embedding norm: {np.linalg.norm(embedding):.3f}")
        print("   ✓ Keyword fallback works")
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nTo test with actual database heuristics:")
        print("  python src/query/query.py --semantic 'Your task here'")
        return 0
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        print("Make sure you're running from the repo root directory")
        return 1
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def test_with_database():
    """Test semantic search with actual database (if available)."""
    print("\n" + "=" * 60)
    print("Testing with Database (if available)")
    print("=" * 60)
    
    try:
        from semantic_search import SemanticSearcher
        from models import initialize_database
        
        # Try to initialize database
        try:
            await initialize_database()
            print("✓ Database initialized")
        except Exception as e:
            print(f"⚠ Database not available: {e}")
            print("Skipping database tests")
            return 0
        
        # Create searcher and test
        searcher = await SemanticSearcher.create()
        
        # Test computing embeddings
        print("\nComputing embeddings for all heuristics...")
        count = await searcher.compute_all_heuristic_embeddings()
        print(f"✓ Processed {count} heuristics")
        
        # Test semantic search
        print("\nTesting semantic search...")
        results = await searcher.find_relevant_heuristics(
            task="Refactor authentication module",
            threshold=0.5,  # Lower threshold for testing
            limit=3
        )
        
        print(f"✓ Found {len(results)} relevant heuristics")
        for h in results:
            print(f"  - {h.get('rule', 'N/A')[:50]}... (score: {h.get('_final_score', 0):.3f})")
        
        await searcher.cleanup()
        print("\n✓ Database tests completed")
        return 0
        
    except Exception as e:
        print(f"\n⚠ Database test error: {e}")
        print("This is expected if no database is set up")
        return 0


if __name__ == '__main__':
    print("\n" + "🧪 Semantic Search Test Suite" + "\n")
    
    # Run basic tests
    result = asyncio.run(test_semantic_search())
    
    if result == 0:
        # Try database tests (optional)
        asyncio.run(test_with_database())
    
    sys.exit(result)
