"""
Semantic search utilities for embedding-based heuristic retrieval (Option B).

Uses lightweight local embeddings (sentence-transformers or similar) to enable
semantic matching between task descriptions and heuristics.

Usage:
    from semantic_search import SemanticSearcher
    
    searcher = await SemanticSearcher.create()
    results = await searcher.find_relevant_heuristics(
        task="Refactor authentication module",
        threshold=0.75,
        limit=5
    )
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Try to import embedding libraries
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import with fallbacks
try:
    from query.models import Heuristic, get_manager
    from query.exceptions import QuerySystemError, DatabaseError
except ImportError:
    from models import Heuristic, get_manager
    from exceptions import QuerySystemError, DatabaseError


class SemanticSearcher:
    """
    Semantic search for heuristics using embeddings.
    
    Supports multiple embedding backends:
    - sentence-transformers (local, fast, no API calls)
    - OpenAI embeddings (if API key available)
    - Simple keyword fallback (if no embeddings available)
    
    Embeddings are cached to avoid recomputation.
    """
    
    # Default model - small, fast, good for semantic similarity
    DEFAULT_MODEL = 'all-MiniLM-L6-v2'
    
    # Embedding cache directory
    CACHE_DIR = '.embedding_cache'
    
    def __init__(self, base_path: Optional[Path] = None, model_name: Optional[str] = None):
        """
        Initialize semantic searcher (use create() for async init).
        
        Args:
            base_path: Base path for cache storage
            model_name: Embedding model name (defaults to DEFAULT_MODEL)
        """
        self.base_path = base_path or Path.home() / '.claude' / 'emergent-learning'
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
        self._use_openai = False
        
        # Cache setup
        self.cache_path = self.base_path / self.CACHE_DIR
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, np.ndarray] = {}
    
    @classmethod
    async def create(
        cls,
        base_path: Optional[Path] = None,
        model_name: Optional[str] = None,
        prefer_openai: bool = False
    ) -> 'SemanticSearcher':
        """
        Async factory to create and initialize SemanticSearcher.
        
        Args:
            base_path: Base path for cache storage
            model_name: Embedding model name
            prefer_openai: Whether to prefer OpenAI over local models
            
        Returns:
            Initialized SemanticSearcher instance
        """
        searcher = cls(base_path, model_name)
        await searcher._initialize_model(prefer_openai)
        await searcher._load_heuristic_embeddings()
        return searcher
    
    async def _initialize_model(self, prefer_openai: bool = False):
        """Initialize the embedding model."""
        # Check for OpenAI API key if preferred
        if prefer_openai and OPENAI_AVAILABLE and os.environ.get('OPENAI_API_KEY'):
            self._use_openai = True
            return
        
        # Try sentence-transformers
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                return
            except Exception as e:
                print(f"Warning: Failed to load sentence-transformers model: {e}")
        
        # Fallback: use OpenAI if available
        if OPENAI_AVAILABLE and os.environ.get('OPENAI_API_KEY'):
            self._use_openai = True
            return
        
        # Final fallback: no embeddings, will use keyword matching
        print("Warning: No embedding backend available. Using keyword fallback.")
    
    async def _load_heuristic_embeddings(self):
        """Load cached heuristic embeddings from disk."""
        cache_file = self.cache_path / 'heuristic_embeddings.json'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for key, vec in data.items():
                        self._cache[key] = np.array(vec)
            except Exception as e:
                print(f"Warning: Failed to load embedding cache: {e}")
    
    async def _save_heuristic_embeddings(self):
        """Save heuristic embeddings to disk cache."""
        cache_file = self.cache_path / 'heuristic_embeddings.json'
        try:
            data = {k: v.tolist() for k, v in self._cache.items()}
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: Failed to save embedding cache: {e}")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Generate embedding
        if self._use_openai:
            embedding = await self._embed_openai(text)
        elif self.model is not None:
            embedding = self.model.encode(text, convert_to_numpy=True)
        else:
            # Fallback: simple keyword vector
            embedding = self._keyword_fallback(text)
        
        # Cache and return
        self._cache[cache_key] = embedding
        return embedding
    
    async def _embed_openai(self, text: str) -> np.ndarray:
        """Generate embedding using OpenAI API."""
        import openai
        client = openai.AsyncOpenAI()
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(response.data[0].embedding)
    
    def _keyword_fallback(self, text: str) -> np.ndarray:
        """
        Simple keyword-based fallback when no embeddings available.
        Creates a sparse vector based on word frequencies.
        """
        # Simple bag-of-words representation
        words = text.lower().split()
        # Use a fixed vocabulary hash for consistency
        vector = np.zeros(1000)
        for word in words:
            idx = hash(word) % 1000
            vector[idx] += 1
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    async def find_relevant_heuristics(
        self,
        task: str,
        threshold: float = 0.75,
        limit: int = 5,
        domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find heuristics semantically relevant to the task.
        
        Args:
            task: Task description to match against
            threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum number of results
            domain: Optional domain to filter by first
            
        Returns:
            List of heuristics with similarity scores, sorted by relevance
        """
        # Get task embedding
        task_embedding = await self.embed(task)
        
        # Query heuristics from database
        m = get_manager()
        heuristics = []
        
        async with m:
            async with m.connection():
                query = Heuristic.select()
                
                # Filter by domain if specified
                if domain:
                    query = query.where(Heuristic.domain == domain)
                
                # Get all heuristics (or domain-filtered)
                async for h in query:
                    heuristics.append(h.__data__.copy())
        
        # Calculate similarity scores
        scored_heuristics = []
        for h in heuristics:
            # Create rich text for embedding
            heuristic_text = f"{h['rule']}"
            if h.get('explanation'):
                heuristic_text += f" {h['explanation']}"
            if h.get('domain'):
                heuristic_text += f" Domain: {h['domain']}"
            
            # Get embedding
            h_embedding = await self.embed(heuristic_text)
            
            # Calculate similarity
            similarity = self.cosine_similarity(task_embedding, h_embedding)
            
            # Boost score based on confidence and validation
            confidence_boost = h.get('confidence', 0.5) * 0.1
            validation_boost = min(h.get('times_validated', 0) * 0.01, 0.1)
            final_score = similarity + confidence_boost + validation_boost
            
            if final_score >= threshold:
                h['_similarity'] = similarity
                h['_final_score'] = final_score
                scored_heuristics.append(h)
        
        # Sort by final score and limit
        scored_heuristics.sort(key=lambda x: x['_final_score'], reverse=True)
        return scored_heuristics[:limit]
    
    async def compute_all_heuristic_embeddings(self) -> int:
        """
        Pre-compute and cache embeddings for all heuristics.
        Call this after adding new heuristics to update the cache.
        
        Returns:
            Number of heuristics processed
        """
        m = get_manager()
        count = 0
        
        async with m:
            async with m.connection():
                async for h in Heuristic.select():
                    # Create rich text for embedding
                    heuristic_text = f"{h.rule}"
                    if h.explanation:
                        heuristic_text += f" {h.explanation}"
                    if h.domain:
                        heuristic_text += f" Domain: {h.domain}"
                    
                    # Generate and cache embedding
                    await self.embed(heuristic_text)
                    count += 1
        
        # Save cache to disk
        await self._save_heuristic_embeddings()
        return count
    
    async def cleanup(self):
        """Clean up resources and save cache."""
        await self._save_heuristic_embeddings()


# Simple keyword extractor for fallback mode
def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text for simple matching."""
    # Simple keyword extraction
    words = text.lower().split()
    # Filter common stop words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                  'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                  'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                  'through', 'during', 'before', 'after', 'above', 'below',
                  'between', 'under', 'and', 'but', 'or', 'yet', 'so'}
    return [w for w in words if w not in stop_words and len(w) > 2]
