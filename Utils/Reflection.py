from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage


class Reflection:
    def __init__(self, llm, max_turns: int = 5):
        self.llm = llm
        self.max_turns = max_turns

    # --------------------------------------------------
    # Convert LangChain memory → prompt string
    # --------------------------------------------------
    def _format_from_session_memory(self, history: InMemoryChatMessageHistory) -> str:
        messages = history.messages[-self.max_turns * 2 :]
        lines = []

        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            lines.append(f"{role}: {msg.content}")

        return "\n".join(lines)

    # --------------------------------------------------
    # Main call
    # --------------------------------------------------
    def __call__(self, session_memory, session_id: str) -> str:
        history = session_memory.get(session_id)

        history_string = self._format_from_session_memory(history)

        system_prompt = """
Bạn là một module viết lại câu hỏi cho hệ thống RAG.

Nhiệm vụ:
- Dựa trên lịch sử hội thoại bên dưới
- Viết lại câu hỏi CUỐI CÙNG thành một câu hỏi ĐỘC LẬP, rõ nghĩa
- KHÔNG trả lời câu hỏi
- KHÔNG thêm thông tin mới
- Nếu câu hỏi đã độc lập, hãy giữ nguyên
""".strip()

        user_prompt = f"""
Lịch sử hội thoại:
{history_string}

Câu hỏi độc lập:
""".strip()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        completion = self.llm.invoke(messages)

        return completion.content.strip()
