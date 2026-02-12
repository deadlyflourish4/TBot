"""
TTS background tasks using Chatterbox TTS.
Supports 23 languages via ChatterboxMultilingualTTS.
"""
import io
import logging
import os
import time
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
# LOCAL STORAGE
# ========================================
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "tts")
os.makedirs(STORAGE_DIR, exist_ok=True)


def save_audio_local(audio_buffer: io.BytesIO, filename: str) -> dict:
    """Save WAV audio to local storage directory."""
    file_path = os.path.join(STORAGE_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(audio_buffer.read())

    file_id = filename.replace("tts_", "").replace(".wav", "")
    logger.info(f"Audio saved: {file_path}")

    return {
        "url": f"/storage/tts/{filename}",
        "file_id": file_id,
        "path": os.path.abspath(file_path),
    }


# ========================================
# CELERY TASKS
# ========================================

# Cache model in worker process to avoid reloading on every request
_model_cache = {}


def _get_model(device: str):
    """Load and cache ChatterboxMultilingualTTS model."""
    if "model" not in _model_cache:
        from chatterbox.tts import ChatterboxTTS
        logger.info(f"[Chatterbox] Loading model on {device} (first time)...")
        _model_cache["model"] = ChatterboxTTS.from_pretrained(device=device)
        logger.info("[Chatterbox] Model loaded and cached.")
    return _model_cache["model"]


@celery_app.task(bind=True, max_retries=3, time_limit=300)
def generate_tts(
    self,
    text: str,
    language_id: str = "en",
    audio_id: Optional[str] = None,
    audio_prompt_path: Optional[str] = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
) -> dict:
    """
    Generate TTS audio using Chatterbox and save locally.

    Args:
        text: Text to synthesize
        language_id: Language code (23 supported)
        audio_id: Custom audio ID (from C#), defaults to celery task id
        audio_prompt_path: Optional ~10s WAV for voice cloning
        exaggeration: Voice expressiveness 0.0-1.0
        cfg_weight: CFG guidance weight 0.0-1.0

    Returns:
        {"url": "...", "file_id": "...", "path": "...", "language": "...", "status": "completed"}
    """
    import torch
    import torchaudio as ta

    start = time.time()

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"[Chatterbox] lang={language_id}, device={device}, text_len={len(text)}")

        # Validate language
        if language_id not in LANGUAGE_MAP:
            logger.warning(f"Unsupported language '{language_id}', falling back to 'en'")
            language_id = "en"

        # Load model (cached in worker process)
        model = _get_model(device)

        # Build generate kwargs
        generate_kwargs = {
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
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

        # Save to local storage
        file_id = audio_id or self.request.id
        filename = f"tts_{file_id}.wav"
        save_result = save_audio_local(audio_buffer, filename)

        elapsed = round(time.time() - start, 2)
        logger.info(f"[Chatterbox] Done in {elapsed}s: {save_result['url']}")

        return {
            "url": save_result["url"],
            "file_id": save_result["file_id"],
            "path": save_result["path"],
            "task_id": self.request.id,
            "language": language_id,
            "duration_seconds": elapsed,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"[Chatterbox] TTS error: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_old_audio(max_age_hours: int = 24):
    """Delete TTS files older than max_age_hours from local storage."""
    import glob

    cutoff = time.time() - (max_age_hours * 3600)
    pattern = os.path.join(STORAGE_DIR, "tts_*.wav")
    deleted = 0

    for filepath in glob.glob(pattern):
        if os.path.getmtime(filepath) < cutoff:
            os.remove(filepath)
            deleted += 1

    logger.info(f"Cleanup: deleted {deleted} files older than {max_age_hours}h")
    return {"deleted": deleted}
