from sqlalchemy import text


def preload_location_bundles(db_manager) -> dict:
    """
    Return:
      {
        (region_id, subproject_id): [name1, name2, ...]
      }
    """
    bundles = {}

    for region_id, cfg in db_manager.DB_MAP.items():
        engine = db_manager.get_engine(region_id)
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
            bundles.setdefault(key, []).append(r.SubProjectName)

    return bundles
