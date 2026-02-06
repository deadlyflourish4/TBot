# Chatterbox TTS + Celery Integration

Hướng dẫn tích hợp **Chatterbox TTS** với **Celery + RabbitMQ** cho xử lý bất đồng bộ.

## Quick Start

### 1. Cấu hình Upload API

Mở file `app/tasks/tts_tasks.py` và cập nhật:

```python
# Thay đổi URL và API key theo backend của bạn
UPLOAD_API_URL = os.getenv("TTS_UPLOAD_API_URL", "https://your-backend.com/upload")
UPLOAD_API_KEY = os.getenv("TTS_UPLOAD_API_KEY", "your-api-key")
```

Hoặc set environment variables trong `.env`:

```env
TTS_UPLOAD_API_URL=https://your-backend.com/api/upload-audio
TTS_UPLOAD_API_KEY=your-secret-key
```

### 2. Implement `upload_audio_to_backend()`

Trong `tts_tasks.py`, cập nhật hàm `upload_audio_to_backend()` theo API spec của backend:

```python
def upload_audio_to_backend(audio_buffer: io.BytesIO, filename: str) -> dict:
    import requests
    
    response = requests.post(
        UPLOAD_API_URL,
        headers={"Authorization": f"Bearer {UPLOAD_API_KEY}"},
        files={"file": (filename, audio_buffer, "audio/wav")},
    )
    response.raise_for_status()
    return response.json()  # Expected: {"url": "...", "file_id": "..."}
```

---

## API Endpoints

### POST `/api/text-to-speech`
Submit TTS request (async).

**Request:**
```json
{
    "text": "Hello world",
    "language_id": "en",
    "exaggeration": 0.5,
    "cfg_weight": 0.5
}
```

**Response:**
```json
{
    "task_id": "abc123-def456",
    "status": "pending",
    "message": "TTS processing started..."
}
```

### GET `/api/tts/status/{task_id}`
Poll for result.

**Response (pending):**
```json
{"status": "STARTED", "task_id": "abc123"}
```

**Response (completed):**
```json
{
    "status": "completed",
    "url": "https://your-backend.com/audio/tts_abc123.wav",
    "language": "en"
}
```

### GET `/api/tts/languages`
List 23 supported languages.

---

## Supported Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| ar | Arabic | nl | Dutch |
| da | Danish | no | Norwegian |
| de | German | pl | Polish |
| el | Greek | pt | Portuguese |
| en | English | ru | Russian |
| es | Spanish | sv | Swedish |
| fi | Finnish | sw | Swahili |
| fr | French | tr | Turkish |
| he | Hebrew | zh | Chinese |
| hi | Hindi | ja | Japanese |
| it | Italian | ko | Korean |
| ms | Malay | | |

---

## Parameters

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `exaggeration` | 0.5 | Độ biểu cảm (0.0-1.0). Cao = dramatic |
| `cfg_weight` | 0.5 | CFG weight. Thấp = expressive hơn |

**Tips:**
- Neutral/normal: `exaggeration=0.5, cfg_weight=0.5`
- Expressive: `exaggeration=0.7, cfg_weight=0.3`
- Language transfer: `cfg_weight=0.0`

---

## Run Services

```bash
# 1. Start infrastructure
docker compose up -d rabbitmq redis

# 2. Start Celery worker (needs GPU)
cd app
celery -A tasks worker -l info

# 3. Start FastAPI
uvicorn main:app --reload
```

---

## Requirements

- **GPU**: CUDA-compatible GPU (required for Chatterbox)
- **Python**: 3.11
- **Dependencies**: `chatterbox-tts`, `torchaudio`, `celery`, `redis`
