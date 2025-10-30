from langchain_core.chat_history import InMemoryChatMessageHistory

class SessionMemory:
    """
    Shared session memory for all chatbot agents.
    Stores user–AI messages in memory for each session_id.
    Keeps only the last N messages (short-term memory).
    """

    def __init__(self, max_turns: int = 5):
        self.sessions = {}
        self.max_turns = max_turns  # số lượt user–AI muốn giữ lại

    # ==========================================================
    # Basic memory access
    # ==========================================================
    def get(self, session_id: str) -> InMemoryChatMessageHistory:
        """Return existing session history or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = InMemoryChatMessageHistory()
        return self.sessions[session_id]

    def _trim_history(self, session_id: str):
        """Cắt bớt lịch sử để chỉ giữ lại 5 lượt gần nhất."""
        history = self.get(session_id).messages
        # Mỗi lượt gồm 2 message (user + ai)
        max_messages = self.max_turns * 2
        if len(history) > max_messages:
            # Giữ lại phần cuối
            self.sessions[session_id].messages = history[-max_messages:]

    def append_user(self, session_id: str, message: str):
        """Append user message."""
        self.get(session_id).add_user_message(message)
        self._trim_history(session_id)

    def append_ai(self, session_id: str, message: str):
        """Append assistant (AI) message."""
        self.get(session_id).add_ai_message(message)
        self._trim_history(session_id)

    # ==========================================================
    # Export helpers
    # ==========================================================
    def get_history_list(self, session_id: str):
        """
        Return chat history as a plain list of strings.
        Example:
            ["user: Hello", "ai: Hi there!", "user: Show me POI 101"]
        """
        history = self.get(session_id).messages
        formatted = []
        for msg in history:
            role = "user" if msg.type == "human" else "ai"
            formatted.append(f"{role}: {msg.content}")
        return formatted

    # ==========================================================
    # Maintenance
    # ==========================================================
    def clear(self, session_id: str):
        """Reset a session conversation."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all(self):
        """Delete all sessions."""
        self.sessions.clear()
