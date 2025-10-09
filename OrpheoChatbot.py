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
app = FastAPI(title="Minimal TTS API")

class TextRequest(BaseModel):
    text: str

async def get_voice(lang_code: str):
    voices = await edge_tts.list_voices()

    candidates = [v for v in voices if v["Locale"].startswith(lang_code)]
    if not candidates:
        return "en-US-GuyNeural"  

    male_voices = [v for v in candidates if v["Gender"].lower() == "male"]
    if male_voices:
        return male_voices[0]["Name"]

    return candidates[0]["Name"]

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
        text=text,
        voice=voice,
        rate="-5%",
        volume="+5%"
    )
    await communicate.save(filepath)

    return {
        "status": "success",
        "language_detected": lang_code,
        "voice_used": voice,
        "file_path": filepath,
    }

@app.post("/text-translate")
async def text_translate(text: TextRequest, target_lang: str = "en"):
    if not text.strip():
        return {"error": "Text cannot be empty"}
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return {
            "translated_text": translated,
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/chatbot-response")
async def chatbot_response(query: TextRequest):
    if not query.text.strip():
        return {"error": "Query cannot be empty"}
    try:
        response = bot.run(session_id="default", user_question=query.text)
        return response
    except Exception as e:
        return {"error": str(e)}