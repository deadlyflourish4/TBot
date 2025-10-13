from Agent.BaseAgent import BaseAgent
from Utils.SessionMemory import SessionMemory


class RouterAgent(BaseAgent):
    """
    RouterAgent:
      - Classifies user input into one of three routes:
          1. 'sql'    → internal database lookup
          2. 'search' → external web query
          3. 'other'  → small talk or unrecognized
      - Writes both user query and routing result into shared SessionMemory.
      - Returns unified JSON format for pipeline control.
    """

    def __init__(
        self,
        system_prompt: str,
        api_key: str,
        memory: SessionMemory = None,
    ):
        super().__init__(
            system_prompt=system_prompt,
            api_key=api_key,
            temperature=0,
            memory=memory,
        )

    def route(self, session_id: str, query: str) -> dict:
        """Run routing classifier and store result in memory."""
        try:
            # if self.memory:
            #     self.memory.append_user(session_id, query)

            # Run classifier model
            route_text = self.run_llm(session_id, query)
            route = (route_text or "").strip().lower()

            # Normalize prefixes like "Route: SQL"
            for prefix in ["route:", "result:", "answer:", "type:"]:
                if route.startswith(prefix):
                    route = route.replace(prefix, "").strip()

            # Basic route normalization
            if any(x in route for x in ["sql", "database", "query"]):
                route = "sql"
            elif any(x in route for x in ["search", "web", "google"]):
                route = "search"
            else:
                # Handle conversational confirmations
                if route in ["yes", "ok", "okay", "sure", "yeah", "có", "dạ", "ừ"]:
                    route = self._infer_from_history(session_id)
                else:
                    route = "other"

            # Log route decision into memory
            # if self.memory:
            #     self.memory.append_ai(session_id, f"[Routing] → {route.upper()}")

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
            # if self.memory:
            #     self.memory.append_ai(session_id, error_msg)

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

    def _infer_from_history(self, session_id: str) -> str:
        """Infer previous context when user only replies with short confirmation."""
        if not self.memory:
            return "other"

        history = self.memory.get(session_id).messages
        for msg in reversed(history):
            if msg.type == "ai":
                content = msg.content.lower()
                if "sql" in content:
                    return "sql"
                if "search" in content:
                    return "search"

        return "other"
