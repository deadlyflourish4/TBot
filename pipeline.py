# pipeline.py
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .Agent.SQLagent import SQLAgent
from .Agent.Searchagent import SearchAgent
from .Agent.Answeragent import AnswerAgent
from .Agent.Routeagent import RouterAgent
from .Database.db import MultiDBManager
from .SystemPrompt.SQLprompt import sql_prompt
from .SystemPrompt.Ansprompt import ans_prompt
from .SystemPrompt.Routeprompt import route_prompt
from .Utils.SessionMemory import SessionMemory
from sqlalchemy import text

class DBWrapper:
    """Gói SQLAlchemy engine thành interface có run_query()"""
    def __init__(self, engine):
        self.engine = engine

    def run_query(self, sql: str):
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(r._mapping) for r in result]

# def get_sql_by_region(db_name:str):

class ChatState(TypedDict):
    session_id: str
    user_question: str
    route: str
    region_id: int
    sql_result: Optional[dict]
    search_result: Optional[dict]
    answer_result: Optional[dict]
    final_output: Optional[dict]


class GraphOrchestrator:
    """Orchestrator chính, multi-region + multi-session."""

    def __init__(self):
        self.memory = SessionMemory()
        self.api_key = "AIzaSyB6l_kooxHVkG2EWKI823wEMXEa_1A5lxY"
        self.db_manager = MultiDBManager()

        # Agents không phụ thuộc DB
        self.search_agent = SearchAgent(system_prompt=None, api_key=self.api_key, memory=self.memory)
        self.answer_agent = AnswerAgent(system_prompt=ans_prompt, api_key=self.api_key, memory=self.memory)
        self.router_agent = RouterAgent(system_prompt=route_prompt, api_key=self.api_key, memory=self.memory)

        # Build graph
        graph = StateGraph(ChatState)
        graph.add_node("router", self.router_node)
        graph.add_node("sql", self.sql_node)
        graph.add_node("search", self.search_node)
        graph.add_node("other", self.other_node)
        graph.add_node("answer", self.answer_node)

        graph.set_entry_point("router")
        graph.add_conditional_edges(
            "router",
            lambda s: s["route"],
            {"sql": "sql", "search": "search", "other": "other"},
        )
        graph.add_edge("sql", "answer")
        graph.add_edge("search", "answer")
        graph.add_edge("other", "answer")
        graph.add_edge("answer", END)
        self.compiled_graph = graph.compile()

    # ========== Node logic ==========

    def router_node(self, state: ChatState) -> ChatState:
        res = self.router_agent.route(state["session_id"], state["user_question"])
        route = res.get("route", "other").strip().lower()
        state["route"] = route
        return state

    def sql_node(self, state: ChatState) -> ChatState:
        region_id = state.get("region_id", 0)
        db_name = self.db_manager.DB_MAP[region_id]["prefix"]
        new_sql_prompt = sql_prompt.replace("{DB_PREFIX}", db_name)

        db_engine = self.db_manager.get_engine(region_id)
        db = DBWrapper(db_engine)

        sql_agent = SQLAgent(system_prompt=new_sql_prompt, db=db, api_key=self.api_key, memory=self.memory)
        result = sql_agent.get_query(state["session_id"], state["user_question"])

        print(f"[SQL_NODE] Region={region_id} | SQL={result.get('sql_query')}")
        print(f"[SQL_NODE] Rows={len(result.get('db_result', []))}")

        state["sql_result"] = result
        return state


    def search_node(self, state: ChatState) -> ChatState:
        result = self.search_agent.run(state["session_id"], state["user_question"])
        state["search_result"] = result
        return state

    def other_node(self, state: ChatState) -> ChatState:
        answer = self.answer_agent.run(
            session_id=state["session_id"],
            user_question=state["user_question"],
            sql_query="-- none --",
            query_result=state["user_question"],
        )
        state["answer_result"] = answer
        state["final_output"] = answer
        return state

    def answer_node(self, state: ChatState) -> ChatState:
        route = state["route"]
        session_id = state["session_id"]
        user_question = state["user_question"]

        if route == "sql":
            sql_res = state.get("sql_result", {})
            answer = self.answer_agent.run(
                session_id=session_id,
                user_question=user_question,
                sql_query=sql_res.get("sql_query", "SQL executed"),
                query_result=sql_res.get("db_result", []),
            )
        elif route == "search":
            search_res = state.get("search_result", {})
            query_result = search_res.get("db_result") or search_res.get("message") or str(search_res)
            answer = self.answer_agent.run(
                session_id=session_id,
                user_question=user_question,
                sql_query="-- no SQL used --",
                query_result=query_result,
            )
        else:
            answer = self.answer_agent.run(
                session_id=session_id,
                user_question=user_question,
                sql_query="-- none --",
                query_result=user_question,
            )

        # Lưu vào session memory
        self.memory.append_user(session_id, user_question)
        self.memory.append_ai(session_id, answer.get("message"))
        state["answer_result"] = answer
        state["final_output"] = answer
        return state

    # ========== Run pipeline ==========

    def run(self, session_id: str, user_question: str, region_id: int = 0) -> dict:
        """Run pipeline có region riêng cho mỗi request."""
        state = {
            "session_id": session_id,
            "user_question": user_question,
            "region_id": region_id,
        }
        result = self.compiled_graph.invoke(state)
        final = result.get("final_output", {})
        if not final:
            final = {
                "question_old": [user_question],
                "message": "No response generated.",
                "audio": [],
                "location": {},
            }
        final["question_old"] = self.memory.get_history_list(session_id)
        return final
