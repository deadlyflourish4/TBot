# Phase 0: Infrastructure Setup

## Overview

Phase này chuẩn bị nền tảng infrastructure cho TBot V2, bao gồm Docker services mới và dependencies.

**Thời gian dự kiến**: 2-3 ngày

---

## Objectives

1. Cập nhật Docker Compose với services mới
2. Thêm Python dependencies
3. Cấu hình environment variables
4. Verify tất cả services chạy được

---

## 1. Docker Compose Updates

### Services mới cần thêm

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `qdrant` | `qdrant/qdrant:latest` | 6333, 6334 | Vector database |
| `redis` | `redis:7-alpine` | 6379 | Cache + Celery backend |
| `rabbitmq` | `rabbitmq:3-management-alpine` | 5672, 15672 | Message broker |
| `celery_worker` | (build from ./app) | - | Background tasks |

### docker-compose.yml additions

```yaml
services:
  # ... existing services ...

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: tbot
      RABBITMQ_DEFAULT_PASS: tbot123
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  celery_worker:
    build: ./app
    container_name: celery_worker
    command: celery -A tasks worker -l info -c 2
    env_file:
      - .env
    environment:
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: amqp://tbot:tbot123@rabbitmq:5672//
    depends_on:
      - redis
      - rabbitmq

volumes:
  qdrant_data:
  redis_data:
  rabbitmq_data:
```

---

## 2. Python Dependencies

### Thêm vào requirements.txt

```txt
# ===============================
# Vector Database
# ===============================
qdrant-client>=1.7.0

# ===============================
# Async Task Queue
# ===============================
celery>=5.3.0
redis>=5.0.0
kombu>=5.3.0

# ===============================
# Agent Framework
# ===============================
langgraph

# ===============================
# Observability (Phase 4)
# ===============================
langfuse
```

---

## 3. Environment Variables

### Thêm vào .env.example

```bash
# ===============================
# Vector Database (Qdrant)
# ===============================
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# ===============================
# Cache & Message Queue
# ===============================
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=amqp://tbot:tbot123@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ===============================
# LLM Configuration
# ===============================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b
```

---

## 4. Verification Steps

### 4.1 Start infrastructure

```bash
cd TBot
docker-compose up -d qdrant redis rabbitmq
```

### 4.2 Verify Qdrant

```bash
# Check Qdrant health
curl http://localhost:6333/health

# Expected: {"status":"ok"}
```

**Dashboard**: Open `http://localhost:6333/dashboard`

### 4.3 Verify Redis

```bash
docker exec -it redis redis-cli PING

# Expected: PONG
```

### 4.4 Verify RabbitMQ

**Management UI**: Open `http://localhost:15672`
- Username: `tbot`
- Password: `tbot123`

---

## 5. Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflict 6333 | Change Qdrant port mapping |
| RabbitMQ won't start | Check disk space (needs >200MB free) |
| Redis connection refused | Ensure redis container is running |

---

## Acceptance Criteria

- [ ] `docker-compose up -d` không có lỗi
- [ ] Qdrant dashboard accessible tại `localhost:6333`
- [ ] Redis PING trả về PONG
- [ ] RabbitMQ Management UI accessible
- [ ] `pip install -r requirements.txt` thành công

---

## Next Steps

Sau khi Phase 0 hoàn thành → Chuyển sang [Phase 1: LangGraph Agent](./PHASE1_LANGGRAPH.md)
