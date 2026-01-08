"""
TBot Pipeline with Query-Oriented RAG.

Flow:
1. User Input → Reflection → Synthesized Query
2. Semantic Router → [Chitchat] → LLMs
                   → [RAG] → QueryStore → Reranker → SQL Execute → LLMs
"""
import logging
from typing import Any, Dict, List, Optional

import torch
from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from agents.Answeragent import AnswerAgent
from agents.SemanticRouter import SemanticRouter
from database.db import MultiDBManager
from rag.location import NERService, LocationStore
from rag.query_store import QueryStore
from rag.reranker import Reranker
from utils.Reflection import Reflection
from utils.SessionMemory import SessionMemory

logger = logging.getLogger(__name__)


# ==========================================================
# DB WRAPPER
# ==========================================================
class DBWrapper:
    """Database wrapper with parameterized query support."""

    def __init__(self, engine, debug: bool = False):
        self.engine = engine
        self.debug = debug

    def run_query(self, sql: str, params: dict = None) -> List[Dict]:
        """Execute SQL query with parameters."""
        if self.debug:
            logger.debug(f"SQL: {sql.strip()}")
            logger.debug(f"Params: {params}")

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            rows = [dict(r._mapping) for r in result]

        if self.debug:
            logger.debug(f"Rows: {len(rows)}")

        return rows


# ==========================================================
# PIPELINE (Shared Resources)
# ==========================================================
class Pipeline:
    """Shared resources - initialized once."""

    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "anansupercuteeeee/multilingual-traveling"

        logger.info(f"Loading embedder: {model_name} on {device.upper()}")
        self.embedder = SentenceTransformer(model_name, device=device)

        # Core components
        self.db_manager = MultiDBManager()
        self.semantic_router = SemanticRouter(self.embedder)
        self.ner_service = NERService()

        # Location store
        self.location_store = LocationStore(
            embedder=self.embedder,
            db_manager=self.db_manager,
            ner_service=self.ner_service,
        )
        self.location_store.preload()

        # Query RAG components
        self.query_store = QueryStore(embedder=self.embedder)
        self.reranker = Reranker()

        logger.info("Pipeline initialized")


# ==========================================================
# GRAPH ORCHESTRATOR
# ==========================================================
class GraphOrchestrator:
    """Main orchestrator with Query-Oriented RAG."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.memory = SessionMemory()
        self.pipeline = Pipeline()

        # Shared components
        self.router = self.pipeline.semantic_router
        self.location_store = self.pipeline.location_store
        self.db_manager = self.pipeline.db_manager
        self.query_store = self.pipeline.query_store
        self.reranker = self.pipeline.reranker

        # LLM Agent
        self.answer_agent = AnswerAgent(system_prompt="", memory=self.memory)

        # Reflection module
        self.reflection = Reflection(llm=self.answer_agent.llm)

    def _log(self, msg: str) -> None:
        if self.debug:
            logger.debug(msg)

    # ----------------------------------------------------------
    # LLM Response
    # ----------------------------------------------------------
    def synthesize_response(self, question: str, data: Any, intent: str) -> str:
        """Generate natural language response."""
        try:
            return self.answer_agent.run_synthesizer(question, data, intent)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return str(data)

    # ----------------------------------------------------------
    # RAG: Execute SQL Template
    # ----------------------------------------------------------
    def execute_rag_query(
        self,
        template: Dict,
        variables: Dict,
        ctx: Dict,
    ) -> Optional[Dict]:
        """Execute SQL template with bound variables."""
        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine, debug=self.debug)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = template["sql_template"].replace("{prefix}", prefix)

        print(f"📊 [SQL] {sql}")
        print(f"📊 [PARAMS] {variables}")
        rows = db.run_query(sql, variables)
        print(f"📊 [RESULT] {len(rows)} rows")

        return rows[0] if rows else None

    # ----------------------------------------------------------
    # Chitchat Handler
    # ----------------------------------------------------------
    def run_chitchat(self, question: str) -> Dict:
        """Handle chitchat directly with LLM."""
        return {"context": "social", "query": question}

    # ==========================================================
    # MAIN PIPELINE
    # ==========================================================
    def run(
        self,
        session_id: str,
        user_question: str,
        user_location: str,
        project_id: int,
        region_id: int = 0,
    ) -> Dict[str, Any]:
        """
        Main pipeline entry point.

        Flow:
        1. Reflection (rewrite query)
        2. Semantic Router (chitchat vs RAG)
        3. [Chitchat] → LLM
        4. [RAG] → QueryStore → Reranker → SQL → LLM
        """
        ctx = {
            "session_id": f"{session_id}_{region_id}",
            "project_id": project_id,
            "region_id": region_id,
        }

        print(f"\n{'='*50}")
        print(f"📥 [INPUT] {user_question}")
        print(f"{'='*50}")

        # 1️⃣ REFLECTION - Rewrite query with context
        self.memory.append_user(ctx["session_id"], user_question)
        synthesized_query = self.reflection(self.memory, ctx["session_id"])
        print(f"🔄 [REFLECTION] {user_question} → {synthesized_query}")

        # 2️⃣ SEMANTIC ROUTER - Chitchat or RAG?
        route_result = self.router.classify(synthesized_query)
        is_chitchat = route_result["is_chitchat"]
        route_type = 'CHITCHAT' if is_chitchat else 'RAG'
        print(f"🚦 [ROUTER] {route_type} (score: {route_result['score']:.2f})")

        # 3️⃣ ROUTE: Chitchat vs RAG
        if is_chitchat:
            raw_data = self.run_chitchat(synthesized_query)
            final_message = self.synthesize_response(
                synthesized_query, raw_data, "chitchat"
            )
        else:
            # 4️⃣ QUERY RAG - Match query to template
            candidates = self.query_store.match(synthesized_query, top_k=3)

            if not candidates:
                logger.warning("No matching query templates")
                raw_data = {"error": "no_template_match"}
                final_message = "Xin lỗi, tôi không hiểu câu hỏi của bạn."
            else:
                # 5️⃣ RERANKER - Get best match
                reranked = self.reranker.rerank(synthesized_query, candidates, top_k=1)
                best_match = reranked[0]
                template = best_match["template"]

                print(f"📋 [TEMPLATE] {template['intent']} (score: {best_match.get('rerank_score', best_match['score']):.3f})")

                # 6️⃣ EXTRACT VARIABLES - Use NER for place_name
                variables = {"project_id": project_id}  # Always include project_id
                
                if "place_name" in template["required_vars"]:
                    ner_locs = self.location_store.extract_ner(synthesized_query)
                    print(f"🏷️ [NER] Extracted: {ner_locs}")

                    if ner_locs:
                        place = self.location_store.match(
                            region_id=region_id,
                            project_id=project_id,
                            ner_location=ner_locs[0],
                        )
                        if place:
                            variables["place_name"] = place["name"]

                    # Fallback to context
                    if "place_name" not in variables:
                        last_place = self.memory.get_ctx(ctx["session_id"], "last_target_place")
                        if last_place:
                            variables["place_name"] = last_place["name"]

                # Check required variables
                missing = [v for v in template["required_vars"] if v not in variables]
                if missing:
                    logger.warning(f"Missing variables: {missing}")
                    raw_data = {"error": "missing_variables", "missing": missing}
                    final_message = "Bạn muốn hỏi về địa điểm nào?"
                else:
                    # 7️⃣ EXECUTE SQL
                    raw_data = self.execute_rag_query(template, variables, ctx)

                    # Save target place
                    if "place_name" in variables:
                        self.memory.set_ctx(
                            ctx["session_id"],
                            "last_target_place",
                            {"name": variables["place_name"]},
                        )

                    # 8️⃣ LLM RESPONSE
                    if raw_data:
                        if template["intent"] == "direction" and raw_data.get("Location"):
                            final_message = "Bạn có thể bấm nút bên dưới để xem cách đi"
                        else:
                            final_message = self.synthesize_response(
                                synthesized_query, raw_data, template["intent"]
                            )
                    else:
                        final_message = "Xin lỗi, không tìm thấy thông tin."

        # Save AI response
        self.memory.append_ai(ctx["session_id"], final_message)

        # Format output
        location = None
        audio = None

        if raw_data and isinstance(raw_data, dict):
            location = raw_data.get("Location")
            if raw_data.get("media_type", "").lower() == "video":
                audio = raw_data.get("url")

        return {
            "Message": final_message,
            "location": location,
            "audio": audio,
            "session_id": ctx["session_id"],
        }
