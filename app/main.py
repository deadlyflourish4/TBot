# ===== 1. Standard library imports =====
import io
import os
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from os import getenv
from typing import List, Optional


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
from tasks.sync_tasks import sync_all_regions, sync_single_region

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

# --- GCS (for image generation only) ---
GCS_image = "guidepassasia_image_generation"


# ---------- MODELS ----------
class TextRequest(BaseModel):
    text: str


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
    """Request model for TTS generation from C#."""
    id: str  # Unique ID from C#
    poi: str  # Point of Interest name
    langcode: str = "en"  # Language code: en, vi, ko, ja, zh, etc.
    text: str  # Text content to convert
    content_type: str = "detail"  # "attraction" or "detail"


@app.post("/api/text-to-speech")
async def text_to_speech(req: TTSRequest):
    """
    API 1: Submit TTS request for async processing.
    
    Input from C#:
        id, poi, langcode, text, content_type
    
    Returns:
        task_id to use with /api/tts/status/{task_id}
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")
    if len(text) > 5000:
        raise HTTPException(400, "Text too long (max 5000 chars)")
    
    # Map langcode to Chatterbox language_id
    language_id = req.langcode.lower()
    if language_id not in LANGUAGE_MAP:
        language_id = "en"  # Default to English if unsupported
    
    # Submit to Celery queue with custom ID
    task = generate_tts.apply_async(
        kwargs={
            "text": text,
            "language_id": language_id,
            "audio_id": req.id,
        },
        task_id=req.id
    )
    
    return {
        "task_id": task.id,
        "id": req.id,
        "poi": req.poi,
        "content_type": req.content_type,
        "status": "pending",
    }


@app.get("/api/tts/status/{task_id}")
async def tts_status(task_id: str):
    """
    API 2: Check TTS task status.
    
    Returns:
        - status: "PENDING" | "STARTED" | "completed" | "failed"
        - url: Local file path (when completed)
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


# ---------- VECTOR SYNC ----------
@app.post("/api/sync-vectors")
async def trigger_vector_sync(region_id: Optional[int] = None):
    """Trigger Qdrant vector sync (background task)."""
    if region_id is not None:
        task = sync_single_region.delay(region_id)
        return {"task_id": task.id, "region_id": region_id, "status": "syncing"}
    else:
        task = sync_all_regions.delay()
        return {"task_id": task.id, "regions": "all", "status": "syncing"}

# ---------- CHATBOT ----------
@app.post("/api/chatbot-response")
async def chatbot_response(req: ChatRequest):
    session_id = req.session_id
    session = chat_sessions.get_session(session_id) if session_id else None

    if not session:
        session = chat_sessions.create_session(req.region_id, session_id=session_id)
        session_id = session.session_id

    # V2: TravelAgent with function calling (async)
    result = await bot.run(
        session_id=session_id,
        user_question=req.text,
        user_location=req.user_geography,
        project_id=req.project_id,
        region_id=req.region_id,
    )

    # Save to session history
    response_text = result.get("Message", "") if isinstance(result, dict) else str(result)
    session.add_message("user", req.text)
    session.add_message("assistant", response_text)

    return result


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
