#!/usr/bin/env python3
"""
RAG-Enhanced Query System for Emergent Learning Framework

Premium retrieval pipeline:
1. SQL pre-filter by domain/tags/recency
2. Embed query with bge-large via Ollama
3. Vector similarity search
4. Cross-encoder re-ranking
5. Return top-k most relevant results

Requires: Ollama running with bge-large model
Optional: sentence-transformers for re-ranking
"""

import sqlite3
import os
import sys
import argparse
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add services path for VRAM manager
sys.path.insert(0, str(Path.home() / ".claude" / "services"))

try:
    from vram_manager import VRAMClient, VRAMManager
    VRAM_AVAILABLE = True
except ImportError:
    VRAM_AVAILABLE = False
    VRAMClient = None

# Ollama client
try:
    import urllib.request
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Re-ranker (optional, for maximum accuracy)
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    CrossEncoder = None


class OllamaEmbedder:
    """Embed text using Ollama's embedding models."""

    def __init__(self, model: str = "nomic-embed-text", base_url: str = None):
        self.model = model
        self.base_url = base_url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

    def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text."""
        try:
            data = json.dumps({"model": self.model, "prompt": text}).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/embeddings",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result.get("embedding")
        except Exception as e:
            print(f"Embedding error: {e}", file=sys.stderr)
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts."""
        return [self.embed(t) for t in texts]


class RAGQuerySystem:
    """
    RAG-enhanced query system with semantic search and re-ranking.

    Flow:
    1. ensure_services() - auto-launch Ollama if needed
    2. SQL pre-filter - narrow candidates by domain/tags
    3. embed_query() - get query vector
    4. vector_search() - find similar items
    5. rerank() - cross-encoder scoring
    6. return top-k
    """

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            self.base_path = Path.home() / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"
        self.vectors_path = self.memory_path / "vectors.db"

        # Initialize VRAM client
        self.vram_client = VRAMClient() if VRAM_AVAILABLE else None

        # Initialize embedder (lazy)
        self._embedder = None

        # Initialize re-ranker (lazy)
        self._reranker = None

        # Ensure vector DB exists
        self._init_vector_db()

    @property
    def embedder(self) -> OllamaEmbedder:
        if self._embedder is None:
            self._embedder = OllamaEmbedder()
        return self._embedder

    @property
    def reranker(self):
        if self._reranker is None and RERANKER_AVAILABLE:
            try:
                self._reranker = CrossEncoder('BAAI/bge-reranker-v2-m3', device='cuda')
            except Exception:
                try:
                    self._reranker = CrossEncoder('BAAI/bge-reranker-v2-m3', device='cpu')
                except Exception as e:
                    print(f"Re-ranker init failed: {e}", file=sys.stderr)
        return self._reranker

    def _init_vector_db(self):
        """Initialize vector storage database."""
        conn = sqlite3.connect(str(self.vectors_path))
        cursor = conn.cursor()

        # Store embeddings for heuristics and learnings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_type, source_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_source
            ON embeddings(source_type, source_id)
        """)

        conn.commit()
        conn.close()

    def ensure_services(self, need_ollama: bool = True) -> bool:
        """Ensure required services are running."""
        if not self.vram_client:
            # No VRAM manager - check Ollama directly
            return self._check_ollama()

        result = self.vram_client.ensure_services(ollama=need_ollama, comfyui=False)
        return result.get("ollama") != "failed"

    def _check_ollama(self) -> bool:
        """Direct check if Ollama is available."""
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/tags",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _sql_prefilter(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Pre-filter candidates from SQL before semantic search.

        Returns (heuristics, learnings) tuples.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        heuristics = []
        learnings = []

        # Query heuristics
        h_conditions = ["1=1"]
        h_params = []

        if domain:
            h_conditions.append("domain = ?")
            h_params.append(domain)
        if min_confidence > 0:
            h_conditions.append("confidence >= ?")
            h_params.append(min_confidence)

        h_query = f"""
            SELECT id, domain, rule, explanation, confidence, is_golden,
                   'heuristic' as source_type
            FROM heuristics
            WHERE {' AND '.join(h_conditions)}
            ORDER BY is_golden DESC, confidence DESC
            LIMIT ?
        """
        h_params.append(limit)

        cursor.execute(h_query, h_params)
        heuristics = [dict(row) for row in cursor.fetchall()]

        # Query learnings
        l_conditions = ["1=1"]
        l_params = []

        if domain:
            l_conditions.append("domain = ?")
            l_params.append(domain)
        if tags:
            tag_conds = " OR ".join(["tags LIKE ?" for _ in tags])
            l_conditions.append(f"({tag_conds})")
            l_params.extend([f"%{t}%" for t in tags])

        l_query = f"""
            SELECT id, type, title, summary, tags, domain,
                   'learning' as source_type
            FROM learnings
            WHERE {' AND '.join(l_conditions)}
            ORDER BY created_at DESC
            LIMIT ?
        """
        l_params.append(limit)

        cursor.execute(l_query, l_params)
        learnings = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return heuristics, learnings

    def _get_or_create_embedding(
        self,
        source_type: str,
        source_id: int,
        content: str
    ) -> Optional[List[float]]:
        """Get cached embedding or create new one."""
        conn = sqlite3.connect(str(self.vectors_path))
        cursor = conn.cursor()

        # Check cache
        cursor.execute("""
            SELECT embedding FROM embeddings
            WHERE source_type = ? AND source_id = ?
        """, (source_type, source_id))

        row = cursor.fetchone()
        if row and row[0]:
            conn.close()
            return json.loads(row[0])

        # Create new embedding
        embedding = self.embedder.embed(content)
        if embedding:
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings (source_type, source_id, content, embedding)
                VALUES (?, ?, ?, ?)
            """, (source_type, source_id, content, json.dumps(embedding)))
            conn.commit()

        conn.close()
        return embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _content_for_item(self, item: Dict) -> str:
        """Extract searchable content from an item."""
        if item.get('source_type') == 'heuristic':
            return f"{item.get('rule', '')} {item.get('explanation', '')}"
        else:
            return f"{item.get('title', '')} {item.get('summary', '')}"

    def semantic_search(
        self,
        query: str,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        top_k: int = 10,
        use_reranker: bool = True
    ) -> List[Dict]:
        """
        Full RAG search pipeline.

        1. SQL pre-filter
        2. Embed query
        3. Vector similarity
        4. Re-rank (if available)
        5. Return top-k
        """
        # Ensure Ollama is running
        if not self.ensure_services():
            print("Warning: Ollama not available, falling back to SQL-only", file=sys.stderr)
            heuristics, learnings = self._sql_prefilter(domain, tags, min_confidence, top_k)
            return heuristics + learnings

        # VRAM coordination for RAG operation
        if self.vram_client:
            with self.vram_client.rag_operation(VRAMManager.OP_RAG_EMBED) as acquired:
                if not acquired:
                    print("Warning: Could not acquire VRAM, proceeding anyway", file=sys.stderr)
                return self._do_semantic_search(query, domain, tags, min_confidence, top_k, use_reranker)
        else:
            return self._do_semantic_search(query, domain, tags, min_confidence, top_k, use_reranker)

    def _do_semantic_search(
        self,
        query: str,
        domain: Optional[str],
        tags: Optional[List[str]],
        min_confidence: float,
        top_k: int,
        use_reranker: bool
    ) -> List[Dict]:
        """Internal semantic search implementation."""

        # Step 1: SQL pre-filter
        heuristics, learnings = self._sql_prefilter(domain, tags, min_confidence, limit=100)
        candidates = heuristics + learnings

        if not candidates:
            return []

        # Step 2: Embed query
        query_embedding = self.embedder.embed(query)
        if not query_embedding:
            print("Warning: Query embedding failed, returning SQL results", file=sys.stderr)
            return candidates[:top_k]

        # Step 3: Score candidates by similarity
        scored = []
        for item in candidates:
            content = self._content_for_item(item)
            item_embedding = self._get_or_create_embedding(
                item['source_type'],
                item['id'],
                content
            )

            if item_embedding:
                similarity = self._cosine_similarity(query_embedding, item_embedding)
                item['similarity'] = similarity
                scored.append(item)
            else:
                # Include without score
                item['similarity'] = 0.0
                scored.append(item)

        # Sort by similarity
        scored.sort(key=lambda x: x['similarity'], reverse=True)

        # Step 4: Re-rank top candidates (if available and requested)
        if use_reranker and self.reranker and len(scored) > 0:
            # Re-rank top 50
            to_rerank = scored[:min(50, len(scored))]

            pairs = [(query, self._content_for_item(item)) for item in to_rerank]
            rerank_scores = self.reranker.predict(pairs)

            for i, item in enumerate(to_rerank):
                item['rerank_score'] = float(rerank_scores[i])

            to_rerank.sort(key=lambda x: x['rerank_score'], reverse=True)
            scored = to_rerank + scored[50:]

        return scored[:top_k]

    def index_all(self, force: bool = False):
        """
        Pre-compute embeddings for all heuristics and learnings.

        Args:
            force: If True, re-embed even if cached
        """
        if not self.ensure_services():
            print("Ollama not available for indexing", file=sys.stderr)
            return

        # Get all heuristics
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT id, rule, explanation FROM heuristics")
        heuristics = cursor.fetchall()

        cursor.execute("SELECT id, title, summary FROM learnings")
        learnings = cursor.fetchall()

        conn.close()

        print(f"Indexing {len(heuristics)} heuristics and {len(learnings)} learnings...")

        # Index heuristics
        for h in heuristics:
            content = f"{h['rule']} {h['explanation'] or ''}"
            if force:
                # Delete existing
                vconn = sqlite3.connect(str(self.vectors_path))
                vconn.execute("DELETE FROM embeddings WHERE source_type='heuristic' AND source_id=?", (h['id'],))
                vconn.commit()
                vconn.close()

            self._get_or_create_embedding('heuristic', h['id'], content)
            print(".", end="", flush=True)

        # Index learnings
        for l in learnings:
            content = f"{l['title']} {l['summary'] or ''}"
            if force:
                vconn = sqlite3.connect(str(self.vectors_path))
                vconn.execute("DELETE FROM embeddings WHERE source_type='learning' AND source_id=?", (l['id'],))
                vconn.commit()
                vconn.close()

            self._get_or_create_embedding('learning', l['id'], content)
            print(".", end="", flush=True)

        print("\nDone!")


def main():
    """CLI for RAG query system."""
    parser = argparse.ArgumentParser(
        description="RAG-Enhanced Query System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--domain", type=str, help="Filter by domain")
    parser.add_argument("--tags", type=str, help="Filter by tags (comma-separated)")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--no-rerank", action="store_true", help="Skip re-ranking step")
    parser.add_argument("--index", action="store_true", help="Index all content")
    parser.add_argument("--force-index", action="store_true", help="Force re-index all")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    rag = RAGQuerySystem()

    if args.index or args.force_index:
        rag.index_all(force=args.force_index)
        return

    if not args.query:
        parser.print_help()
        return

    tags = args.tags.split(",") if args.tags else None
    results = rag.semantic_search(
        args.query,
        domain=args.domain,
        tags=tags,
        top_k=args.top_k,
        use_reranker=not args.no_rerank
    )

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"Found {len(results)} results for: {args.query}\n")
        for i, r in enumerate(results, 1):
            src = r.get('source_type', 'unknown')
            score = r.get('rerank_score', r.get('similarity', 0))
            if src == 'heuristic':
                print(f"{i}. [H] {r['rule'][:60]}... (score: {score:.3f})")
            else:
                print(f"{i}. [L] {r['title'][:60]}... (score: {score:.3f})")


if __name__ == "__main__":
    main()
