# 📅 TBot V2 Development Roadmap

## Timeline Overview

```
         Week 1         Week 2         Week 3         Week 4         Week 5
    ┌───────────────────────────────────────────────────────────────────────┐
    │ Phase 0 │      Phase 1          │      Phase 2          │  Phase 3   │
    │  Prep   │   Function Calling    │    Hybrid RAG         │   Async    │
    │ (2-3d)  │      (7 days)         │     (7 days)          │  (3-4d)    │
    └───────────────────────────────────────────────────────────────────────┘
                                                                │  Phase 4  │
                                                                │  Testing  │
                                                                │  (3-4d)   │
```

---

## Phase 0: Preparation (2-3 ngày)

### Mục tiêu
Chuẩn bị infrastructure và dependencies trước khi code.

### Tasks

| Task | File/Command | Done |
|------|--------------|------|
| Cập nhật docker-compose.yml | `docker-compose.yml` | ☐ |
| Thêm dependencies | `requirements.txt` | ☐ |
| Tạo .env.example | `.env.example` | ☐ |
| Test services chạy | `docker-compose up -d` | ☐ |
| Tạo feature branch | `git checkout -b feature/v2` | ☐ |

### docker-compose.yml additions

```yaml
# Thêm vào docker-compose.yml hiện tại
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: tbot
      RABBITMQ_DEFAULT_PASS: tbot123

  celery_worker:
    build: ./app
    command: celery -A tasks worker -l info
    depends_on:
      - redis
      - rabbitmq

volumes:
  qdrant_data:
```

### Verification
```bash
docker-compose ps  # Tất cả services running
curl http://localhost:6333/collections  # Qdrant OK
curl http://localhost:15672  # RabbitMQ dashboard
```

---

## Phase 1: Function Calling Core (1 tuần)

### Mục tiêu
Thay thế SemanticRouter + QueryStore bằng LLM-driven TravelAgent.

### Chi tiết: [PHASE1_FUNCTION_CALLING.md](./PHASE1_FUNCTION_CALLING.md)

### Tasks Summary

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Tool Definitions | `app/tools/definitions.py` |
| 2-3 | Tool Executor | `app/tools/executor.py` |
| 4-5 | TravelAgent | `app/agents/travel_agent.py` |
| 6-7 | Pipeline Integration | Modified `pipeline.py` |

### Success Criteria
- [ ] Agent gọi đúng tool cho query "Bà Nà Hills ở đâu?"
- [ ] Agent gọi đúng tool cho query "có video gì về Hội An?"
- [ ] Chitchat vẫn hoạt động ("xin chào")
- [ ] Multi-region (0-3) đều work

---

## Phase 2: Hybrid RAG với Qdrant (1 tuần)

### Mục tiêu
Bổ sung vector search khi SQL exact match không tìm thấy.

### Chi tiết: [PHASE2_HYBRID_RAG.md](./PHASE2_HYBRID_RAG.md)

### Tasks Summary

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Qdrant Setup | `app/rag/vector_store.py` |
| 3-4 | Data Sync Job | `app/jobs/sync_vectors.py` |
| 4-5 | Hybrid Search | Updated `search_places()` tool |
| 6-7 | Fallback Logic | SQL → Vector chain |

### Success Criteria
- [ ] Qdrant có data từ tất cả 4 databases
- [ ] Query "có gì hay ở Đà Nẵng?" trả về relevant results
- [ ] Filtering by region_id hoạt động
- [ ] Response time < 2 seconds

---

## Phase 3: Async Infrastructure (3-4 ngày)

### Mục tiêu
Non-blocking background tasks cho TTS, sync, notifications.

### Chi tiết: [PHASE3_ASYNC.md](./PHASE3_ASYNC.md)

### Tasks Summary

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Celery Config | `app/tasks/__init__.py` |
| 2 | TTS Async | `app/tasks/tts_tasks.py` |
| 2-3 | Vector Sync Task | `app/tasks/sync_tasks.py` |
| 3-4 | Redis Caching | Session + query cache |

### Success Criteria
- [ ] TTS endpoint returns task_id immediately
- [ ] Sync job runs without blocking API
- [ ] Redis caches session memory
- [ ] RabbitMQ dashboard shows task flow

---

## Phase 4: Testing & Deployment (3-4 ngày)

### Mục tiêu
Ensure production-ready quality.

### Tasks

| Task | Type | Command |
|------|------|---------|
| Unit tests | Automated | `pytest tests/unit/` |
| Integration tests | Automated | `pytest tests/integration/` |
| Load testing | Manual | `locust -f loadtest.py` |
| Staging deploy | Manual | `docker-compose -f staging.yml up` |
| Documentation | Manual | Update README, API docs |

### Success Criteria
- [ ] Test coverage > 70%
- [ ] All 4 regions pass integration tests
- [ ] Response time P95 < 3 seconds
- [ ] No critical bugs in staging

---

## Risk Management

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ollama function calling unstable | High | Keep SemanticRouter as fallback |
| Qdrant slow indexing | Medium | Batch indexing, background job |
| Celery task failures | Medium | Retry logic, dead letter queue |
| Breaking existing features | High | Extensive testing, feature flags |

---

## Dependencies

```
# requirements.txt additions
qdrant-client>=1.7.0
celery>=5.3.0
redis>=5.0.0
kombu>=5.3.0
```

---

## Monitoring

| Service | Dashboard URL |
|---------|---------------|
| RabbitMQ | http://localhost:15672 |
| Qdrant | http://localhost:6333/dashboard |
| Flower (Celery) | http://localhost:5555 |
