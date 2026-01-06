"""
Query Store for Query-Oriented RAG.
Stores query templates and performs semantic matching.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class QueryStore:
    """
    In-memory store for query templates with semantic matching.
    
    Each template has:
    - key: Text for embedding (what user might ask)
    - intent: Intent label
    - sql_template: SQL with :placeholders
    - required_vars: Variables needed to execute
    """

    def __init__(self, embedder: SentenceTransformer, templates_path: str = None):
        """
        Initialize QueryStore.
        
        Args:
            embedder: Sentence transformer model for embeddings
            templates_path: Path to query_templates.json
        """
        self.embedder = embedder
        self.templates: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        
        if templates_path is None:
            templates_path = Path(__file__).parent / "query_templates.json"
        
        self._load_templates(templates_path)
        logger.info(f"QueryStore initialized with {len(self.templates)} templates")

    def _load_templates(self, path: str) -> None:
        """Load templates from JSON file and compute embeddings."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.templates = json.load(f)
            
            # Embed all keys
            keys = [t["key"] for t in self.templates]
            self.embeddings = self.embedder.encode(
                [f"passage: {k}" for k in keys],
                normalize_embeddings=True,
            )
            
            logger.info(f"Loaded {len(self.templates)} query templates")
        except FileNotFoundError:
            logger.warning(f"Templates file not found: {path}")
            self.templates = []
            self.embeddings = None

    def match(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Find best matching query templates.
        
        Args:
            query: User query (synthesized from Reflection)
            top_k: Number of top matches to return
            
        Returns:
            List of matches with template and score
        """
        if not self.templates or self.embeddings is None:
            logger.warning("No templates loaded")
            return []
        
        # Embed query
        q_emb = self.embedder.encode(
            f"query: {query}",
            normalize_embeddings=True,
        )
        
        # Compute similarities
        scores = self.embeddings @ q_emb
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "template": self.templates[idx],
                "score": float(scores[idx]),
            })
        
        logger.debug(f"Top match: {results[0]['template']['intent']} (score: {results[0]['score']:.3f})")
        return results

    def get_template_by_intent(self, intent: str) -> Optional[Dict]:
        """Get template by intent name."""
        for t in self.templates:
            if t["intent"] == intent:
                return t
        return None
