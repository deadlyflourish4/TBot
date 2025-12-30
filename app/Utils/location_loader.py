from sqlalchemy import text


def load_location_bundle(db_manager, region_id: int, subproject_id: int):
    """
    Load a small set of candidate names for a known (region_id, subproject_id).
    Keep it SMALL (1~20 strings) for speed.
    """
    cfg = db_manager.DB_MAP[region_id]
    engine = db_manager.get_engine(region_id)
    prefix = cfg["prefix"]

    # Bạn có thể thêm POI hoặc bảng khác nếu có
    sql = f"""
    SELECT TOP 1
        SubProjectName,
        POI
    FROM {prefix}.SubProjects
    WHERE SubProjectID = :sid
    """

    with engine.connect() as conn:
        row = conn.execute(text(sql), {"sid": subproject_id}).fetchone()

    if not row:
        return []

    names = []
    if row.SubProjectName:
        names.append(row.SubProjectName)
    if hasattr(row, "POI") and row.POI:
        names.append(row.POI)

    # remove dup + strip
    dedup = []
    seen = set()
    for n in names:
        n2 = n.strip()
        if n2 and n2.lower() not in seen:
            dedup.append(n2)
            seen.add(n2.lower())

    return dedup
