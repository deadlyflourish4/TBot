from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import (
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate
)
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


class RouterAgent:
    def __init__(self, system_prompt: str):
        # 1. Khởi tạo LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            google_api_key="AIzaSyBJQy05Kx09kMV384-dMxY6EPx-1H29vsY"
        )

        # 2. Prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{query}")
        ])

        # 3. Pipeline
        pipeline = prompt_template | self.llm

        # 4. Lưu history cho từng session
        self.chat_map = {}

        def get_chat_history(session_id: str) -> InMemoryChatMessageHistory:
            if session_id not in self.chat_map:
                self.chat_map[session_id] = InMemoryChatMessageHistory()
            return self.chat_map[session_id]

        # 5. Pipeline with memory
        self.pipeline_with_history = RunnableWithMessageHistory(
            pipeline,
            get_session_history=get_chat_history,
            input_messages_key="query",
            history_messages_key="history"
        )

    def route(self, session_id: str, query: str) -> str:
        """Phân loại câu hỏi thành sql | search | other."""
        response = self.pipeline_with_history.invoke(
            {"query": query},
            config={"configurable": {"session_id": session_id}}
        )

        route = response.content.strip().lower()

        # Bảo vệ output (chỉ nhận giá trị hợp lệ)
        if route not in ["sql", "search", "other"]:
            return "other"
        return route
