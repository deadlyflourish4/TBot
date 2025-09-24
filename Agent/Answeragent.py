from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import (
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate
)
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


class AnswerAgent:
    def __init__(self, system_prompt: str):
        # 1. Khởi tạo LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            google_api_key="AIzaSyBt7W0PFrh6q9v9lmljhldgoY0bx6pIRmY"

        )

        # 2. Prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template(
                "Câu hỏi gốc: {user_question}\n"
                "SQL đã chạy: {sql_query}\n"
                "Kết quả từ DB: {query_result}\n\n"
                "→ Viết câu trả lời tự nhiên:"
            ),
        ])

        pipeline = prompt_template | self.llm

        # 3. Lưu history riêng cho từng session
        self.chat_map = {}

        def get_chat_history(session_id: str) -> InMemoryChatMessageHistory:
            if session_id not in self.chat_map:
                self.chat_map[session_id] = InMemoryChatMessageHistory()
            return self.chat_map[session_id]

        # 4. Pipeline with memory
        self.pipeline_with_history = RunnableWithMessageHistory(
            pipeline,
            get_session_history=get_chat_history,
            input_messages_key="user_question",
            history_messages_key="history"
        )

    def get_answer(self, session_id: str, user_question: str, sql_query: str, query_result):
        """Tạo câu trả lời tự nhiên từ SQL output."""
        response = self.pipeline_with_history.invoke(
            {
                "user_question": user_question,
                "sql_query": sql_query,
                "query_result": query_result
            },
            config={"configurable": {"session_id": session_id}}
        )
        return response.content
