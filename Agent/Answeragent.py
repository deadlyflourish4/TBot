from Agent.BaseAgent import BaseAgent
from Utils.SessionMemory import SessionMemory


class AnswerAgent(BaseAgent):
    """
    AnswerAgent:
      - Combines outputs from SQLAgent and SearchAgent
      - Generates natural, context-aware English answers
      - Uses shared SessionMemory for continuity
      - ALWAYS returns standardized JSON (NEVER None)
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
            temperature=0.3,
            memory=memory,
        )

    # ==========================================================
    def run(
        self,
        session_id: str,
        user_question: str,
        sql_query: str,
        query_result,
    ):
        """
        Generate clean, natural responses.
        GUARANTEE: always return dict.
        """

        # -------- Build augmented user prompt --------
        user_prompt = (
            f"User question: {user_question}\n"
            f"Executed SQL (if any): {sql_query or 'None'}\n"
            f"Query or Search result: {query_result or []}\n\n"
            "Generate a fluent, informative, and natural English response "
            "as a helpful travel guide. "
            "Avoid mentioning SQL, databases, or JSON explicitly."
        )

        # -------- Call LLM (SAFE) --------
        try:
            base_text = self.run_llm(session_id, user_prompt)
        except Exception as e:
            base_text = f"LLM error: {e}"

        # -------- HARD GUARANTEE TEXT --------
        if not base_text or not isinstance(base_text, str):
            base_text = "I couldn't generate a clear answer from the available information."

        # -------- Extract audio & location --------
        audios = []
        location_dict = {}

        if isinstance(query_result, list):
            for row in query_result:
                if not isinstance(row, dict):
                    continue

                # Audio / media URLs
                for k, v in row.items():
                    if (
                        isinstance(k, str)
                        and "mediaurl" in k.lower()
                        and v
                        and isinstance(v, (list, str))
                    ):
                        if isinstance(v, list):
                            audios.extend(v)
                        else:
                            audios.append(v)

                # Location mapping
                sub_id = row.get("subprojectid") or row.get("SubProjectID")
                loc_val = row.get("location") or row.get("Location")
                if sub_id and loc_val:
                    location_dict[str(sub_id)] = str(loc_val)

        # -------- FINAL GUARANTEED RETURN --------
        return self.format_json(
            question_old=[],
            message=base_text,
            audio=list(set(audios)),
            location=location_dict,
        )
