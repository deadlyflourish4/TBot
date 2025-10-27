from Agent.BaseAgent import BaseAgent
# from ..Database.db import MultiDBManager
from Database.db import MultiDBManager
from Utils.SessionMemory import SessionMemory


class SQLAgent(BaseAgent):
    """
    SQLAgent:
      - Converts natural language into SQL queries using LLM.
      - Executes SQL safely via DatabaseConnector.
      - Logs all input/output to shared SessionMemory.
      - Returns structured data for downstream agents.
    """

    def __init__(
        self,
        system_prompt: str,
        db: MultiDBManager,
        api_key: str,
        memory: SessionMemory = None,
    ):
        super().__init__(
            system_prompt=system_prompt,
            api_key=api_key,
            temperature=0,
            memory=memory,
        )
        self.db = db

    def get_query(self, session_id: str, query: str) -> dict:
        """Generate, execute, and return SQL query results."""
        try:
            # if self.memory:
            #     self.memory.append_user(session_id, query)

            sql_text = self.run_llm(session_id, query)
            sql_text = self.clean_sql_code(sql_text)

            queries = [q.strip() for q in sql_text.split(";") if q.strip()]
            if not queries:
                # if self.memory:
                #     self.memory.append_ai(session_id, "[No valid SQL generated]")
                return {"question": query, "sql_query": None, "db_result": []}

            all_results = []
            for sql_cmd in queries:
                if not sql_cmd.upper().startswith("SELECT"):
                    continue
                try:
                    result = self.db.run_query(sql_cmd)
                    all_results.extend(result)
                except Exception as e:
                    all_results.append({"error": str(e), "sql": sql_cmd})

            # if self.memory:
            #     self.memory.append_ai(session_id, f"[SQL executed]\n{sql_text}")

            return {
                "question": query,
                "sql_query": sql_text,
                "db_result": all_results,
            }

        except Exception as e:
            # if self.memory:
            #     self.memory.append_ai(session_id, f"[SQLAgent Error] {str(e)}")
            return {
                "question": query,
                "sql_query": None,
                "db_result": [],
                "error": str(e),
            }
