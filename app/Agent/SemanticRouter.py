import re
from typing import Dict, List, Optional

import numpy as np
import torch

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

HF_TOKEN = os.getenv("HF_TOKEN")
# =========================================================
# INTENT DEFINITIONS (GIỮ ID CŨ)
# =========================================================
INTENT_LABELS = {
    0: "direction",
    1: "media",
    2: "info",
    3: "chitchat",
    4: "count",  # nếu sau này train thêm
    5: "follow_up",  # xử lý bằng context, không embedding
}


class SemanticRouter:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "anansupercuteeeee/multilingual-traveling"

        print(
            f"🚀 Loading Intent Router (embedding-only): {model_name} on {device.upper()}"
        )
        self.model = SentenceTransformer(model_name, device=device)

        self.last_intent_id = None
        self.last_target_place = None

        # -------------------------------------------------
        # LABEL-BASED INTENT EMBEDDING (E5)
        # -------------------------------------------------
        LABELS = {
            "location": "where is, address, directions, how far, distance",
            "media": "play audio, play video, open media",
            "info": "general information, opening hours, ticket price, history",
            "chitchat": "casual conversation, greeting, small talk",
        }

        LABEL_TO_INTENT_ID = {
            "location": 0,
            "media": 1,
            "info": 2,
            "chitchat": 3,
        }

        self.intent_id_by_index = []
        label_texts = []

        for label, desc in LABELS.items():
            label_texts.append(f"passage: {desc}")
            self.intent_id_by_index.append(LABEL_TO_INTENT_ID[label])

        self.label_vectors = self.model.encode(label_texts, normalize_embeddings=True)

        print("✅ SemanticRouter ready (PURE embedding)")

    # =====================================================
    # MAIN CLASSIFIER
    # =====================================================
    def classify_intent(self, text: str, threshold: float = 0.55) -> Dict:
        if not text or not text.strip():
            return {
                "id": 3,
                "label": "chitchat",
                "score": 0.0,
                "method": "empty",
            }

        # -------------------------------------------------
        # FOLLOW-UP (rất nhẹ – optional)
        # -------------------------------------------------
        if self.last_intent_id is not None and len(text.split()) <= 4:
            return {
                "id": 5,
                "label": "follow_up",
                "score": 1.0,
                "method": "context",
                "follow_of": INTENT_LABELS[self.last_intent_id],
            }

        # -------------------------------------------------
        # EMBEDDING INTENT CLASSIFICATION
        # -------------------------------------------------
        q_vec = self.model.encode(f"query: {text}", normalize_embeddings=True)

        sims = q_vec @ self.label_vectors.T
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        best_intent = self.intent_id_by_index[best_idx]

        if best_score < threshold:
            self.last_intent_id = 3
            return {
                "id": 3,
                "label": "fallback",
                "score": best_score,
                "method": "fallback",
            }

        self.last_intent_id = best_intent
        return {
            "id": best_intent,
            "label": INTENT_LABELS[best_intent],
            "score": best_score,
            "method": "embedding",
        }

    # =====================================================
    # PLACE MATCH (GIỮ NGUYÊN)
    # =====================================================
    def find_target_place(
        self, user_query: str, candidates: List[Dict[str, str]]
    ) -> Optional[Dict]:
        if not candidates:
            return None

        texts = [f"passage: {c['name']}" for c in candidates]
        q_vec = self.model.encode(f"query: {user_query}", normalize_embeddings=True)
        c_vecs = self.model.encode(texts, normalize_embeddings=True)

        sims = cosine_similarity([q_vec], c_vecs)[0]
        idx = int(np.argmax(sims))

        if sims[idx] > 0.78:
            return candidates[idx]
        return None
