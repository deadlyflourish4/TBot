from langchain_core.chat_history import InMemoryChatMessageHistory
from collections import defaultdict
from typing import Any


class SessionMemory:
    """
    Session-scoped memory:
    - Chat history (LangChain compatible)
    - Routing / context memory (intent, target_place, ...)
    """

    def __init__(self, max_turns: int = 5):
        self.sessions = {}
        self.context = defaultdict(dict)
        self.max_turns = max_turns

    # ==========================================================
    # CHAT MEMORY (GIỮ NGUYÊN)
    # ==========================================================
    def get(self, session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in self.sessions:
            self.sessions[session_id] = InMemoryChatMessageHistory()
        return self.sessions[session_id]

    def _trim_history(self, session_id: str):
        history = self.get(session_id).messages
        max_messages = self.max_turns * 2
        if len(history) > max_messages:
            self.sessions[session_id].messages = history[-max_messages:]

    def append_user(self, session_id: str, message: str):
        self.get(session_id).add_user_message(message)
        self._trim_history(session_id)

    def append_ai(self, session_id: str, message: str):
        self.get(session_id).add_ai_message(message)
        self._trim_history(session_id)

    def get_history_list(self, session_id: str):
        history = self.get(session_id).messages
        formatted = []
        for msg in history:
            role = "user" if msg.type == "human" else "ai"
            formatted.append(f"{role}: {msg.content}")
        return formatted

    # ==========================================================
    # CONTEXT MEMORY (MỚI – RẤT QUAN TRỌNG)
    # ==========================================================
    def set_ctx(self, session_id: str, key: str, value: Any):
        self.context[session_id][key] = value

    def get_ctx(self, session_id: str, key: str, default=None):
        return self.context[session_id].get(key, default)

    def clear_ctx(self, session_id: str):
        self.context.pop(session_id, None)

    # ==========================================================
    # MAINTENANCE
    # ==========================================================
    def clear(self, session_id: str):
        self.sessions.pop(session_id, None)
        self.context.pop(session_id, None)

    def clear_all(self):
        self.sessions.clear()
        self.context.clear()
