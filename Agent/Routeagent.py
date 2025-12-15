from Agent.BaseAgent import BaseAgent
from Utils.SessionMemory import SessionMemory


class RouterAgent(BaseAgent):
    """
    RouterAgent:
      - Classifies user input into one of three routes:
          1. 'sql'    → internal database lookup
          2. 'search' → external web query
          3. 'other'  → small talk or unrecognized
      - Uses LLM for classification
      - Can infer route from short confirmations using memory
    """

    def __init__(
        self,
        system_prompt: str,
        memory: SessionMemory = None,
        model_name: str = "deepseek-r1:8b",
    ):
        super().__init__(
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=0,   # routing → deterministic
            memory=memory,
        )

    # ==========================================================
    def route(self, session_id: str, query: str) -> dict:
        """Run routing classifier and return routing decision."""
        try:
            route_text = self.run_llm(session_id, query)
            route = (route_text or "").strip().lower()

            # Normalize prefixes like "Route: SQL"
            for prefix in ["route:", "result:", "answer:", "type:"]:
                if route.startswith(prefix):
                    route = route.replace(prefix, "").strip()

            # Normalize routing keywords
            if any(k in route for k in ["sql", "database", "query"]):
                route = "sql"
            elif any(k in route for k in ["search", "web", "google"]):
                route = "search"
            else:
                # Handle short confirmations
                if route in ["yes", "ok", "okay", "sure", "yeah", "có", "dạ", "ừ"]:
                    route = self._infer_from_history(session_id)
                else:
                    route = "other"

            print(f"[ROUTER] ROUTE = {route.upper()}")

            return {
                "question_old": (
                    self.memory.get_history_list(session_id)
                    if self.memory
                    else [query]
                ),
                "message": f"Routed to {route.upper()} branch.",
                "audio": [],
                "location": {},
                "route": route,
            }

        except Exception as e:
            error_msg = f"Routing failed: {e}"
            return {
                "question_old": (
                    self.memory.get_history_list(session_id)
                    if self.memory
                    else [query]
                ),
                "message": error_msg,
                "audio": [],
                "location": {},
                "route": "other",
            }

    # ==========================================================
    def _infer_from_history(self, session_id: str) -> str:
        """
        Infer previous context when user replies with short confirmation
        (e.g., 'ok', 'có', 'ừ').
        """
        if not self.memory:
            return "other"

        session = self.memory.get(session_id)
        if not session or not session.messages:
            return "other"

        for msg in reversed(session.messages):
            if msg.type == "ai":
                content = msg.content.lower()
                if "sql" in content:
                    return "sql"
                if "search" in content:
                    return "search"

        return "other"
