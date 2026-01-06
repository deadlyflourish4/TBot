import logging
import re
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    BaseAgent using LangChain + Ollama
    (Compatible with LangGraph)
    """

    def __init__(
        self,
        system_prompt: str,
        model_name: str = "qwen2.5:3b",  # Lighter model for faster inference
        temperature: float = 0.2,
        memory=None,
    ):
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.memory = memory

        self.llm = ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL"),
        )

    # ==========================================================
    # LLM RUNNER
    # ==========================================================
    def run_llm(self, session_id: str, query: str) -> str:
        messages = []

        # System
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        # History (giữ đúng logic bạn đang làm)
        if self.memory:
            session = self.memory.get(session_id)
            if session and hasattr(session, "messages"):
                for m in session.messages:
                    if m.type == "human":
                        messages.append(HumanMessage(content=m.content))
                    else:
                        messages.append(AIMessage(content=m.content))

        # Current query
        messages.append(HumanMessage(content=query))

        try:
            resp = self.llm.invoke(messages)
            text = (resp.content or "").strip()

            if self.memory:
                self.memory.append_ai(session_id, text)

            return text

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"[Error calling LLM: {e}]"

    # ==========================================================
    # SQL CLEANER (GIỮ NGUYÊN)
    # ==========================================================
    def clean_sql_code(self, sql_code: str) -> str:
        if not sql_code:
            return ""

        match = re.search(
            r"```sql\s*(.*?)\s*```", sql_code, flags=re.IGNORECASE | re.DOTALL
        )
        if match:
            return match.group(1).strip()

        sql_code = re.sub(r"```.*?```", "", sql_code, flags=re.DOTALL)
        sql_code = re.sub(r"^\s*sql\s*\n", "", sql_code, flags=re.IGNORECASE)
        return sql_code.strip()

    # ==========================================================
    # OUTPUT FORMAT (GIỮ NGUYÊN)
    # ==========================================================
    def format_json(self, question_old, message: str, audio=None, location=None):
        return {
            "question_old": question_old or [],
            "message": (message or "").strip(),
            "audio": audio or [],
            "location": location or {},
        }
