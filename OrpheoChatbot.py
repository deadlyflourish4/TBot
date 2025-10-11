from fastapi import FastAPI
from pydantic import BaseModel
import edge_tts
import asyncio
import os
import uuid
from langdetect import detect
from deep_translator import GoogleTranslator
from .pipeline import GraphOrchestrator

bot = GraphOrchestrator()
app = FastAPI(title="Orpheo Multi-Region API")


# ---------- MODELS ----------
class TextRequest(BaseModel):
    text: str

class ChatRequest(BaseModel):
    text: str
    session_id: str = "default"
    region_id: int = 0


# ---------- TTS ----------
async def get_voice(lang_code: str):
    voices = await edge_tts.list_voices()
    candidates = [v for v in voices if v["Locale"].startswith(lang_code)]
    if not candidates:
        return "en-US-GuyNeural"
    male_voices = [v for v in candidates if v["Gender"].lower() == "male"]
    return male_voices[0]["Name"] if male_voices else candidates[0]["Name"]

@app.post("/text-to-speech")
async def text_to_speech(req: TextRequest):
    text = req.text.strip()
    if not text:
        return {"error": "Text cannot be empty"}

    lang_code = detect(text)
    voice = await get_voice(lang_code)

    os.makedirs("outputs", exist_ok=True)
    filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join("outputs", filename)

    communicate = edge_tts.Communicate(
        text=text, voice=voice, rate="-5%", volume="+5%"
    )
    await communicate.save(filepath)

    return {
        "status": "success",
        "language_detected": lang_code,
        "voice_used": voice,
        "file_path": filepath,
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
        return {"error": str(e)}


# ---------- CHATBOT ----------
@app.post("/chatbot-response")
async def chatbot_response(req: ChatRequest):
    text = req.text.strip()
    if not text:
        return {"error": "Query cannot be empty"}

    try:
        response = bot.run(
            session_id=req.session_id,
            user_question=text,
            region_id=req.region_id
        )
        return response
    except Exception as e:
        return {"error": str(e)}
