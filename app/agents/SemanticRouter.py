"""
Semantic Router for intent classification.
Simple binary classification: RAG query vs Chitchat.
"""
import logging
from typing import Dict

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SemanticRouter:
    """
    Simple binary classifier: RAG vs Chitchat.
    Uses embedding similarity with predefined labels.
    """

    def __init__(self, embedder: SentenceTransformer):
        self.model = embedder

        # Binary classification: RAG or Chitchat
        labels = {
            "rag": "question about place, location, information, directions, media, history, opening hours",
            "chitchat": "casual conversation, greeting, thanks, bye, hello, small talk",
        }

        self.label_names = list(labels.keys())
        label_texts = [f"passage: {desc}" for desc in labels.values()]
        self.label_vectors = self.model.encode(label_texts, normalize_embeddings=True)

        logger.info("SemanticRouter ready (RAG/Chitchat)")

    def classify(self, text: str, threshold: float = 0.5) -> Dict:
        """
        Classify query as RAG or Chitchat.
        
        Returns:
            {"is_chitchat": bool, "score": float}
        """
        if not text or not text.strip():
            return {"is_chitchat": True, "score": 0.0}

        q_vec = self.model.encode(f"query: {text}", normalize_embeddings=True)
        sims = q_vec @ self.label_vectors.T

        # Index 0 = RAG, Index 1 = Chitchat
        rag_score = float(sims[0])
        chitchat_score = float(sims[1])

        is_chitchat = chitchat_score > rag_score

        logger.debug(f"RAG={rag_score:.3f} Chitchat={chitchat_score:.3f} → {'chitchat' if is_chitchat else 'rag'}")

        return {
            "is_chitchat": is_chitchat,
            "score": max(rag_score, chitchat_score),
        }
