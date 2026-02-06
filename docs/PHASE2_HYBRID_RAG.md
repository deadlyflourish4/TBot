# Phase 2: Hybrid RAG với Qdrant

## Mục tiêu

Bổ sung **vector search** để xử lý các query mơ hồ mà SQL không match được.

---

## Bước 1: Qdrant Setup (Day 1-2)

### Verify Qdrant Container

```bash
# Check container running
docker-compose ps | grep qdrant

# Test connection
curl http://localhost:6333/collections
```

### Tạo file `app/rag/vector_store.py`

```python
"""
TravelVectorStore: Qdrant-based vector search.
Indexed from SubProjects table.
"""
import logging
from typing import Dict, List, Optional

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TravelVectorStore:
    """Vector store for travel knowledge."""
    
    COLLECTION_NAME = "travel_knowledge"
    VECTOR_SIZE = 384  # E5-small
    
    def __init__(
        self,
        embedder: SentenceTransformer,
        host: str = "localhost",
        port: int = 6333
    ):
        self.embedder = embedder
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()
        logger.info(f"TravelVectorStore connected to {host}:{port}")
    
    def _ensure_collection(self):
        """Create collection if not exists."""
        collections = [c.name for c in self.client.get_collections().collections]
        
        if self.COLLECTION_NAME not in collections:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.COLLECTION_NAME}")
    
    async def index_from_database(self, db_manager) -> int:
        """
        Sync all SubProjects to vector store.
        
        Returns:
            Number of documents indexed
        """
        from sqlalchemy import text
        
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
                rows = conn.execute(text(sql)).fetchall()
            
            for row in rows:
                # Combine name + intro for better semantic matching
                text_content = f"{row.SubProjectName}. {row.Introduction}"
                
                embedding = self.embedder.encode(
                    f"passage: {text_content}",
                    normalize_embeddings=True
                )
                
                point_id = f"{region_id}_{row.SubProjectID}"
                
                points.append(models.PointStruct(
                    id=hash(point_id) & 0x7FFFFFFF,  # Positive int
                    vector=embedding.tolist(),
                    payload={
                        "region_id": region_id,
                        "project_id": row.ProjectID,
                        "subproject_id": row.SubProjectID,
                        "name": row.SubProjectName,
                        "text": text_content[:1000]  # Truncate for payload
                    }
                ))
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=batch
            )
        
        logger.info(f"Indexed {len(points)} documents to Qdrant")
        return len(points)
    
    async def search(
        self,
        query: str,
        region_id: Optional[int] = None,
        project_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query
            region_id: Filter by region (optional)
            project_id: Filter by project (optional)
            top_k: Number of results
            
        Returns:
            List of matching documents
        """
        # Embed query
        q_embedding = self.embedder.encode(
            f"query: {query}",
            normalize_embeddings=True
        )
        
        # Build filter
        must_conditions = []
        if region_id is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="region_id",
                    match=models.MatchValue(value=region_id)
                )
            )
        if project_id is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchValue(value=project_id)
                )
            )
        
        query_filter = models.Filter(must=must_conditions) if must_conditions else None
        
        # Search
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=q_embedding.tolist(),
            query_filter=query_filter,
            limit=top_k
        )
        
        return [
            {
                "name": r.payload["name"],
                "text": r.payload["text"],
                "score": r.score,
                "region_id": r.payload["region_id"],
                "project_id": r.payload["project_id"]
            }
            for r in results
        ]
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.COLLECTION_NAME)
        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status
        }
```

---

## Bước 2: Data Sync Job (Day 3-4)

### Tạo file `app/jobs/sync_vectors.py`

```python
"""
Sync database to Qdrant.
Run manually or as scheduled job.
"""
import asyncio
import logging
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_transformers import SentenceTransformer
from database.db import MultiDBManager
from rag.vector_store import TravelVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_all():
    """Sync all regions to Qdrant."""
    logger.info("Starting vector sync...")
    
    # Initialize
    embedder = SentenceTransformer("intfloat/multilingual-e5-small")
    db_manager = MultiDBManager()
    store = TravelVectorStore(
        embedder=embedder,
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
    
    # Index
    count = await store.index_from_database(db_manager)
    
    # Stats
    stats = store.get_stats()
    logger.info(f"Sync complete: {count} docs, {stats}")
    
    return count


if __name__ == "__main__":
    asyncio.run(sync_all())
```

### Run sync

```bash
# Manual sync
docker-compose exec fastapi python jobs/sync_vectors.py

# Verify
curl http://localhost:6333/collections/travel_knowledge
```

---

## Bước 3: Integrate vào ToolExecutor (Day 4-5)

### Cập nhật `app/tools/executor.py`

```python
class ToolExecutor:
    def __init__(self, db_manager, vector_store=None):
        self.db = db_manager
        self.vector_store = vector_store  # TravelVectorStore instance
        # ...

    async def _get_place_info(self, args: Dict, ctx: Dict) -> Dict:
        """Get place info - with vector fallback."""
        # Try SQL first
        result = await self._sql_get_place_info(args, ctx)
        
        if result["found"]:
            return result
        
        # Fallback to vector search
        if self.vector_store:
            logger.info(f"SQL miss, trying vector search: {args['place_name']}")
            return await self._search_places({"query": args["place_name"]}, ctx)
        
        return {"found": False, "message": "Không tìm thấy"}

    async def _search_places(self, args: Dict, ctx: Dict) -> Dict:
        """Vector search implementation."""
        if not self.vector_store:
            return {"found": False, "message": "Vector search chưa sẵn sàng"}
        
        results = await self.vector_store.search(
            query=args["query"],
            region_id=ctx.get("region_id"),
            project_id=ctx.get("project_id"),
            top_k=args.get("top_k", 5)
        )
        
        if results:
            return {
                "found": True,
                "places": results,
                "count": len(results),
                "source": "vector_search"
            }
        
        return {"found": False, "message": "Không tìm thấy kết quả"}
```

---

## Bước 4: Test (Day 6-7)

### Test queries

```python
# tests/test_vector_store.py
import pytest
from rag.vector_store import TravelVectorStore

@pytest.mark.asyncio
async def test_search_fuzzy_query():
    """Test vector search với query mơ hồ."""
    store = TravelVectorStore(embedder)
    
    results = await store.search("có gì hay ở Đà Nẵng", region_id=0)
    
    assert len(results) > 0
    assert any("Bà Nà" in r["name"] for r in results)

@pytest.mark.asyncio
async def test_region_filtering():
    """Test filtering by region."""
    store = TravelVectorStore(embedder)
    
    results = await store.search("điểm du lịch", region_id=1)
    
    for r in results:
        assert r["region_id"] == 1
```

---

## Data Flow

```
Query: "có gì vui ở Đà Nẵng?"
         │
         ▼
┌─────────────────────────────┐
│  ToolExecutor               │
│  get_attractions("Đà Nẵng") │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  SQL Query                  │
│  WHERE SubProjectName       │
│  LIKE '%Đà Nẵng%'           │
│  → No results               │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Vector Search (Qdrant)     │
│  query: "có gì vui ở Đà Nẵng" │
│  → Found: Bà Nà Hills (0.85)  │
│  → Found: Ngũ Hành Sơn (0.78) │
│  → Found: Biển Mỹ Khê (0.72)  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Return results             │
└─────────────────────────────┘
```

---

## Checklist

- [ ] Verify Qdrant container running
- [ ] Tạo `app/rag/vector_store.py`
- [ ] Test collection creation
- [ ] Tạo `app/jobs/sync_vectors.py`
- [ ] Run initial sync cho 4 regions
- [ ] Verify data trong Qdrant dashboard
- [ ] Cập nhật ToolExecutor với vector search
- [ ] Cập nhật Pipeline để inject vector_store
- [ ] Test fallback SQL → Vector
- [ ] Test region filtering
- [ ] Benchmark response time
