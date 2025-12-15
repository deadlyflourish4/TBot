from Agent.BaseAgent import BaseAgent
from Database.db import MultiDBManager
from Utils.SessionMemory import SessionMemory


class SQLAgent(BaseAgent):
    """
    SQLAgent:
      - Converts natural language into SQL queries using LLM
      - Executes SQL safely via MultiDBManager
      - Returns structured results for downstream agents
    """

    def __init__(
        self,
        system_prompt: str,
        db: MultiDBManager,
        memory: SessionMemory = None,
        model_name: str = "deepseek-r1:8b",
    ):
        super().__init__(
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=0,      # SQL → deterministic
            memory=memory,
        )
        self.db = db

    # ======================================================
    def get_query(self, session_id: str, query: str) -> dict:
        """
        Generate SQL from natural language, execute it,
        and return results.
        """
        try:
            # 1️⃣ Generate SQL via LLM
            sql_text = self.run_llm(session_id, query)
            sql_text = self.clean_sql_code(sql_text)

            print("\n========== GENERATED SQL ==========")
            print(sql_text)
            print("===================================\n")

            queries = [q.strip() for q in sql_text.split(";") if q.strip()]

            if not queries:
                return {
                    "question": query,
                    "sql_query": None,
                    "db_result": [],
                }

            # 2️⃣ Execute SELECT queries only
            all_results = []
            for sql_cmd in queries:
                if not sql_cmd.upper().startswith("SELECT"):
                    continue

                try:
                    result = self.db.run_query(sql_cmd)
                    all_results.extend(result)
                except Exception as e:
                    all_results.append({
                        "error": str(e),
                        "sql": sql_cmd,
                    })
            print("\n[SQL_AGENT] DB RESULT:")
            print("ROWS =", len(all_results))
            for row in all_results[:5]:
                print(row)
            print("[SQL_AGENT] END RESULT\n")
            return {
                "question": query,
                "sql_query": sql_text,
                "db_result": all_results,
            }

        except Exception as e:
            return {
                "question": query,
                "sql_query": None,
                "db_result": [],
                "error": str(e),
            }
