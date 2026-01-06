"""
Reranker module for Query-Oriented RAG.
Uses cross-encoder for more accurate ranking.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Reranker:
    """
    Reranker using cross-encoder model for accurate scoring.
    
    Falls back to original scores if model not available.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize Reranker.
        
        Args:
            model_name: HuggingFace cross-encoder model name
        """
        self.model = None
        self.model_name = model_name
        
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker model: {model_name}")
            self.model = CrossEncoder(model_name)
            logger.info("Reranker ready")
        except ImportError:
            logger.warning("CrossEncoder not available, using score-based ranking")
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}")

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 1,
    ) -> List[Dict]:
        """
        Rerank candidates based on query.
        
        Args:
            query: User query
            candidates: List of candidates with 'template' and 'score'
            top_k: Number of results to return
            
        Returns:
            Reranked list of candidates
        """
        if not candidates:
            return []
        
        if self.model is None:
            # Fallback: just sort by original score
            return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]
        
        # Prepare pairs for cross-encoder
        pairs = []
        for c in candidates:
            # Use the key field for reranking
            key_text = c["template"]["key"]
            pairs.append((query, key_text))
        
        # Get cross-encoder scores
        try:
            scores = self.model.predict(pairs)
            
            # Attach scores and sort
            for i, c in enumerate(candidates):
                c["rerank_score"] = float(scores[i])
            
            reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
            
            logger.debug(f"Reranked top: {reranked[0]['template']['intent']} (score: {reranked[0]['rerank_score']:.3f})")
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]

    def is_available(self) -> bool:
        """Check if reranker model is loaded."""
        return self.model is not None
