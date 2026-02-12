"""
TravelVectorStore: Qdrant-based vector search for travel knowledge.
Indexed from SubProjects table across all regions.
"""
import logging
import os
from typing import Dict, List, Optional

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TravelVectorStore:
    """Vector store for travel knowledge with region/project filtering."""

    COLLECTION_NAME = "travel_knowledge"
    VECTOR_SIZE = 384  # multilingual-e5-small

    def __init__(
        self,
        embedder: SentenceTransformer,
        host: str = None,
        port: int = None,
    ):
        self.embedder = embedder
        host = host or os.getenv("QDRANT_HOST", "localhost")
        port = port or int(os.getenv("QDRANT_PORT", "6333"))

        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()
        logger.info(f"TravelVectorStore connected to {host}:{port}")

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def _ensure_collection(self):
        """Create collection if not exists."""
        collections = [c.name for c in self.client.get_collections().collections]

        if self.COLLECTION_NAME not in collections:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.COLLECTION_NAME}")

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def index_from_database(self, db_manager) -> int:
        """
        Sync ALL regions from SQL Server → Qdrant.

        Returns:
            Number of documents indexed.
        """
        from sqlalchemy import text as sql_text

        points = []

        for region_id, cfg in db_manager.DB_MAP.items():
            engine = db_manager.get_engine(region_id)
            prefix = cfg["prefix"]

            sql = f"""
            SELECT SubProjectID, SubProjectName, Introduction, ProjectID
            FROM {prefix}.SubProjects
            WHERE Introduction IS NOT NULL
            """

            with engine.connect() as conn:
                rows = conn.execute(sql_text(sql)).fetchall()

            for row in rows:
                text_content = f"{row.SubProjectName}. {row.Introduction}"

                embedding = self.embedder.encode(
                    f"passage: {text_content}",
                    normalize_embeddings=True,
                )

                point_id = hash(f"{region_id}_{row.SubProjectID}") & 0x7FFFFFFF

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload={
                            "region_id": region_id,
                            "project_id": row.ProjectID,
                            "subproject_id": row.SubProjectID,
                            "name": row.SubProjectName,
                            "text": text_content[:1000],
                        },
                    )
                )

            logger.info(f"Region {region_id}: {len(rows)} docs prepared")

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=batch,
            )

        logger.info(f"Indexed {len(points)} documents to Qdrant")
        return len(points)

    async def index_region(self, db_manager, region_id: int) -> int:
        """Sync a single region to Qdrant."""
        from sqlalchemy import text as sql_text

        cfg = db_manager.DB_MAP.get(region_id)
        if not cfg:
            raise ValueError(f"Invalid region_id: {region_id}")

        engine = db_manager.get_engine(region_id)
        prefix = cfg["prefix"]

        sql = f"""
        SELECT SubProjectID, SubProjectName, Introduction, ProjectID
        FROM {prefix}.SubProjects
        WHERE Introduction IS NOT NULL
        """

        with engine.connect() as conn:
            rows = conn.execute(sql_text(sql)).fetchall()

        points = []
        for row in rows:
            text_content = f"{row.SubProjectName}. {row.Introduction}"

            embedding = self.embedder.encode(
                f"passage: {text_content}",
                normalize_embeddings=True,
            )

            point_id = hash(f"{region_id}_{row.SubProjectID}") & 0x7FFFFFFF

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        "region_id": region_id,
                        "project_id": row.ProjectID,
                        "subproject_id": row.SubProjectID,
                        "name": row.SubProjectName,
                        "text": text_content[:1000],
                    },
                )
            )

        if points:
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=batch,
                )

        logger.info(f"Region {region_id}: indexed {len(points)} documents")
        return len(points)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        region_id: Optional[int] = None,
        project_id: Optional[int] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Semantic search with optional region/project filtering.

        Args:
            query: Search text
            region_id: Filter by region (0-3)
            project_id: Filter by project
            top_k: Max results

        Returns:
            List of {name, text, score, region_id, project_id}
        """
        q_embedding = self.embedder.encode(
            f"query: {query}",
            normalize_embeddings=True,
        )

        # Build filter
        must_conditions = []
        if region_id is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="region_id",
                    match=models.MatchValue(value=region_id),
                )
            )
        if project_id is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchValue(value=project_id),
                )
            )

        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=q_embedding.tolist(),
            query_filter=query_filter,
            limit=top_k,
        )

        return [
            {
                "name": r.payload["name"],
                "text": r.payload["text"],
                "score": r.score,
                "region_id": r.payload["region_id"],
                "project_id": r.payload["project_id"],
            }
            for r in results
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.COLLECTION_NAME)
        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value if hasattr(info.status, "value") else str(info.status),
        }
