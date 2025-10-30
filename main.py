# ===== 1. Standard library imports =====
import io
import os
import uuid
from io import BytesIO
from os import getenv
from typing import Optional, List
from datetime import datetime

# ===== 2. Third-party imports =====
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends

from Security.middleware import jwt_middleware
from datetime import timedelta
from pydantic import BaseModel
from langdetect import detect
from deep_translator import GoogleTranslator
from PIL import Image
import edge_tts
from google import genai
from google.genai.types import GenerateContentConfig, Modality, Part, ImageConfig
from langdetect import detect
# ===== 3. Local project imports =====
from pipeline import GraphOrchestrator
# from Azure_blob.blob import AzureBlobUploader
from Chat.chatsession import ChatManager
from Database.db import MultiDBManager
from GCP.storage import GCStorage
from Security.middleware import jwt_middleware
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

security = HTTPBearer()
app = FastAPI(title="Orpheo Multi-Region API", swagger_ui_parameters={"persistAuthorization": True})
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
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
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
VOICES_CACHE = None
GCS_bucket = "guidepassasia_chatbot"
GCS_image = "guidepassasia_image_generation"
tts_buffers = {}

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
# ---------- TTS ----------
async def get_voice(lang_code: str) -> str:
    """
    Args:
        lang_code (str): The ISO language code (e.g., "en", "vi", "ja") used to 
            select the appropriate voice.

    Returns:
        str: The name of the selected Edge TTS voice.
    """
    global VOICES_CACHE
    if VOICES_CACHE is None:
        VOICES_CACHE = await edge_tts.list_voices()

    candidates = [v for v in VOICES_CACHE if v["Locale"].lower().startswith(lang_code.lower())]
    if not candidates:
        return "en-US-GuyNeural"
    male = [v for v in candidates if v.get("Gender", "").lower() == "male"]
    return (male[0]["Name"] if male else candidates[0]["Name"])

@app.post("/api/text-to-speech")
async def text_to_speech(req: TextRequest):
    """
    Generate text-to-speech (TTS) audio and upload to GCS.

    Args:
        req (TextRequest): Input containing 'text'.

    Returns:
        dict: JSON response with metadata and upload URL.
    """
    text = req.text.strip()
    if not text:
        return {"error": "Text cannot be empty"}
    if len(text) > 1000:
        return {"error": "Text too long (max 1000 chars)"}

    # Detect language and select voice
    lang_code = detect(text)
    voice = "en-US-JennyNeural"
    try:
        voices = await edge_tts.list_voices()
        candidates = [v for v in voices if v["Locale"].startswith(lang_code)]
        if candidates:
            voice = candidates[0]["Name"]
    except Exception:
        pass

    # Generate to memory buffer
    communicate = edge_tts.Communicate(text=text, voice=voice)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    buffer.seek(0)

    # Generate a globally unique file name
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    tts_id = uuid.uuid4().hex
    blob_name = f"tts/{timestamp}_{tts_id}.mp3"

    try:
        gcs_url = tts_storage.upload_blob_from_memory(GCS_bucket, buffer, blob_name)
    except Exception as e:
        return {"error": f"GCS upload failed: {str(e)}"}
    finally:
        buffer.close()

    return {
        "tts_id": tts_id[:8],  # short form for tracking
        "voice_used": voice,
        "language_detected": lang_code,
        "gcs_url": gcs_url,
        "message": "TTS successfully generated and uploaded to GCS."
    }

@app.post("/api/upload-tts")
async def upload_tts(gcs_url: str, upload: bool = True):
    """
    Upload or discard a previously generated text-to-speech (TTS) audio file.

    Args:
        gcs_url (str): The public URL of the file in GCS.
        upload (bool): If False, delete the file. If True, keep it.

    Returns:
        dict: JSON message about the result.
    """
    if not gcs_url:
        return {"error": "Missing gcs_url"}

    try:
        if not upload:
            # Discard (delete) the blob
            tts_storage.delete_blob(gcs_url)
            return {"message": f"TTS file deleted: {gcs_url}"}
        else:
            # No action needed — already uploaded
            return {
                "message": "TTS file retained successfully.",
                "public_url": gcs_url
            }

    except Exception as e:
        return {"error": f"Operation failed: {str(e)}"}

@app.post("/api/delete-tts")
def delete_tts(url: str = Body(..., embed=True)):
    try:
        result = tts_storage.delete_blob(url)
        return {"message": "Deleted successfully", "url": url, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        project_id = req.project_id,
        region_id=region_id,
    )

    session.add_message("user", req.text)
    # session.add_message("assistant", response_text)

    return response_text

@app.post("/api/generate-image")
def generate_image(
    req: ImageGenRequest
):
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

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./GCP/guidepassasiacloud-250f74bc75bb.json"
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

