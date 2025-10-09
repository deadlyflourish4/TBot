from typing import TypedDict, Optional, Dict
from langgraph.graph import StateGraph, END
import json

from .Agent.SQLagent import SQLAgent
from .Agent.Searchagent import SearchAgent
from .Agent.Answeragent import AnswerAgent
from .Agent.Routeagent import RouterAgent
from .Database.db import DatabaseConnector
from .SystemPrompt.SQLprompt import sql_prompt
from .SystemPrompt.Ansprompt import ans_prompt
from .SystemPrompt.Routeprompt import route_prompt
from .Utils.SessionMemory import SessionMemory


class ChatState(TypedDict):
    session_id: str
    user_question: str
    route: str
    sql_result: Optional[dict]
    search_result: Optional[dict]
    answer_result: Optional[dict]
    final_output: Optional[dict]


class GraphOrchestrator:
    """Main orchestrator controlling the full multi-agent pipeline."""

    def __init__(self):
        self.memory = SessionMemory()
        db = DatabaseConnector()
        api_key = "AIzaSyB6l_kooxHVkG2EWKI823wEMXEa_1A5lxY"

        # All agents share the same session memory
        self.sql_agent = SQLAgent(system_prompt=sql_prompt, db=db, api_key=api_key, memory=self.memory)
        self.search_agent = SearchAgent(system_prompt=None, api_key=api_key, memory=self.memory)
        self.answer_agent = AnswerAgent(system_prompt=ans_prompt, api_key=api_key, memory=self.memory)
        self.router_agent = RouterAgent(system_prompt=route_prompt, api_key=api_key, memory=self.memory)

        # Build LangGraph
        graph = StateGraph(ChatState)
        graph.add_node("router", self.router_node)
        graph.add_node("sql", self.sql_node)
        graph.add_node("search", self.search_node)
        graph.add_node("other", self.other_node)
        graph.add_node("answer", self.answer_node)

        graph.set_entry_point("router")
        graph.add_conditional_edges(
            "router",
            lambda state: state["route"],
            {"sql": "sql", "search": "search", "other": "other"},
        )

        graph.add_edge("sql", "answer")
        graph.add_edge("search", "answer")
        graph.add_edge("other", "answer")
        graph.add_edge("answer", END)

        self.compiled_graph = graph.compile()

    # ========== Node Definitions ==========

    def router_node(self, state: ChatState) -> ChatState:
        """Classify user question as sql / search / other."""
        res = self.router_agent.route(state["session_id"], state["user_question"])
        route = res.get("route", "other").strip().lower()
        state["route"] = route
        return state

    def sql_node(self, state: ChatState) -> ChatState:
        """Execute SQL query."""
        result = self.sql_agent.get_query(state["session_id"], state["user_question"])
        state["sql_result"] = result
        return state

    def search_node(self, state: ChatState) -> ChatState:
        """Execute web search."""
        result = self.search_agent.run(state["session_id"], state["user_question"])
        state["search_result"] = result
        return state

    def other_node(self, state: ChatState) -> ChatState:
        """Handle general or fallback questions."""
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
        """Generate final natural-language answer."""
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
            query_result = (
                search_res.get("db_result")
                or search_res.get("message")
                or str(search_res)
            )
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

        # Store conversation in shared memory
        self.memory.append_user(session_id, user_question)
        self.memory.append_ai(session_id, answer.get("message"))

        # Combine final output
        state["answer_result"] = answer
        state["final_output"] = answer
        return state

    # ========== Public Method ==========

    def run(self, session_id: str, user_question: str) -> dict:
        """Run the full pipeline and return unified JSON."""
        result = self.compiled_graph.invoke(
            {"session_id": session_id, "user_question": user_question}
        )

        final = result.get("final_output", {})
        if not final:
            final = {
                "question_old": [user_question],
                "message": "No response generated.",
                "audio": [],
                "location": {},
            }

        # Replace question_old with global conversation memory
        final["question_old"] = self.memory.get_history_list(session_id)
        return final


if __name__ == "__main__":
    orchestrator = GraphOrchestrator()

    questions = [
        # "Gioi thieu POI 201",
        # "Co",
        # "Hello, my name is anansupercuteeeee",
        # "what is my name?", 
        # "Ưhich POI i have just asked you to introduce?",
        "location of POI 2",
        "co",
        "i ưant to hear media about Chinatown",
    ]

    for q in questions:
        output = orchestrator.run("session_1", q)
        print("=" * 80)
        print("Question:", q)
        print("Final JSON Output:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
