"""
Manual sync script: SQL Server → Qdrant.
Usage: python jobs/sync_vectors.py [--region REGION_ID]
"""
import asyncio
import argparse
import logging
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_transformers import SentenceTransformer
from database.db import MultiDBManager
from rag.vector_store import TravelVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def sync_all():
    """Sync all 4 regions to Qdrant."""
    logger.info("Starting full vector sync...")

    embedder = SentenceTransformer("intfloat/multilingual-e5-small")
    db_manager = MultiDBManager()
    store = TravelVectorStore(
        embedder=embedder,
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    count = await store.index_from_database(db_manager)
    stats = store.get_stats()
    logger.info(f"Sync complete: {count} docs indexed | {stats}")
    return count


async def sync_region(region_id: int):
    """Sync a single region."""
    logger.info(f"Syncing region {region_id}...")

    embedder = SentenceTransformer("intfloat/multilingual-e5-small")
    db_manager = MultiDBManager()
    store = TravelVectorStore(
        embedder=embedder,
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    count = await store.index_region(db_manager, region_id)
    logger.info(f"Region {region_id} sync complete: {count} docs")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync SQL → Qdrant")
    parser.add_argument("--region", type=int, help="Specific region ID (0-3)")
    args = parser.parse_args()

    if args.region is not None:
        asyncio.run(sync_region(args.region))
    else:
        asyncio.run(sync_all())
