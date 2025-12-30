import numpy as np
from sqlalchemy import text


class LocationStore:
    def __init__(self, embedder, db_manager):
        self.embedder = embedder
        self.db_manager = db_manager

        # (region_id, subproject_id) -> {names, embeddings}
        self._store = {}

    def preload(self):
        """
        Load ALL locations + embeddings into RAM once.
        """
        for region_id, cfg in self.db_manager.DB_MAP.items():
            engine = self.db_manager.get_engine(region_id)
            prefix = cfg["prefix"]

            sql = f"""
            SELECT SubProjectID, SubProjectName
            FROM {prefix}.SubProjects
            WHERE SubProjectName IS NOT NULL
            """

            with engine.connect() as conn:
                rows = conn.execute(text(sql)).fetchall()

            for r in rows:
                key = (region_id, r.SubProjectID)
                self._store.setdefault(key, []).append(r.SubProjectName)

        # embed once
        for key, names in self._store.items():
            embs = self.embedder.encode(
                [f"passage: {n}" for n in names],
                normalize_embeddings=True,
            )
            self._store[key] = {
                "names": names,
                "embeddings": embs,
            }

    def match(self, region_id: int, subproject_id: int, ner_location: str):
        key = (region_id, subproject_id)
        data = self._store.get(key)

        if not data or not ner_location:
            return None

        q_emb = self.embedder.encode(
            f"query: {ner_location}",
            normalize_embeddings=True,
        )

        scores = np.dot(data["embeddings"], q_emb)
        idx = int(scores.argmax())
        score = float(scores[idx])

        if score < 0.6:
            return None

        return {
            "name": data["names"][idx],
            "score": score,
        }
