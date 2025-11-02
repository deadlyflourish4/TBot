from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate,
)
from Agent.BaseAgent import BaseAgent
from Utils.SessionMemory import SessionMemory

class AnswerAgent(BaseAgent):
    """
    AnswerAgent:
      - Combines outputs from SQLAgent and SearchAgent.
      - Generates natural, context-aware English answers.
      - Uses shared SessionMemory for continuity.
      - Returns standardized JSON:
        {
          "question_old": [<history>],
          "message": <AI text>,
          "audio": [<audio URLs>],
          "location": {<SubProjectID>: "lat,long"}
        }
    """

    def __init__(self, system_prompt: str, api_key: str, memory: SessionMemory = None):
        super().__init__(system_prompt, api_key, temperature=0.3, memory=memory)

        # Build contextual LLM pipeline
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template(
                    "User question: {user_question}\n"
                    "Executed SQL (if any): {sql_query}\n"
                    "Query or Search result: {query_result}\n\n"
                    "Generate a fluent, informative, and natural English response "
                    "as a helpful travel guide. Avoid mentioning SQL or JSON explicitly."
                ),
            ]
        )
        self.pipeline = self.prompt_template | self.llm

    # ==========================================================
    def run(
        self,
        session_id: str,
        user_question: str,
        sql_query: str,
        query_result,
    ):
        """
        Generate clean, natural responses and update shared session memory.
        """
        # Record user query in session
        # if self.memory:
        #     self.memory.append_user(session_id, user_question)

        # Build context for LLM
        history_msgs = (
            self.memory.get(session_id).messages if self.memory else []
        )
        response = self.pipeline.invoke(
            {
                "user_question": user_question,
                "sql_query": sql_query or "None",
                "query_result": query_result or [],
                "history": history_msgs,
            }
        )
        base_text = (response.content or "").strip()

        # Log AI response back to memory
        # if self.memory:
        #     self.memory.append_ai(session_id, base_text)

        # Extract potential audio & location data
        audios = ""
        location_dict = {}

        if isinstance(query_result, list):
            for row in query_result:
                if not isinstance(row, dict):
                    continue
                # Extract media/audio URLs
                for k, v in row.items():
                    if "mediaurl" in k.lower() and v and "EN" in v:
                        audios = v
                # Extract location fields
                sub_id = row.get("subprojectid") or row.get("SubProjectID")
                loc_val = row.get("location") or row.get("Location")
                if sub_id and loc_val:
                    location_dict[str(sub_id)] = str(loc_val)

        # Return final unified structure
        return self.format_json(
            question_old=self.memory.get_history_list(session_id)
            if self.memory
            else [user_question],
            message=base_text,
            audio=list(set(audios)),
            location=location_dict,
        )
