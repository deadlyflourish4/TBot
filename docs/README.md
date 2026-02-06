# TBot V2 - AI Travel Companion

## 📋 Mục Lục

- [Tổng Quan](#tổng-quan)
- [Kiến Trúc](#kiến-trúc)
- [Lộ Trình Phát Triển](#lộ-trình-phát-triển)
- [Quick Start](#quick-start)

---

## Tổng Quan

**TBot V2** nâng cấp từ template-matching RAG lên **LLM-driven Function Calling** với **Hybrid Search**.

### So Sánh V1 vs V2

| Aspect | V1 (Hiện tại) | V2 (Đề xuất) |
|--------|---------------|--------------|
| Intent Detection | SemanticRouter (binary) | LLM Function Calling |
| Query Processing | 4 SQL templates cố định | 5+ Tools động |
| Search | SQL exact match only | Hybrid (SQL + Vector) |
| Async | Synchronous | Celery + RabbitMQ |
| Scalability | Single worker | Distributed workers |

### Tech Stack

| Component | Technology |
|-----------|------------|
| **API** | FastAPI + Nginx |
| **LLM** | Ollama (qwen2.5/deepseek) |
| **Vector DB** | Qdrant |
| **Database** | SQL Server (4 regions) |
| **Message Broker** | RabbitMQ |
| **Cache** | Redis |
| **Task Queue** | Celery |
| **Container** | Docker Compose |

---

## Kiến Trúc

Chi tiết xem: [ARCHITECTURE.md](./ARCHITECTURE.md)

### High-Level Flow

```
User Query
    ↓
TravelAgent (Function Calling)
    ↓
Tool Selection (LLM decides)
    ↓
ToolExecutor → SQL / Vector Search
    ↓
Response Synthesis
    ↓
User Response
```

---

## Lộ Trình Phát Triển

Chi tiết xem: [ROADMAP.md](./ROADMAP.md)

| Phase | Timeline | Status |
|-------|----------|--------|
| Phase 0: Preparation | 2-3 ngày | 🔜 Pending |
| Phase 1: Function Calling | 1 tuần | 🔜 Pending |
| Phase 2: Hybrid RAG | 1 tuần | 🔜 Pending |
| Phase 3: Async Infrastructure | 3-4 ngày | 🔜 Pending |
| Phase 4: Testing | 3-4 ngày | 🔜 Pending |

---

## Quick Start

### Prerequisites

- Docker Desktop with GPU support
- Python 3.10+
- Ollama installed locally

### Development Setup

```bash
# Clone và setup
git clone <repo-url>
cd TBot

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f fastapi
```

### Test Chatbot

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Bà Nà Hills ở đâu?",
    "project_id": 1,
    "region_id": 0
  }'
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Kiến trúc hệ thống chi tiết |
| [ROADMAP.md](./ROADMAP.md) | Lộ trình phát triển |
| [CHATBOT_BEHAVIOR.md](./CHATBOT_BEHAVIOR.md) | Hành vi chatbot sau upgrade |
| [PHASE1_FUNCTION_CALLING.md](./PHASE1_FUNCTION_CALLING.md) | Hướng dẫn Phase 1 |
| [PHASE2_HYBRID_RAG.md](./PHASE2_HYBRID_RAG.md) | Hướng dẫn Phase 2 |
| [PHASE3_ASYNC.md](./PHASE3_ASYNC.md) | Hướng dẫn Phase 3 |
| [API_REFERENCE.md](./API_REFERENCE.md) | API Documentation |
