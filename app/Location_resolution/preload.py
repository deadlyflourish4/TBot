from sqlalchemy import text


def preload(self):
    """
    Cache structure:
    {
      (region_id, project_id): {
          "names": [...],
          "embeddings": np.ndarray
      }
    }
    """
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

    # embed once
    for key, data in self._store.items():
        data["embeddings"] = self.embedder.encode(
            [f"passage: {n}" for n in data["names"]],
            normalize_embeddings=True,
        )

    print("📍 LocationStore preloaded into RAM")
