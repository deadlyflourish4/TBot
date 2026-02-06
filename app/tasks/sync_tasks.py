"""
Vector sync background tasks.
Sync database content to Qdrant.
"""
import logging

from tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def sync_all_regions(self):
    """
    Sync all database regions to Qdrant.
    Called daily by Celery Beat or manually triggered.
    """
    import asyncio
    
    logger.info("Starting full vector sync...")
    
    try:
        # Lazy imports to avoid circular dependencies
        from database.db import MultiDBManager
        from sentence_transformers import SentenceTransformer
        
        # Check if Qdrant is configured
        import os
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        
        # Import vector store (will be created in Phase 2)
        try:
            from rag.vector_store import TravelVectorStore
            
            embedder = SentenceTransformer("intfloat/multilingual-e5-small")
            db_manager = MultiDBManager()
            store = TravelVectorStore(embedder=embedder, host=qdrant_host)
            
            count = asyncio.run(store.index_from_database(db_manager))
            
            logger.info(f"Vector sync complete: {count} documents indexed")
            return {"indexed": count, "task_id": self.request.id, "status": "success"}
            
        except ImportError:
            logger.warning("TravelVectorStore not yet implemented (Phase 2)")
            return {"status": "skipped", "message": "Vector store not implemented yet"}
            
    except Exception as e:
        logger.error(f"Vector sync failed: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def sync_single_region(self, region_id: int):
    """Sync a specific region to Qdrant."""
    import asyncio
    
    logger.info(f"Syncing region {region_id}...")
    
    try:
        from database.db import MultiDBManager
        from sentence_transformers import SentenceTransformer
        
        import os
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        
        try:
            from rag.vector_store import TravelVectorStore
            
            embedder = SentenceTransformer("intfloat/multilingual-e5-small")
            db_manager = MultiDBManager()
            store = TravelVectorStore(embedder=embedder, host=qdrant_host)
            
            count = asyncio.run(store.index_region(db_manager, region_id))
            
            return {"region_id": region_id, "indexed": count, "status": "success"}
            
        except ImportError:
            return {"status": "skipped", "message": "Vector store not implemented yet"}
            
    except Exception as e:
        logger.error(f"Region sync failed: {e}")
        return {"status": "error", "message": str(e)}
