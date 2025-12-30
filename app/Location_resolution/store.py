import numpy as np
from sqlalchemy import text
from Location_resolution.ner import NERService


class LocationStore:
    def __init__(self, ner_service: NERService, embedder, db_manager):
        self.ner_service = ner_service
        self.embedder = embedder
        self.db_manager = db_manager
        self._store = {}
        self.cache = {}

        print("📍 LocationStore initialized")

    def extract_ner(self, text: str):
        return self.ner_service.extract_locations(text)

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

    def match(self, region_id: int, project_id: int, ner_location: str):
        print(
            f"[LocationStore.match] region={region_id}, "
            f"project={project_id}, ner='{ner_location}'"
        )

        key = (int(region_id), int(project_id))
        data = self._store.get(key)

        if not data:
            print(f"[LocationStore.match] ❌ No cache for key={key}")
            return None

        if not ner_location:
            return None

        q_emb = self.embedder.encode(
            f"query: {ner_location}",
            normalize_embeddings=True,
        )

        scores = data["embeddings"] @ q_emb
        idx = int(scores.argmax())
        score = float(scores[idx])

        print(f"[LocationStore.match] best='{data['names'][idx]}' score={score:.4f}")

        if score < 0.6:
            return None

        return {
            "subproject_name": data["names"][idx],
            "score": score,
        }
