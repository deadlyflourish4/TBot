"""
TravelAgent: LLM-driven agent with function calling.
Replaces SemanticRouter + QueryStore pipeline.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

from langchain_community.chat_models import ChatOllama

from tools.definitions import TRAVEL_TOOLS
from tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là T-Bot, một hướng dẫn viên du lịch AI thông minh và thân thiện.

NHIỆM VỤ:
- Trả lời câu hỏi về các địa điểm du lịch
- Sử dụng các công cụ (tools) để tìm thông tin chính xác
- Nếu không tìm thấy, thành thật nói không biết

NGUYÊN TẮC:
1. LUÔN ưu tiên dùng tool để tìm thông tin, KHÔNG được bịa
2. Trả lời ngắn gọn, thân thiện với "dạ/ạ/nhé"
3. Nếu user chào hỏi (xin chào, cảm ơn...), trả lời trực tiếp không cần tool
4. Nếu tool trả về found=False, thông báo không tìm thấy

CÁC TOOL CÓ SẴN:
- get_place_info: Lấy thông tin giới thiệu địa điểm
- get_place_location: Lấy vị trí, địa chỉ
- get_place_media: Lấy video, audio
- get_attractions: Lấy danh sách điểm tham quan
- search_places: Tìm kiếm địa điểm (dùng khi không biết tên chính xác)

ĐỊNH DẠNG RESPONSE:
- Dùng emoji phù hợp (📍 cho vị trí, 🎬 cho video, 🎯 cho điểm tham quan)
- Kết thúc bằng câu hỏi gợi ý nếu phù hợp
"""


class TravelAgent:
    """LLM Agent với function calling cho travel chatbot."""

    def __init__(
        self,
        executor: ToolExecutor,
        model_name: str = None,
        max_iterations: int = 3
    ):
        """
        Args:
            executor: ToolExecutor instance for tool execution
            model_name: Ollama model name (default from env)
            max_iterations: Max tool call iterations
        """
        self.executor = executor
        self.max_iterations = max_iterations
        self.tools = TRAVEL_TOOLS
        
        # Get model from env or default
        model = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        
        self.llm = ChatOllama(
            model=model,
            temperature=0.2,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        
        logger.info(f"TravelAgent initialized with model: {model}")

    async def run(
        self,
        query: str,
        context: Dict[str, Any],
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Main agent loop.
        
        Args:
            query: User question
            context: {region_id, project_id, user_location}
            chat_history: Previous messages for context
            
        Returns:
            Final response string
        """
        # Check for chitchat first (no tool needed)
        if self._is_chitchat(query):
            return await self._handle_chitchat(query)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Add chat history (last 3 turns = 6 messages)
        if chat_history:
            messages.extend(chat_history[-6:])
        
        messages.append({"role": "user", "content": query})
        
        for iteration in range(self.max_iterations):
            logger.debug(f"Agent iteration {iteration + 1}/{self.max_iterations}")
            
            try:
                # Call LLM with tools
                response = self.llm.invoke(
                    messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                # Check for tool calls
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args", {})
                        
                        logger.info(f"🔧 Tool call: {tool_name}({tool_args})")
                        
                        # Execute tool
                        result = await self.executor.execute(
                            tool_name, tool_args, context
                        )
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", tool_name),
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                else:
                    # No tool calls = final answer
                    final_response = response.content.strip()
                    logger.info(f"✅ Final response: {final_response[:100]}...")
                    return final_response
                    
            except Exception as e:
                logger.error(f"Agent error in iteration {iteration + 1}: {e}")
                if iteration == self.max_iterations - 1:
                    return f"Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại."
        
        # Max iterations reached, try to synthesize from what we have
        return "Xin lỗi, tôi không thể tìm được thông tin phù hợp. Bạn có thể thử hỏi cụ thể hơn không ạ?"

    def _is_chitchat(self, query: str) -> bool:
        """Quick check for chitchat queries that don't need tools."""
        chitchat_keywords = [
            "xin chào", "chào bạn", "hello", "hi ", "hey",
            "cảm ơn", "thanks", "thank you", "cám ơn",
            "tạm biệt", "bye", "goodbye",
            "bạn khỏe không", "bạn là ai", "tên bạn là gì",
        ]
        query_lower = query.lower().strip()
        return any(kw in query_lower for kw in chitchat_keywords)

    async def _handle_chitchat(self, query: str) -> str:
        """Handle chitchat without using tools."""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["xin chào", "chào", "hello", "hi"]):
            return "Xin chào bạn! 👋 Mình là T-Bot, hướng dẫn viên du lịch AI. Bạn muốn tìm hiểu về địa điểm nào không ạ?"
        
        if any(kw in query_lower for kw in ["cảm ơn", "thanks", "cám ơn"]):
            return "Dạ không có chi ạ! 😊 Bạn cần hỗ trợ gì thêm không nhé?"
        
        if any(kw in query_lower for kw in ["tạm biệt", "bye"]):
            return "Tạm biệt bạn! Chúc bạn có chuyến đi vui vẻ nhé! 🌟"
        
        if "bạn là ai" in query_lower or "tên bạn" in query_lower:
            return "Mình là T-Bot, trợ lý du lịch AI của bạn. Mình có thể giúp bạn tìm thông tin về các địa điểm du lịch, video, hướng dẫn đường đi và nhiều thứ khác nữa! 🗺️"
        
        # Default chitchat response
        return "Mình là T-Bot, sẵn sàng hỗ trợ bạn về các địa điểm du lịch. Bạn muốn tìm hiểu gì ạ?"
