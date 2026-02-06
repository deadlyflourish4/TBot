# ===== 1. Standard library imports =====
import io
import os
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from os import getenv
from typing import List, Optional

import edge_tts

from database.db import MultiDBManager
from deep_translator import GoogleTranslator

# ===== 2. Third-party imports =====
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from services.chat_manager import ChatManager
from services.storage import GCStorage
from google import genai
from google.genai.types import GenerateContentConfig, ImageConfig, Modality, Part
from langdetect import detect
from PIL import Image
from fastapi.staticfiles import StaticFiles

# ===== 3. Local project imports =====
from pipeline import GraphOrchestrator
from pydantic import BaseModel
from security.middleware import jwt_middleware

security = HTTPBearer()
app = FastAPI(
    title="Orpheo Multi-Region API",
    swagger_ui_parameters={"persistAuthorization": True},
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount(
    "/storage",
    StaticFiles(directory=os.path.join(BASE_DIR, "storage")),
    name="storage",
)
app.middleware("http")(jwt_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
# --- deps ---
bot = GraphOrchestrator()
db_manager = MultiDBManager()
chat_sessions = ChatManager(db_manager=db_manager, session_timeout=1800)
tts_storage = GCStorage(credentials_path="./GCP/guidepassasiacloud-250f74bc75bb.json")

# --- cache voices ---
GCS_bucket = "guidepassasia_chatbot"
GCS_image = "guidepassasia_image_generation"
tts_buffers = {}
VOICE_MAP = {
    "ar": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "en": {
        "male": "en-US-BrianMultilingualNeural",
        "female": "en-US-EmmaMultilingualNeural",
    },
    "pt": {"male": "pt-PT-DuarteNeural", "female": "pt-PT-RaquelNeural"},
    "de": {
        "male": "de-DE-KillianNeural",
        "female": "de-DE-SeraphinaMultilingualNeural",
    },
    "ko": {"male": "ko-KR-HyunsuMultilingualNeural", "female": "ko-KR-SunHiNeural"},
    "hu": {"male": "hu-HU-TamasNeural", "female": "hu-HU-NoemiNeural"},
    "id": {"male": "id-ID-ArdiNeural", "female": "id-ID-GadisNeural"},
    "ms": {"male": "ms-MY-OsmanNeural", "female": "ms-MY-YasminNeural"},
    "ru": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"},
    "ja": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural"},
    "fi": {"male": "fi-FI-HarriNeural", "female": "fi-FI-NooraNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-VivienneMultilingualNeural"},
    "fil": {"male": "fil-PH-AngeloNeural", "female": "fil-PH-BlessicaNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-XimenaNeural"},
    "th": {"male": "th-TH-NiwatNeural", "female": "th-TH-PremwadeeNeural"},
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "zh-CN": {"male": "zh-CN-YunjianNeural", "female": "zh-CN-XiaoxiaoNeural"},
    "zh-HK": {"male": "zh-HK-WanLungNeural", "female": "zh-HK-HiuGaaiNeural"},
    "vi": {"male": "vi-VN-NamMinhNeural", "female": "vi-VN-HoaiMyNeural"},
    "it": {"male": "it-IT-DiegoNeural", "female": "it-IT-ElsaNeural"},
}


# ---------- MODELS ----------
class TextRequest(BaseModel):
    text: str
    lang_code: str
    gender: str


class ChatRequest(BaseModel):
    text: str
    user_geography: str
    project_id: int
    region_id: int
    session_id: str = None


class ImageGenRequest(BaseModel):
    content_uri: str
    style_uris: List[str]
    prompt: Optional[str] = (
        "Generate an image that keeps the composition of the content image "
        "but adopts the color palette and lighting style of the reference images."
    )
    file_name: str
    aspect_ratio: Optional[str] = "1:1"
    model_id: Optional[str] = "gemini-2.5-flash-image"


# ---------- TTS (Async via Celery + Chatterbox) ----------
from tasks.tts_tasks import generate_tts, LANGUAGE_MAP


class TTSRequest(BaseModel):
    """Request model for TTS generation."""
    text: str
    language_id: str = "en"  # 23 languages: ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh
    exaggeration: float = 0.5  # 0.0-1.0, higher = more expressive
    cfg_weight: float = 0.5  # 0.0-1.0, lower = more expressive


@app.post("/api/text-to-speech")
async def text_to_speech(req: TTSRequest):
    """
    Submit TTS request for async processing via Celery.
    
    Supported languages (23):
    ar (Arabic), da (Danish), de (German), el (Greek), en (English),
    es (Spanish), fi (Finnish), fr (French), he (Hebrew), hi (Hindi),
    it (Italian), ja (Japanese), ko (Korean), ms (Malay), nl (Dutch),
    no (Norwegian), pl (Polish), pt (Portuguese), ru (Russian),
    sv (Swedish), sw (Swahili), tr (Turkish), zh (Chinese)
    
    Returns:
        task_id: Use to poll /api/tts/status/{task_id}
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")
    if len(text) > 1000:
        raise HTTPException(400, "Text too long (max 1000 chars)")
    
    if req.language_id not in LANGUAGE_MAP:
        raise HTTPException(400, f"Unsupported language: {req.language_id}. Supported: {list(LANGUAGE_MAP.keys())}")
    
    # Submit to Celery queue
    task = generate_tts.delay(
        text=text,
        language_id=req.language_id,
        exaggeration=req.exaggeration,
        cfg_weight=req.cfg_weight,
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "message": "TTS processing started. Poll /api/tts/status/{task_id} for result.",
    }


@app.get("/api/tts/status/{task_id}")
async def tts_status(task_id: str):
    """
    Check TTS task status.
    
    Returns:
        - status: "PENDING" | "STARTED" | "completed" | "failed"
        - url: Audio URL (when completed)
    """
    from celery.result import AsyncResult
    from tasks import celery_app
    
    result = AsyncResult(task_id, app=celery_app)
    
    if result.ready():
        if result.successful():
            return {"status": "completed", **result.get()}
        else:
            return {"status": "failed", "error": str(result.result)}
    else:
        return {"status": result.state, "task_id": task_id}


@app.get("/api/tts/languages")
async def tts_languages():
    """Get list of supported TTS languages."""
    return {"languages": LANGUAGE_MAP}


@app.post("/api/delete-tts")
def delete_tts(url: str = Body(..., embed=True)):
    """Delete a TTS audio file. TODO: Implement based on your storage backend."""
    # TODO: Call backend API to delete file
    return {"message": "Not implemented", "url": url}



# ---------- TRANSLATE ----------
@app.post("/api/text-translate")
async def text_translate(req: TextRequest, target_lang: str = "en"):
    text = req.text.strip()
    if not text:
        return {"error": "Text cannot be empty"}
    if len(text) > 5000:
        return {"error": "Text must be under 5000 characters"}
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return {"translated_text": translated}
    except Exception as e:
        return {"error": f"translation_failed: {e}"}


# ---------- CHATBOT ----------
@app.post("/api/chatbot-response")
async def chatbot_response(req: ChatRequest):
    session_id = req.session_id
    session = chat_sessions.get_session(session_id) if session_id else None

    if not session:
        session = chat_sessions.create_session(req.region_id, session_id=session_id)
        session_id = session.session_id

    region_id = req.region_id

    response_text = bot.run(
        session_id=session_id,
        user_question=req.text,
        user_location=req.user_geography,
        project_id=req.project_id,
        region_id=region_id,
    )

    session.add_message("user", req.text)
    # session.add_message("assistant", response_text)

    return response_text


@app.post("/api/generate-image")
def generate_image(req: ImageGenRequest):
    """
    Generate an image based on one content image and multiple style reference images using Vertex AI (Gemini/Imagen).

    Args:
        content_uri: GCS URI of the main content image.
        style_uris: List of GCS URIs for style reference images.
        prompt: Instruction describing how to combine content and styles.
        aspect_ratio: Output aspect ratio ("1:1", "16:9", etc.)
        model_id: The Gemini or Imagen model to use.
        output_path: Local path to save the generated image.
    """
    # --- Khởi tạo Vertex AI client ---
    PROJECT_ID = "guidepassasiacloud"
    LOCATION = "us-central1"

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        "./GCP/guidepassasiacloud-250f74bc75bb.json"
    )
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    content_uri = req.content_uri.strip('"').strip("'")
    style_uris = [u.strip('"').strip("'") for u in req.style_uris]
    prompt = req.prompt
    aspect_ratio = req.aspect_ratio
    model_id = req.model_id
    file_name = req.file_name

    # --- Tạo phần nội dung input ---
    contents = [
        "This is the content image whose composition should be followed:",
        Part.from_uri(file_uri=content_uri, mime_type="image/jpeg"),
        "These are style reference images whose visual style should be applied:",
    ]
    for uri in style_uris:
        contents.append(Part.from_uri(file_uri=uri, mime_type="image/jpeg"))

    contents.append(prompt)

    # --- Gọi model ---
    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=GenerateContentConfig(
            response_modalities=[Modality.IMAGE],
            image_config=ImageConfig(aspect_ratio=aspect_ratio),
        ),
    )

    # --- Lấy ảnh đầu tiên ---
    part = response.candidates[0].content.parts[0]
    img = Image.open(BytesIO(part.inline_data.data))

    # --- Upload lên GCS ---
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    gcs = GCStorage()
    url = gcs.upload_from_bytes(GCS_image, buffer.getvalue(), file_name)

    # print(f" Image uploaded: {url}")
    return url
