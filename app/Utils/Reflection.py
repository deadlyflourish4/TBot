"""
Reflection module for query rewriting.
Rewrites follow-up questions to be standalone using conversation context.
"""
import logging
from langchain_core.chat_history import InMemoryChatMessageHistory

logger = logging.getLogger(__name__)


class Reflection:
    """
    Query rewriter for RAG pipeline.
    Converts follow-up questions into standalone queries.
    
    Optimization:
    - Skips LLM if first message (no context needed)
    - Uses minimal prompt for speed
    """

    def __init__(self, llm, max_turns: int = 3):
        self.llm = llm
        self.max_turns = max_turns

    def _format_history(self, history: InMemoryChatMessageHistory) -> str:
        """Format recent history as compact string."""
        messages = history.messages[-self.max_turns * 2:]
        lines = []
        for msg in messages:
            role = "U" if msg.type == "human" else "A"
            # Truncate long messages
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def __call__(self, session_memory, session_id: str) -> str:
        """
        Rewrite query to be standalone.
        
        Returns original query if:
        - First message in session
        - Query already standalone
        """
        history = session_memory.get(session_id)
        
        # Skip LLM for first message (no context to resolve)
        if len(history.messages) <= 2:
            last_msg = history.messages[-1].content if history.messages else ""
            logger.debug("Reflection: first message, skipping LLM")
            return last_msg

        # Clean, simple prompt
        history_str = self._format_history(history)
        
        prompt = f"""Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question in Vietnamese which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is.

Chat history:
{history_str}

Standalone question:"""

        try:
            result = self.llm.invoke(prompt)
            rewritten = result.content.strip().strip('"')
            print(f"🔄 [REFLECTION] {history.messages[-1].content} → {rewritten}")
            return rewritten
        except Exception as e:
            logger.error(f"Reflection error: {e}")
            return history.messages[-1].content
