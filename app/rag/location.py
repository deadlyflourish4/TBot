"""
Location resolution module for RAG pipeline.
Contains NER service and location matching.
"""
import logging
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import text
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)


class NERService:
    """Named Entity Recognition service for location extraction."""

    def __init__(self, device: str = "cuda"):
        self.model_name = "Davlan/xlm-roberta-base-ner-hrl"
        logger.info(f"Loading NER model: {self.model_name}")

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForTokenClassification.from_pretrained(self.model_name)

        self.pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=device,
            batch_size=1,  # Single request, suppress warning
        )

        logger.info("NERService ready")

    def extract_locations(self, text: str) -> List[str]:
        """Extract location and organization entities from text."""
        results = self.pipeline(text)
        locs = []

        for ent in results:
            if ent.get("entity_group") in ("LOC", "ORG"):
                locs.append(ent["word"].replace("_", " ").strip())

        return locs


class LocationStore:
    """In-memory store for location embeddings with semantic matching."""

    def __init__(self, ner_service: NERService, embedder, db_manager):
        self.ner_service = ner_service
        self.embedder = embedder
        self.db_manager = db_manager
        self._store: Dict = {}

        logger.info("LocationStore initialized")

    def extract_ner(self, text: str) -> List[str]:
        """Extract location entities from text using NER."""
        return self.ner_service.extract_locations(text)

    def preload(self) -> None:
        """Preload all locations from database into memory."""
        for region_id, cfg in self.db_manager.DB_MAP.items():
            engine = self.db_manager.get_engine(region_id)
            prefix = cfg["prefix"]

            sql = f"""
            SELECT ProjectID, SubProjectName
            FROM {prefix}.SubProjects
            WHERE SubProjectName IS NOT NULL
            """

            with engine.connect() as conn:
                rows = conn.execute(text(sql)).fetchall()

            for r in rows:
                key = (int(region_id), int(r.ProjectID))
                self._store.setdefault(key, {"names": [], "embeddings": None})
                self._store[key]["names"].append(r.SubProjectName)

        # Embed all names
        for key, data in self._store.items():
            data["embeddings"] = self.embedder.encode(
                [f"passage: {n}" for n in data["names"]],
                normalize_embeddings=True,
            )

        logger.info(f"LocationStore preloaded: {len(self._store)} region/project pairs")

    def match(
        self, region_id: int, project_id: int, ner_location: str
    ) -> Optional[Dict]:
        """Match NER-extracted location to database entries."""
        key = (int(region_id), int(project_id))
        data = self._store.get(key)

        if not data or not ner_location:
            return None

        q_emb = self.embedder.encode(
            f"query: {ner_location}",
            normalize_embeddings=True,
        )

        scores = data["embeddings"] @ q_emb
        idx = int(scores.argmax())
        score = float(scores[idx])

        if score < 0.6:
            return None

        return {"name": data["names"][idx], "score": score}
