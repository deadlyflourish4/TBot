import json
import logging
import re
from typing import Any, Dict, List, Optional

from langdetect import detect, LangDetectException

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


class AnswerAgent(BaseAgent):
    """
    AnswerAgent: The Core Intelligence of the Travel Bot.
    Handles response synthesis with automatic language detection.
    """

    def __init__(
        self,
        system_prompt: str = "",
        memory: Optional[SessionMemory] = None,
        model_name: str = "qwen2.5:7b",  # Faster than gpt-oss:20b
        temperature: float = 0.3,
    ):
        if not system_prompt:
            system_prompt = (
                "You are a smart, friendly, and helpful AI Travel Guide. "
                "Respond in the same language as the user's question."
            )

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
            logger.debug(f"Detected language: {lang}")
            return lang
        except LangDetectException:
            return "vi"  # default to Vietnamese

    # =========================================================================
    # SYNTHESIZE RESPONSE
    # =========================================================================
    def run_synthesizer(
        self, user_question: str, raw_data: Any, intent_label: str
    ) -> str:
        """
        Generate natural language response.
        Auto-detects input language and responds in the same language.
        """
        # Detect user's language
        user_lang = self._detect_language(user_question)
        lang_name = LANG_NAMES.get(user_lang, user_lang)

        # Handle empty data
        if not raw_data or (isinstance(raw_data, dict) and raw_data.get("error")):
            if user_lang == "en":
                return "Sorry, I couldn't find detailed information about this location. Please try another place!"
            return "Xin lỗi bạn, mình chưa tìm thấy thông tin về địa điểm này. Bạn thử hỏi địa điểm khác nhé!"

        # Build prompt with dynamic language
        prompt = f"""
You are an AI travel guide named "T-Bot".
Use ONLY the data provided below to answer.

[RESPONSE LANGUAGE]
- You MUST respond in {lang_name} ({user_lang})
- If Vietnamese: use friendly tone (dạ/ạ/nhé)
- For other languages: use polite, professional tone

[CONTEXT]
- User question: "{user_question}"
- Intent: "{intent_label}"

[RULES]
- Keep response to 2-4 sentences
- Do not add information outside the DATA
- direction: describe location briefly
- media: say "I'll play the media for you"
- info: summarize 2-3 key points
- chitchat: brief social response

[DATA]: {raw_data}
"""

        try:
            messages = [
                {"role": "system", "content": f"You are a travel assistant. Respond in {lang_name}."},
                {"role": "user", "content": prompt},
            ]
            response = self.llm.invoke(messages)
            return response.content.strip().strip('"')

        except Exception as e:
            logger.error(f"Synthesizer error: {e}")
            return str(raw_data)

    # =========================================================================
    # LEGACY RUN
    # =========================================================================
    def run(self, prompt: str, *args, **kwargs):
        """Legacy wrapper method."""
        return self.llm.invoke(prompt).content
