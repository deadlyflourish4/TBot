from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
import uuid

import edge_tts
from langdetect import detect
from deep_translator import GoogleTranslator
from os import getenv
import os

from pipeline import GraphOrchestrator
# from Azure_blob.blob import AzureBlobUploader
from Chat.chatsession import ChatManager
from Database.db import MultiDBManager
from GCP.storage import GCStorage

app = FastAPI(title="Orpheo Multi-Region API")

# --- deps ---
bot = GraphOrchestrator()
# BLOB_UPLOADER = AzureBlobUploader(
#     connection_string=getenv("BLOB_CONNECTION_STRING"),
#     container_name="tts-audio"
# )
db_manager = MultiDBManager()
chat_sessions = ChatManager(db_manager=db_manager, session_timeout=1800)
tts_storage = GCStorage(credentials_path="./GCP/rare-karma-468001-k3-a7efcf8a7c80.json")

# --- cache voices ---
VOICES_CACHE = None

# ---------- MODELS ----------
class TextRequest(BaseModel):
    text: str

class ChatRequest(BaseModel):
    text: str
    region_id: int
    session_id: str = None


# ---------- TTS ----------
async def get_voice(lang_code: str) -> str:
    global VOICES_CACHE
    if VOICES_CACHE is None:
        VOICES_CACHE = await edge_tts.list_voices()

    candidates = [v for v in VOICES_CACHE if v["Locale"].lower().startswith(lang_code.lower())]
    if not candidates:
        return "en-US-GuyNeural"
    male = [v for v in candidates if v.get("Gender", "").lower() == "male"]
    return (male[0]["Name"] if male else candidates[0]["Name"])

@app.post("/text-to-speech")
async def text_to_speech(req: TextRequest):
    text = req.text.strip()
    if not text:
        return {"error": "Text cannot be empty"}
    if len(text) > 1000:
        return {"error": "Text too long (max 1000 chars)"}

    # Detect language and choose voice
    lang_code = detect(text)
    voice = f"en-US-JennyNeural"  # fallback default
    try:
        voices = await edge_tts.list_voices()
        candidates = [v for v in voices if v["Locale"].startswith(lang_code)]
        if candidates:
            voice = candidates[0]["Name"]
    except Exception:
        pass

    # Prepare file path
    os.makedirs("outputs", exist_ok=True)
    filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join("outputs", filename)

    # Generate TTS to file
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="-5%",
        volume="+5%",
    )
    await communicate.save(filepath)
    print(filepath)
    return {
        "language_detected": lang_code,
        "voice_used": voice,
        "file_path": filepath,
    }

@app.post("/save-tts")
def save_tts(file_path):
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    try:
        url = tts_storage.upload_blob("tts-script", file_path)
        os.remove(file_path)

        return {
            "url": url
        }
    except Exception as e:
        return {
            "message": str(e)
        }
    
@app.post("/delete-tts")
def delete_tts(url):
    try:
        url = tts_storage.delete_blob(url)

        return {
            "url": url
        }
    except Exception as e:
        return {
            "message": str(e)
        }
    
# ---------- TRANSLATE ----------
@app.post("/text-translate")
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
@app.post("/chatbot-response")
async def chatbot_response(req: ChatRequest):
    session_id = req.session_id
    session = chat_sessions.get_session(session_id) if session_id else None

    if not session:
        session = chat_sessions.create_session(req.region_id, session_id=session_id)
        session_id = session.session_id
        
    region_id = session.region_id

    response_text = bot.run(
        session_id=session_id,
        user_question=req.text,
        region_id=region_id,
    )

    session.add_message("user", req.text)
    session.add_message("assistant", response_text)

    return response_text