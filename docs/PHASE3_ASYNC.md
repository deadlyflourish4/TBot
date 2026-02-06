# Phase 3: Async Infrastructure

## Mục tiêu

Non-blocking background tasks cho TTS, vector sync, và notifications.

---

## Kiến Trúc Async

```
FastAPI                RabbitMQ              Celery Worker
   │                      │                       │
   │─── Task Request ────▶│                       │
   │◀── Task ID ──────────│                       │
   │                      │─── Dispatch ─────────▶│
   │                      │                       │── Execute
   │                      │                       │── Store result
   │                      │◀── Complete ──────────│
   │─── Poll result ─────▶│                       │
   │◀── Result ───────────│                       │
```

---

## Bước 1: Celery Configuration (Day 1)

### Tạo file `app/tasks/__init__.py`

```python
"""
Celery application configuration.
"""
import os
from celery import Celery

# Create Celery app
celery_app = Celery(
    "tbot_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://tbot:tbot123@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=[
        "tasks.tts_tasks",
        "tasks.sync_tasks",
        "tasks.notification_tasks"
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
)

# Periodic tasks (optional)
celery_app.conf.beat_schedule = {
    "sync-vectors-daily": {
        "task": "tasks.sync_tasks.sync_all_regions",
        "schedule": 86400.0,  # Every 24 hours
    },
}
```

### Thêm vào `requirements.txt`

```
celery>=5.3.0
redis>=5.0.0
kombu>=5.3.0
```

---

## Bước 2: TTS Task (Day 2)

### Tạo file `app/tasks/tts_tasks.py`

```python
"""
Async TTS generation tasks.
"""
import io
import logging
import edge_tts
from google.cloud import storage

from tasks import celery_app

logger = logging.getLogger(__name__)

# Voice mapping
VOICE_MAP = {
    "vi": {"male": "vi-VN-NamMinhNeural", "female": "vi-VN-HoaiMyNeural"},
    "en": {"male": "en-US-GuyNeural", "female": "en-US-JennyNeural"},
    "zh": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaomoNeural"},
}


@celery_app.task(bind=True, max_retries=3)
def generate_tts(self, text: str, lang: str = "vi", gender: str = "female") -> dict:
    """
    Generate TTS audio asynchronously.
    
    Args:
        text: Text to synthesize
        lang: Language code (vi, en, zh)
        gender: Voice gender (male, female)
        
    Returns:
        {"url": "https://storage.googleapis.com/...", "duration": 5.2}
    """
    try:
        # Get voice
        voice = VOICE_MAP.get(lang, VOICE_MAP["vi"])[gender]
        
        # Generate audio
        communicate = edge_tts.Communicate(text, voice)
        audio_data = io.BytesIO()
        
        for chunk in communicate.stream_sync():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        
        # Upload to GCS
        client = storage.Client()
        bucket = client.bucket("tbot-audio")
        blob = bucket.blob(f"tts/{self.request.id}.mp3")
        blob.upload_from_file(audio_data, content_type="audio/mpeg")
        blob.make_public()
        
        url = blob.public_url
        logger.info(f"TTS generated: {url}")
        
        return {
            "url": url,
            "task_id": self.request.id,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        # Retry with exponential backoff
        self.retry(exc=e, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_old_audio(max_age_hours: int = 24):
    """Delete old TTS files from GCS."""
    from datetime import datetime, timedelta
    
    client = storage.Client()
    bucket = client.bucket("tbot-audio")
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    count = 0
    for blob in bucket.list_blobs(prefix="tts/"):
        if blob.time_created < cutoff:
            blob.delete()
            count += 1
    
    logger.info(f"Cleaned up {count} old audio files")
    return count
```

---

## Bước 3: Vector Sync Task (Day 2-3)

### Tạo file `app/tasks/sync_tasks.py`

```python
"""
Background tasks for vector synchronization.
"""
import logging
from tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def sync_all_regions(self):
    """
    Sync all database regions to Qdrant.
    Called daily by Celery Beat.
    """
    from database.db import MultiDBManager
    from rag.vector_store import TravelVectorStore
    from sentence_transformers import SentenceTransformer
    import asyncio
    
    logger.info("Starting full vector sync...")
    
    embedder = SentenceTransformer("intfloat/multilingual-e5-small")
    db_manager = MultiDBManager()
    store = TravelVectorStore(embedder=embedder)
    
    count = asyncio.run(store.index_from_database(db_manager))
    
    logger.info(f"Vector sync complete: {count} documents")
    return {"indexed": count, "task_id": self.request.id}


@celery_app.task(bind=True)
def sync_single_region(self, region_id: int):
    """Sync a specific region to Qdrant."""
    from database.db import MultiDBManager
    from rag.vector_store import TravelVectorStore
    from sentence_transformers import SentenceTransformer
    import asyncio
    
    logger.info(f"Syncing region {region_id}...")
    
    embedder = SentenceTransformer("intfloat/multilingual-e5-small")
    db_manager = MultiDBManager()
    store = TravelVectorStore(embedder=embedder)
    
    # Only sync specific region
    count = asyncio.run(store.index_region(db_manager, region_id))
    
    return {"region_id": region_id, "indexed": count}
```

---

## Bước 4: Redis Caching (Day 3-4)

### Tạo file `app/utils/cache.py`

```python
"""
Redis caching utilities.
"""
import json
import logging
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache wrapper."""
    
    def __init__(self, host: str = "redis", port: int = 6379, db: int = 1):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.default_ttl = 3600  # 1 hour
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set cached value."""
        self.client.setex(
            key,
            ttl or self.default_ttl,
            json.dumps(value, ensure_ascii=False)
        )
    
    def delete(self, key: str):
        """Delete cached value."""
        self.client.delete(key)
    
    # Session memory cache
    def get_session(self, session_id: str) -> Optional[list]:
        """Get cached session messages."""
        return self.get(f"session:{session_id}")
    
    def set_session(self, session_id: str, messages: list, ttl: int = 1800):
        """Cache session messages (30 min default)."""
        self.set(f"session:{session_id}", messages, ttl)
    
    # Query result cache
    def get_query_result(self, query_hash: str) -> Optional[dict]:
        """Get cached query result."""
        return self.get(f"query:{query_hash}")
    
    def set_query_result(self, query_hash: str, result: dict, ttl: int = 300):
        """Cache query result (5 min default)."""
        self.set(f"query:{query_hash}", result, ttl)
```

### Integrate với Pipeline

```python
# pipeline.py
from utils.cache import RedisCache

class Pipeline:
    def __init__(self):
        # ...
        self.cache = RedisCache()

class GraphOrchestrator:
    async def run(self, ...):
        # Check cache first
        query_hash = hashlib.md5(f"{query}:{region_id}:{project_id}".encode()).hexdigest()
        cached = self.pipeline.cache.get_query_result(query_hash)
        if cached:
            return cached
        
        # Process query...
        result = await self.pipeline.agent.run(...)
        
        # Cache result
        self.pipeline.cache.set_query_result(query_hash, result)
        
        return result
```

---

## Bước 5: API Integration

### Cập nhật `app/main.py`

```python
from tasks.tts_tasks import generate_tts

@app.post("/tts")
async def text_to_speech(req: TextRequest):
    """
    Generate TTS asynchronously.
    Returns task_id immediately, poll for result.
    """
    # Send to Celery
    task = generate_tts.delay(
        text=req.text,
        lang=req.lang_code,
        gender=req.gender
    )
    
    return {
        "task_id": task.id,
        "status": "processing",
        "poll_url": f"/tts/status/{task.id}"
    }

@app.get("/tts/status/{task_id}")
async def get_tts_status(task_id: str):
    """Get TTS task status."""
    from tasks import celery_app
    
    result = celery_app.AsyncResult(task_id)
    
    if result.ready():
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result.get()
        }
    else:
        return {
            "task_id": task_id,
            "status": result.status,
        }
```

---

## Monitoring

### Flower Dashboard

```yaml
# docker-compose.yml
flower:
  image: mher/flower
  ports:
    - "5555:5555"
  environment:
    CELERY_BROKER_URL: amqp://tbot:tbot123@rabbitmq:5672//
  depends_on:
    - rabbitmq
```

Access: http://localhost:5555

---

## Checklist

- [ ] Tạo `app/tasks/__init__.py` với Celery config
- [ ] Tạo `app/tasks/tts_tasks.py`
- [ ] Tạo `app/tasks/sync_tasks.py`
- [ ] Tạo `app/utils/cache.py`
- [ ] Cập nhật `docker-compose.yml` với Celery worker
- [ ] Test TTS async endpoint
- [ ] Test vector sync task
- [ ] Verify RabbitMQ message flow
- [ ] Setup Flower monitoring
- [ ] Integrate Redis caching vào Pipeline
