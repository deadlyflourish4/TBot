"""
TTS background tasks using Chatterbox TTS.
Supports 23 languages via ChatterboxMultilingualTTS.
"""
import io
import logging
import os
from typing import Optional

from tasks import celery_app

logger = logging.getLogger(__name__)

# ========================================
# 23 SUPPORTED LANGUAGES
# ========================================
LANGUAGE_MAP = {
    "ar": "Arabic",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fi": "Finnish",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "nl": "Dutch",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "sv": "Swedish",
    "sw": "Swahili",
    "tr": "Turkish",
    "zh": "Chinese",
}


# ========================================
# TODO: CONFIGURE EXTERNAL UPLOAD API
# ========================================
# Bạn cần điền thông tin API upload từ backend:
#
# UPLOAD_API_URL = "https://your-backend.com/api/upload-audio"
# UPLOAD_API_KEY = os.getenv("UPLOAD_API_KEY", "")
#
# Ví dụ curl mà backend cung cấp:
# curl -X POST https://your-backend.com/api/upload-audio \
#   -H "Authorization: Bearer YOUR_API_KEY" \
#   -F "file=@audio.wav" \
#   -F "filename=tts_abc123.wav"
#
# Response expected:
# {"url": "https://cdn.example.com/audio/tts_abc123.wav", "file_id": "abc123"}
# ========================================

UPLOAD_API_URL = os.getenv("TTS_UPLOAD_API_URL", "")
UPLOAD_API_KEY = os.getenv("TTS_UPLOAD_API_KEY", "")


def upload_audio_to_backend(audio_buffer: io.BytesIO, filename: str) -> dict:
    """
    Upload audio file to external backend API.
    
    TODO: Implement this function based on your backend API spec.
    
    Args:
        audio_buffer: BytesIO containing WAV audio data
        filename: Suggested filename (e.g., "tts_abc123.wav")
        
    Returns:
        {"url": "https://...", "file_id": "..."}
        
    Example implementation for multipart upload:
    
    >>> import requests
    >>> response = requests.post(
    >>>     UPLOAD_API_URL,
    >>>     headers={"Authorization": f"Bearer {UPLOAD_API_KEY}"},
    >>>     files={"file": (filename, audio_buffer, "audio/wav")},
    >>> )
    >>> return response.json()
    """
    import requests
    
    if not UPLOAD_API_URL:
        raise ValueError(
            "TTS_UPLOAD_API_URL not configured. "
            "Set environment variable or update UPLOAD_API_URL in tts_tasks.py"
        )
    
    # TODO: Modify this based on your backend API format
    response = requests.post(
        UPLOAD_API_URL,
        headers={
            "Authorization": f"Bearer {UPLOAD_API_KEY}" if UPLOAD_API_KEY else None,
            # Add other headers as needed
        },
        files={
            "file": (filename, audio_buffer, "audio/wav"),
        },
        # Or use JSON body:
        # json={"filename": filename, "data": base64.b64encode(audio_buffer.read()).decode()}
    )
    
    response.raise_for_status()
    return response.json()


@celery_app.task(bind=True, max_retries=3, time_limit=180)
def generate_tts(
    self,
    text: str,
    language_id: str = "en",
    audio_prompt_path: Optional[str] = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
) -> dict:
    """
    Generate TTS using ChatterboxMultilingualTTS and upload to backend.
    
    Args:
        text: Text to synthesize (max 1000 chars)
        language_id: Language code (ar, da, de, el, en, es, fi, fr, he, hi,
                     it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh)
        audio_prompt_path: Optional ~10s WAV for voice cloning
        exaggeration: Expressiveness 0.0-1.0 (default 0.5)
            - 0.5: Normal/neutral
            - 0.7+: More dramatic/expressive
        cfg_weight: CFG weight 0.0-1.0 (default 0.5)
            - 0.5: Balanced
            - 0.3: More expressive, slower
            - 0.0: Language transfer mode
        
    Returns:
        {"url": "...", "task_id": "...", "language": "...", "status": "completed"}
    """
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"[Chatterbox] lang={language_id}, device={device}, text_len={len(text)}")
        
        # Validate language
        if language_id not in LANGUAGE_MAP:
            logger.warning(f"Unsupported language '{language_id}', falling back to 'en'")
            language_id = "en"
        
        # Load model (cached after first call)
        model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        
        # Build generate kwargs
        generate_kwargs = {
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "language_id": language_id,
        }
        
        # Voice cloning (optional)
        if audio_prompt_path and os.path.exists(audio_prompt_path):
            generate_kwargs["audio_prompt_path"] = audio_prompt_path
            logger.info(f"[Chatterbox] Using voice clone from: {audio_prompt_path}")
        
        # Generate audio
        wav = model.generate(text, **generate_kwargs)
        
        # Save to buffer
        audio_buffer = io.BytesIO()
        ta.save(audio_buffer, wav, model.sr, format="wav")
        audio_buffer.seek(0)
        
        # Upload to backend
        filename = f"tts_{self.request.id}.wav"
        upload_result = upload_audio_to_backend(audio_buffer, filename)
        
        logger.info(f"[Chatterbox] Upload success: {upload_result}")
        
        return {
            "url": upload_result.get("url"),
            "file_id": upload_result.get("file_id"),
            "task_id": self.request.id,
            "language": language_id,
            "status": "completed",
        }
        
    except Exception as e:
        logger.error(f"[Chatterbox] TTS error: {e}", exc_info=True)
        self.retry(exc=e, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_old_audio(max_age_hours: int = 24):
    """
    Delete old TTS files.
    TODO: Implement based on your storage backend.
    """
    logger.info(f"Cleanup task called with max_age_hours={max_age_hours}")
    # TODO: Call backend API to cleanup old files if needed
    return {"status": "not_implemented"}
