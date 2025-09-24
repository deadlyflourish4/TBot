from typing import TypedDict, List, Union, Optional
from langgraph.graph import StateGraph, END

# ==== Import agents ====
from Agent.SQLagent import SQLAgent
from Agent.Searchagent import SearchAgent
from Agent.Answeragent import AnswerAgent
from Agent.Routeagent import RouterAgent
from Database.db import DatabaseConnector
from SystemPrompt.SQLprompt import sql_prompt
from SystemPrompt.Ansprompt import ans_prompt
from SystemPrompt.Routeprompt import route_prompt


# ===== State =====
class ChatState(TypedDict):
    session_id: str
    user_question: str
    route: str
    sql_query: Optional[str]
    db_result: Union[List[dict], str, None]
    search_result: Optional[str]
    final_answer: Optional[str]
    no_data: bool


class GraphOrchestrator:
    def __init__(self):
        # Khởi tạo DB và Agents
        db = DatabaseConnector(server="localhost", database="Orpheo")

        self.sql_agent = SQLAgent(system_prompt=sql_prompt, db=db)
        self.search_agent = SearchAgent()
        self.answer_agent = AnswerAgent(system_prompt=ans_prompt)
        self.router_agent = RouterAgent(system_prompt=route_prompt)

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
            lambda state: state["route"],
            {
                "sql": "sql",
                "search": "search",
                "other": "other"
            }
        )

        graph.add_edge("sql", "answer")
        graph.add_edge("search", "answer")
        graph.add_edge("other", "answer")
        graph.add_edge("answer", END)

        self.compiled_graph = graph.compile()

    # ===== Node functions =====
    def router_node(self, state: ChatState) -> ChatState:
        route = self.router_agent.route(state["session_id"], state["user_question"])
        state["route"] = route
        return state

    def sql_node(self, state: ChatState) -> ChatState:
        res = self.sql_agent.get_query(state["session_id"], state["user_question"])
        state["sql_query"] = res["sql"]
        state["db_result"] = res["result"]
        state["no_data"] = not (isinstance(res["result"], list) and len(res["result"]) > 0)
        return state

    def search_node(self, state: ChatState) -> ChatState:
        state["search_result"] = self.search_agent.run(state["user_question"])
        return state

    def other_node(self, state: ChatState) -> ChatState:
        state["final_answer"] = state["user_question"]
        return state

    def answer_node(self, state: ChatState) -> ChatState:
        if state["route"] == "sql":
            if state["no_data"]:
                state["search_result"] = self.search_agent.run(state["user_question"])
                state["final_answer"] = self.answer_agent.get_answer(
                    state["session_id"],
                    state["user_question"],
                    sql_query=state["sql_query"],
                    query_result="❌ Không có dữ liệu trong DB.\nDữ liệu web:\n" + state["search_result"]
                )
            else:
                state["final_answer"] = self.answer_agent.get_answer(
                    state["session_id"],
                    state["user_question"],
                    sql_query=state["sql_query"],
                    query_result=state["db_result"]
                )
        elif state["route"] == "search":
            state["final_answer"] = self.answer_agent.get_answer(
                state["session_id"],
                state["user_question"],
                sql_query="-- không dùng SQL --",
                query_result=state["search_result"]
            )
        elif state["route"] == "other":
            state["final_answer"] = self.answer_agent.get_answer(
                state["session_id"],
                state["user_question"],
                sql_query="-- không dùng SQL --",
                query_result=state["final_answer"]
            )
        return state

    # ===== Public run =====
    def run(self, session_id: str, user_question: str) -> dict:
        return self.compiled_graph.invoke({
            "session_id": session_id,
            "user_question": user_question
        })


# ===== Test =====
if __name__ == "__main__":
    orchestrator = GraphOrchestrator()

    questions = [
        "Giá tour Huế là bao nhiêu?",
        "Tôi muốn đi Đức",
        "Hello, tôi là Đức Anh"
    ]

    for q in questions:
        output = orchestrator.run("s1", q)

        print("=" * 50)
        print("❓ Câu hỏi:", q)
        print("📍 Route:", output["route"])
        print("📝 SQL:", output.get("sql_query"))
        print("📊 DB result:", output.get("db_result"))
        print("🌍 Search result:", str(output.get("search_result"))[:200], "...")
        print("💬 Final Answer:", output.get("final_answer"))
