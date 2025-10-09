from langchain_core.chat_history import InMemoryChatMessageHistory

class SessionMemory:
    """
    Shared session memory for all chatbot agents.
    Stores user–AI messages in memory for each session_id.
    Provides helper methods for retrieving chat history as LangChain objects or plain text.
    """

    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all(self):
        self.sessions.clear()
    # ==========================================================
    # Basic memory access
    # ==========================================================
    def get(self, session_id: str) -> InMemoryChatMessageHistory:
        """Return existing session history or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = InMemoryChatMessageHistory()
        return self.sessions[session_id]

    def append_user(self, session_id: str, message: str):
        """Append user message."""
        self.get(session_id).add_user_message(message)

    def append_ai(self, session_id: str, message: str):
        """Append assistant (AI) message."""
        self.get(session_id).add_ai_message(message)

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

    def clear(self, session_id: str):
        """Reset a session conversation."""
        if session_id in self.sessions:
            del self.sessions[session_id]
