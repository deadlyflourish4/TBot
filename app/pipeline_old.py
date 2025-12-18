# pipeline.py
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langdetect import detect
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from Agent.SQLagent import SQLAgent
from Agent.Searchagent import SearchAgent
from Agent.Answeragent import AnswerAgent
from Agent.Routeagent import RouterAgent
from Database.db import MultiDBManager
from SystemPrompt.SQLprompt import sql_prompt
from SystemPrompt.Ansprompt import ans_prompt
from SystemPrompt.Routeprompt import route_prompt
from Utils.SessionMemory import SessionMemory


# ==========================================================
# DB Wrapper
# ==========================================================
class DBWrapper:
    def __init__(self, engine):
        self.engine = engine

    def run_query(self, sql: str):
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(r._mapping) for r in result]


# ==========================================================
# Graph State
# ==========================================================
class ChatState(TypedDict):
    session_id: str
    user_question: str
    user_location: str
    project_id: int
    region_id: int

    route: Optional[str]
    sql_result: Optional[dict]
    search_result: Optional[dict]
    final_output: Optional[dict]


# ==========================================================
# Graph Orchestrator (LangGraph)
# ==========================================================
class GraphOrchestrator:
    def __init__(self):
        self.memory = SessionMemory()
        self.db_manager = MultiDBManager()

        self.router_agent = RouterAgent(
            system_prompt=route_prompt,
            memory=self.memory,
        )

        self.search_agent = SearchAgent(
            system_prompt=None,
            memory=self.memory,
        )

        self.answer_agent = AnswerAgent(
            system_prompt=ans_prompt,
            memory=self.memory,
        )

        # -------- Build LangGraph --------
        graph = StateGraph(ChatState)

        graph.add_node("router", self.router_node)
        graph.add_node("sql", self.sql_node)
        graph.add_node("search", self.search_node)
        graph.add_node("answer", self.answer_node)

        graph.set_entry_point("router")

        graph.add_conditional_edges(
            "router",
            lambda s: s["route"],
            {
                "sql": "sql",
                "search": "search",
                "other": "answer",
            },
        )

        graph.add_edge("sql", "answer")
        graph.add_edge("search", "answer")
        graph.add_edge("answer", END)

        self.graph = graph.compile()

    # ======================================================
    # Router Node
    # ======================================================
    def router_node(self, state: ChatState) -> ChatState:
        res = self.router_agent.route(
            state["session_id"],
            state["user_question"]
        )
        state["route"] = res.get("route", "other")
        return state

    # ======================================================
    # SQL Node
    # ======================================================
    def sql_node(self, state: ChatState) -> ChatState:
        region_id = state["region_id"]
        project_id = state["project_id"]
        user_question = state["user_question"]
        user_location = state["user_location"]

        db_name = self.db_manager.DB_MAP[region_id]["prefix"]
        db_engine = self.db_manager.get_engine(region_id)
        db = DBWrapper(db_engine)

        lat, lon = None, None
        if user_location and "," in user_location:
            try:
                lat, lon = map(str.strip, user_location.split(","))
            except ValueError:
                pass

        sql_prompt_filled = (
            sql_prompt
            .replace("{DB_PREFIX}", db_name)
            .replace("{USER_LAT}", lat or "NULL")
            .replace("{USER_LON}", lon or "NULL")
            .replace("{ProjectID}", str(project_id))
        )

        sql_agent = SQLAgent(
            system_prompt=sql_prompt_filled,
            db=db,
            memory=self.memory,
        )

        try:
            sql_result = sql_agent.get_query(
                state["session_id"],
                user_question
            )
            state["sql_result"] = sql_result
            
            if not sql_result.get("db_result"):
                state["route"] = "search"

        except ProgrammingError:
            state["route"] = "search"

        return state

    # ======================================================
    # Search Node
    # ======================================================
    def search_node(self, state: ChatState) -> ChatState:
        state["search_result"] = self.search_agent.run(
            state["session_id"],
            state["user_question"]
        )
        return state

    # ======================================================
    # Answer Node
    # ======================================================
    def answer_node(self, state: ChatState) -> ChatState:
        session_id = state["session_id"]
        user_question = state["user_question"]

        try:
            lang_code = detect(user_question)
        except Exception:
            lang_code = "en"

        self.answer_agent.system_prompt = ans_prompt.replace(
            "{language}", lang_code
        )

        route = state["route"]

        if route == "sql" and state.get("sql_result"):
            answer = self.answer_agent.run(
                session_id=session_id,
                user_question=user_question,
                sql_query=state["sql_result"].get("sql_query"),
                query_result=state["sql_result"].get("db_result"),
            )

        elif route == "search" and state.get("search_result"):
            answer = self.answer_agent.run(
                session_id=session_id,
                user_question=user_question,
                sql_query="-- no SQL used --",
                query_result=state["search_result"].get("message"),
            )

        else:
            answer = self.answer_agent.run(
                session_id=session_id,
                user_question=user_question,
                sql_query="-- none --",
                query_result=user_question,
            )

        # ---- MEMORY WRITE (CHỈ Ở CUỐI) ----
        self.memory.append_user(session_id, user_question)
        self.memory.append_ai(session_id, answer.get("message"))

        answer["question_old"] = self.memory.get_history_list(session_id)
        state["final_output"] = answer
        return state

    # ======================================================
    # Run
    # ======================================================
    def run(
        self,
        session_id: str,
        user_question: str,
        user_location: str,
        project_id: int,
        region_id: int = 0,
    ) -> dict:

        session_key = f"{session_id}_region{region_id}"

        init_state: ChatState = {
            "session_id": session_key,
            "user_question": user_question,
            "user_location": user_location,
            "project_id": project_id,
            "region_id": region_id,
            "route": None,
            "sql_result": None,
            "search_result": None,
            "final_output": None,
        }

        result = self.graph.invoke(init_state)
        return result.get("final_output", {})
