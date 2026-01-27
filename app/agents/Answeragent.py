import json
import logging
import re
from typing import Any, Dict, List, Optional

from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

from agents.BaseAgent import BaseAgent
from utils.SessionMemory import SessionMemory

logger = logging.getLogger(__name__)

# Language display names
LANG_NAMES = {
    "vi": "tiếng Việt",
    "en": "English",
    "zh-cn": "中文",
    "zh-tw": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "th": "ภาษาไทย",
    "fr": "français",
}

# Google Translate language codes
TRANSLATE_CODES = {
    "vi": "vi",
    "en": "en",
    "zh-cn": "zh-cn",
    "zh-tw": "zh-tw",
    "ja": "ja",
    "ko": "ko",
    "th": "th",
    "fr": "fr",
}


class AnswerAgent(BaseAgent):
    """
    AnswerAgent: The Core Intelligence of the Travel Bot.
    Handles response synthesis with automatic language detection and translation.
    """

    def __init__(
        self,
        system_prompt: str = "",
        memory: Optional[SessionMemory] = None,
        model_name: str = "deepseek-r1:8b",
        temperature: float = 0.2,
    ):
        if not system_prompt:
            system_prompt = "You are a smart, friendly, and helpful AI Travel Guide."

        super().__init__(
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            memory=memory,
        )

    # =========================================================================
    # LANGUAGE DETECTION
    # =========================================================================
    def _detect_language(self, text: str) -> str:
        """Detect language of input text."""
        try:
            lang = detect(text)
            return lang
        except LangDetectException:
            return "vi"

    def _translate_to(self, text: str, target_lang: str) -> str:
        """Translate text to target language using Google Translate."""
        if not text or target_lang == "vi":
            return text

        try:
            target_code = TRANSLATE_CODES.get(target_lang, "en")
            translator = GoogleTranslator(source="vi", target=target_code)
            result = translator.translate(text)
            return result
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    # =========================================================================
    # SYNTHESIZE RESPONSE
    # =========================================================================
    def run_synthesizer(
        self, user_question: str, raw_data: Any, intent_label: str
    ) -> str:
        """
        Generate natural language response.
        1. Detect input language
        2. Generate response in Vietnamese (LLM works best)
        3. Translate to user's language if needed
        """
        # Detect user's language
        user_lang = self._detect_language(user_question)
        print(f"🌐 [LANG] Detected: {user_lang}")

        # Handle empty data
        if not raw_data or (isinstance(raw_data, dict) and raw_data.get("error")):
            error_msg = "Xin lỗi bạn, mình chưa tìm thấy thông tin về địa điểm này."
            if user_lang != "vi":
                error_msg = self._translate_to(error_msg, user_lang)
            return error_msg

        # Build prompt - always generate in Vietnamese first (best quality)
        prompt = f"""Bạn là hướng dẫn viên du lịch AI tên "T-Bot".
Chỉ dùng dữ liệu bên dưới để trả lời. Giữ câu trả lời ngắn gọn (2-4 câu).
Dùng giọng thân thiện với "dạ/ạ/nhé".

Câu hỏi: "{user_question}"
Intent: "{intent_label}"

Dữ liệu: {raw_data}

Trả lời:"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "Bạn là hướng dẫn viên du lịch. Trả lời bằng tiếng Việt.",
                },
                {"role": "user", "content": prompt},
            ]
            response = self.llm.invoke(messages)
            result = response.content.strip().strip('"')

            # Translate if user's language is not Vietnamese
            if user_lang != "vi":
                result = self._translate_to(result, user_lang)
                print(f"🌐 [TRANSLATE] Vietnamese → {user_lang}")

            return result

        except Exception as e:
            logger.error(f"Synthesizer error: {e}")
            return str(raw_data)

    # =========================================================================
    # LEGACY RUN
    # =========================================================================
    def run(self, prompt: str, *args, **kwargs):
        """Legacy wrapper method."""
        return self.llm.invoke(prompt).content
