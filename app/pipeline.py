"""
TBot Pipeline V2 with TravelAgent (LLM Function Calling).

Flow:
1. User Input → TravelAgent → LLM decides tool
2. ToolExecutor → SQL query / Qdrant vector search → result
3. LLM synthesizes response
"""
import logging
import os
from typing import Any, Dict

from database.db import MultiDBManager
from agents.travel_agent import TravelAgent
from tools.executor import ToolExecutor
from services.chat_manager import ChatManager

logger = logging.getLogger(__name__)


class GraphOrchestrator:
    """
    V2 Orchestrator using TravelAgent with LLM function calling.
    Replaces SemanticRouter + QueryStore + Reranker pipeline.
    """

    def __init__(self):
        # Database
        self.db_manager = MultiDBManager()

        # Vector store (graceful fallback if Qdrant not available)
        vector_store = self._init_vector_store()

        # ToolExecutor with optional vector search
        self.executor = ToolExecutor(
            db_manager=self.db_manager,
            vector_store=vector_store,
        )

        # TravelAgent (LLM + function calling)
        self.agent = TravelAgent(executor=self.executor)

        # Chat session manager
        self.chat_manager = ChatManager(db_manager=self.db_manager)

        logger.info(
            f"GraphOrchestrator V2 initialized | "
            f"vector_store={'✅' if vector_store else '❌ (SQL only)'}"
        )

    def _init_vector_store(self):
        """Initialize TravelVectorStore, return None if Qdrant unavailable."""
        try:
            from sentence_transformers import SentenceTransformer
            from rag.vector_store import TravelVectorStore

            embedder = SentenceTransformer("intfloat/multilingual-e5-small")
            store = TravelVectorStore(
                embedder=embedder,
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333")),
            )
            logger.info("TravelVectorStore loaded ✅")
            return store
        except Exception as e:
            logger.warning(f"TravelVectorStore unavailable: {e} — running SQL only")
            return None

    async def run(
        self,
        session_id: str,
        user_question: str,
        user_location: str,
        project_id: int,
        region_id: int = 0,
    ) -> Dict[str, Any]:
        """
        Main entry point.

        Args:
            session_id: Chat session ID
            user_question: User's question
            user_location: User's GPS coordinates
            project_id: Project filter
            region_id: Database region (0-3)

        Returns:
            {"Message": "...", "location": ..., "audio": ..., "session_id": ...}
        """
        context = {
            "region_id": region_id,
            "project_id": project_id,
            "user_location": user_location,
        }

        # Get chat history for context
        session = self.chat_manager.get_session(session_id)
        chat_history = None
        if session:
            chat_history = session.get_history(limit=6)

        logger.info(f"[Pipeline] Query: {user_question[:80]}... | region={region_id}")

        # Run TravelAgent (LLM function calling loop)
        try:
            response_text = await self.agent.run(
                query=user_question,
                context=context,
                chat_history=chat_history,
            )
        except Exception as e:
            logger.error(f"[Pipeline] Agent error: {e}", exc_info=True)
            response_text = "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại."

        return {
            "Message": response_text,
            "location": None,
            "audio": None,
            "session_id": session_id,
        }
