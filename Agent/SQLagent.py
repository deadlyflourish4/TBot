from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import (
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate
)
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from Database.db import DatabaseConnector

class SQLAgent:
    def __init__(self, system_prompt: str, db: DatabaseConnector):
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
            HumanMessagePromptTemplate.from_template("{query}"),
        ])

        # 3. Pipeline
        pipeline = prompt_template | self.llm

        # 4. Lưu history riêng cho từng session
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

        self.db = db

    def get_query(self, session_id: str, query: str):
            """Sinh SQL từ LLM, chạy DB, trả kết quả."""
            response = self.pipeline_with_history.invoke(
                {"query": query},
                config={"configurable": {"session_id": session_id}}
            )

            sql_code = response.content.strip()

            # Làm sạch nếu có Markdown code block
            if sql_code.startswith("```"):
                sql_code = sql_code.strip("`")       # bỏ toàn bộ backticks
                sql_code = sql_code.replace("sql\n", "", 1).replace("sql\r\n", "", 1)  # bỏ chữ sql đầu block

            # Nếu không có SELECT thì coi như fail
            if "SELECT" not in sql_code.upper():
                return {"sql": sql_code, "result": "❌ Không sinh được SQL hợp lệ"}

            # Chạy query
            result = self.db.run_query(sql_code)
            return {"sql": sql_code, "result": result}
