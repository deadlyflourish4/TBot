from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate,
)


class BaseAgent:
    """
    Base class for all chatbot agents.

    Responsibilities:
    - Initialize LLM (Google Gemini)
    - Integrate with shared SessionMemory (conversation persistence)
    - Manage prompt construction (system + history + user)
    - Provide unified output JSON format for downstream components
    """

    def __init__(
        self,
        system_prompt: str,
        api_key: str,
        temperature: float = 0.2,
        memory=None,
    ):
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.memory = memory  # shared SessionMemory instance

        # Initialize Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=temperature,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            google_api_key=api_key,
        )

        # Define base prompt template (system → history → user)
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template("{query}"),
            ]
        )

        # Create LLM pipeline
        self.pipeline = self.prompt_template | self.llm

    # ==========================================================
    # LLM RUNNER
    # ==========================================================

    def run_llm(self, session_id: str, query: str) -> str:
        """
        Run LLM with global session memory.

        - Appends user + assistant messages to SessionMemory
        - Retrieves previous conversation context for continuity
        """
        # Record user query
        # if self.memory:
        #     self.memory.append_user(session_id, query)

        # Retrieve full chat history for context
        history_msgs = []
        if self.memory:
            session = self.memory.get(session_id)
            if session and hasattr(session, "messages"):
                history_msgs = session.messages

        # Generate response
        try:
            response = self.pipeline.invoke({"query": query, "history": history_msgs})
            text = (response.content or "").strip()
        except Exception as e:
            text = f"[Error calling LLM: {e}]"

        # Append assistant response
        # if self.memory:
        #     self.memory.append_ai(session_id, text)

        return text

    # ==========================================================
    # SQL CLEANER
    # ==========================================================

    def clean_sql_code(self, sql_code: str) -> str:
        """
        Remove markdown fences and whitespace to get raw SQL string.
        """
        if not sql_code:
            return ""
        sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
        if sql_code.lower().startswith("sql\n"):
            sql_code = sql_code.split("\n", 1)[1].strip()
        return sql_code.strip()

    # ==========================================================
    # STANDARDIZED JSON OUTPUT
    # ==========================================================

    def format_json(self, question_old, message: str, audio=None, location=None):
        """
        Unified output schema for frontend API.

        Example:
        {
            "question_old": [...],
            "message": "Assistant response text",
            "audio": [...],
            "location": {...}
        }
        """
        return {
            "question_old": question_old or [],
            "message": (message or "").strip(),
            "audio": audio or [],
            "location": location or {},
        }
