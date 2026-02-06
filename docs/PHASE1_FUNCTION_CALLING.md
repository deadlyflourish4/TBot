# Phase 1: Function Calling Core

## Mục tiêu

Chuyển từ **template matching** (QueryStore) sang **LLM-driven function calling** (TravelAgent).

---

## Bước 1: Tool Definitions (Day 1-2)

### Tạo file `app/tools/__init__.py`

```python
from .definitions import TRAVEL_TOOLS
from .executor import ToolExecutor

__all__ = ["TRAVEL_TOOLS", "ToolExecutor"]
```

### Tạo file `app/tools/definitions.py`

```python
"""
Tool definitions for TravelAgent.
LLM sẽ dựa vào schema này để quyết định tool nào cần gọi.
"""

TRAVEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_place_info",
            "description": "Lấy thông tin giới thiệu về một địa điểm du lịch. Dùng khi user hỏi 'giới thiệu về X', 'X là gì', 'kể về X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm cần tra cứu"
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_location",
            "description": "Lấy vị trí, địa chỉ của một địa điểm. Dùng khi user hỏi 'X ở đâu', 'địa chỉ của X', 'cách đi đến X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm"
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_media",
            "description": "Lấy video, audio về một địa điểm. Dùng khi user hỏi 'video về X', 'có clip X không'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm"
                    },
                    "media_type": {
                        "type": "string",
                        "enum": ["video", "audio", "all"],
                        "description": "Loại media cần lấy"
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_attractions",
            "description": "Lấy danh sách điểm tham quan trong một địa điểm. Dùng khi user hỏi 'X có gì', 'có gì vui ở X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng kết quả tối đa",
                        "default": 5
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": "Tìm kiếm địa điểm theo từ khóa. Dùng khi không biết chính xác tên địa điểm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Số kết quả trả về",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]
```

---

## Bước 2: Tool Executor (Day 2-3)

### Tạo file `app/tools/executor.py`

```python
"""
ToolExecutor: Execute tools based on LLM decisions.
Handles multi-region database queries.
"""
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Execute travel-related tools."""

    def __init__(self, db_manager, vector_store=None):
        """
        Args:
            db_manager: MultiDBManager instance
            vector_store: Optional TravelVectorStore for search_places
        """
        self.db = db_manager
        self.vector_store = vector_store
        
        self.registry = {
            "get_place_info": self._get_place_info,
            "get_place_location": self._get_place_location,
            "get_place_media": self._get_place_media,
            "get_attractions": self._get_attractions,
            "search_places": self._search_places,
        }

    async def execute(
        self, 
        tool_name: str, 
        args: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool with given arguments and context.
        
        Args:
            tool_name: Name of tool to execute
            args: Tool arguments from LLM
            context: {region_id, project_id, user_location}
            
        Returns:
            Tool execution result as dict
        """
        if tool_name not in self.registry:
            logger.error(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            handler = self.registry[tool_name]
            result = await handler(args, context)
            logger.info(f"Tool {tool_name} executed: {len(str(result))} chars")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}

    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================

    async def _get_place_info(self, args: Dict, ctx: Dict) -> Dict:
        """Get place introduction from database."""
        region_id = ctx["region_id"]
        project_id = ctx["project_id"]
        place_name = args["place_name"]
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT SubProjectName, Introduction 
        FROM {prefix}.SubProjects 
        WHERE SubProjectName LIKE :place_name 
        AND ProjectID = :project_id
        """
        
        with engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {"place_name": f"%{place_name}%", "project_id": project_id}
            ).fetchone()
        
        if row:
            return {
                "found": True,
                "name": row.SubProjectName,
                "introduction": row.Introduction or "Không có thông tin",
                "source": "database"
            }
        
        # Fallback to vector search if available
        if self.vector_store:
            return await self._search_places({"query": place_name, "top_k": 1}, ctx)
        
        return {"found": False, "message": f"Không tìm thấy {place_name}"}

    async def _get_place_location(self, args: Dict, ctx: Dict) -> Dict:
        """Get place location from database."""
        region_id = ctx["region_id"]
        project_id = ctx["project_id"]
        place_name = args["place_name"]
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT SubProjectName, Location 
        FROM {prefix}.SubProjects 
        WHERE SubProjectName LIKE :place_name 
        AND ProjectID = :project_id
        """
        
        with engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {"place_name": f"%{place_name}%", "project_id": project_id}
            ).fetchone()
        
        if row:
            return {
                "found": True,
                "name": row.SubProjectName,
                "location": row.Location or "Không có thông tin địa chỉ",
                "source": "database"
            }
        
        return {"found": False, "message": f"Không tìm thấy vị trí của {place_name}"}

    async def _get_place_media(self, args: Dict, ctx: Dict) -> Dict:
        """Get media files for a place."""
        region_id = ctx["region_id"]
        project_id = ctx["project_id"]
        place_name = args["place_name"]
        media_type = args.get("media_type", "video")
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT sp.SubProjectName, a.AttractionName, am.MediaType, am.MediaURL 
        FROM {prefix}.SubProjects sp 
        JOIN {prefix}.SubProjectAttractions a ON sp.SubProjectID = a.SubProjectID 
        JOIN {prefix}.SubProjectAttractionMedia am ON a.SubProjectAttractionID = am.SubProjectAttractionID 
        WHERE sp.SubProjectName LIKE :place_name 
        AND sp.ProjectID = :project_id
        AND am.MediaType = :media_type
        """
        
        with engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {
                    "place_name": f"%{place_name}%",
                    "project_id": project_id,
                    "media_type": media_type
                }
            ).fetchall()
        
        if rows:
            media_list = [
                {
                    "attraction": r.AttractionName,
                    "type": r.MediaType,
                    "url": r.MediaURL
                }
                for r in rows
            ]
            return {
                "found": True,
                "name": rows[0].SubProjectName,
                "media": media_list,
                "source": "database"
            }
        
        return {"found": False, "message": f"Không tìm thấy media của {place_name}"}

    async def _get_attractions(self, args: Dict, ctx: Dict) -> Dict:
        """Get attractions within a place."""
        region_id = ctx["region_id"]
        project_id = ctx["project_id"]
        place_name = args["place_name"]
        limit = args.get("limit", 5)
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT TOP {limit} sp.SubProjectName, a.AttractionName, a.Introduction 
        FROM {prefix}.SubProjects sp 
        JOIN {prefix}.SubProjectAttractions a ON sp.SubProjectID = a.SubProjectID 
        WHERE sp.SubProjectName LIKE :place_name 
        AND sp.ProjectID = :project_id 
        ORDER BY a.SortOrder
        """
        
        with engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {"place_name": f"%{place_name}%", "project_id": project_id}
            ).fetchall()
        
        if rows:
            attractions = [
                {
                    "name": r.AttractionName,
                    "description": (r.Introduction or "")[:200]
                }
                for r in rows
            ]
            return {
                "found": True,
                "place": rows[0].SubProjectName,
                "attractions": attractions,
                "count": len(attractions),
                "source": "database"
            }
        
        return {"found": False, "message": f"Không tìm thấy điểm tham quan tại {place_name}"}

    async def _search_places(self, args: Dict, ctx: Dict) -> Dict:
        """Search places using vector store (Phase 2)."""
        query = args["query"]
        top_k = args.get("top_k", 5)
        
        if not self.vector_store:
            # Placeholder until Phase 2
            return {
                "found": False,
                "message": "Vector search chưa được cấu hình",
                "source": "vector_store"
            }
        
        results = await self.vector_store.search(
            query=query,
            region_id=ctx.get("region_id"),
            project_id=ctx.get("project_id"),
            top_k=top_k
        )
        
        return {
            "found": len(results) > 0,
            "places": results,
            "count": len(results),
            "source": "vector_store"
        }
```

---

## Bước 3: TravelAgent (Day 4-5)

### Tạo file `app/agents/travel_agent.py`

```python
"""
TravelAgent: LLM-driven agent with function calling.
Replaces SemanticRouter + QueryStore.
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
- Luôn ưu tiên dùng tool để tìm thông tin, không bịa
- Trả lời ngắn gọn, thân thiện với "dạ/ạ/nhé"
- Nếu user chào hỏi (xin chào, cảm ơn...), trả lời trực tiếp không cần tool

CÁC TOOL CÓ SẴN:
- get_place_info: Lấy thông tin giới thiệu địa điểm
- get_place_location: Lấy vị trí, địa chỉ
- get_place_media: Lấy video, audio
- get_attractions: Lấy danh sách điểm tham quan
- search_places: Tìm kiếm địa điểm
"""


class TravelAgent:
    """LLM Agent với function calling cho travel chatbot."""

    def __init__(
        self,
        executor: ToolExecutor,
        model_name: str = "qwen2.5:7b",
        max_iterations: int = 3
    ):
        self.executor = executor
        self.max_iterations = max_iterations
        self.tools = TRAVEL_TOOLS
        
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.2,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        
        logger.info(f"TravelAgent initialized with model: {model_name}")

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
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Add chat history (last 3 turns)
        if chat_history:
            messages.extend(chat_history[-6:])
        
        messages.append({"role": "user", "content": query})
        
        for iteration in range(self.max_iterations):
            logger.debug(f"Agent iteration {iteration + 1}")
            
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
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        
                        logger.info(f"Calling tool: {tool_name}({tool_args})")
                        
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
                    return response.content.strip()
                    
            except Exception as e:
                logger.error(f"Agent error: {e}")
                return f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"
        
        # Max iterations reached
        return "Xin lỗi, tôi không thể tìm được thông tin phù hợp."

    def is_chitchat(self, query: str) -> bool:
        """Quick check for chitchat queries."""
        chitchat_keywords = [
            "xin chào", "chào bạn", "hello", "hi", 
            "cảm ơn", "thanks", "tạm biệt", "bye"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in chitchat_keywords)
```

---

## Bước 4: Pipeline Integration (Day 6-7)

### Cập nhật `app/pipeline.py`

```python
# Thêm imports mới
from agents.travel_agent import TravelAgent
from tools.executor import ToolExecutor

class Pipeline:
    def __init__(self):
        # ... existing code ...
        
        # NEW: Initialize tools and agent
        self.executor = ToolExecutor(
            db_manager=self.db_manager,
            vector_store=None  # Will be added in Phase 2
        )
        self.agent = TravelAgent(
            executor=self.executor,
            model_name="qwen2.5:7b"
        )

class GraphOrchestrator:
    async def run(
        self,
        session_id: str,
        user_question: str,
        user_location: str,
        project_id: int,
        region_id: int = 0,
    ) -> Dict:
        # ... reflection code unchanged ...
        
        # NEW: Use TravelAgent instead of SemanticRouter
        context = {
            "region_id": region_id,
            "project_id": project_id,
            "user_location": user_location
        }
        
        # Get chat history from memory
        history = self.memory.get(session_id)
        chat_history = [
            {"role": "user" if m.type == "human" else "assistant", "content": m.content}
            for m in history.messages[-6:]
        ] if history else None
        
        # Run agent
        response = await self.pipeline.agent.run(
            query=synthesized,
            context=context,
            chat_history=chat_history
        )
        
        # Store response in memory
        self.memory.add_ai_message(session_id, response)
        
        return {"message": response}
```

---

## Testing

### Test cơ bản

```python
# tests/test_tools.py
import pytest
from tools.executor import ToolExecutor

@pytest.mark.asyncio
async def test_get_place_info():
    executor = ToolExecutor(mock_db_manager)
    result = await executor.execute(
        "get_place_info",
        {"place_name": "Bà Nà Hills"},
        {"region_id": 0, "project_id": 1}
    )
    assert result["found"] == True
    assert "Bà Nà" in result["name"]
```

### Test Agent flow

```bash
# Manual test
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Bà Nà Hills ở đâu?",
    "project_id": 1,
    "region_id": 0
  }'
```

---

## Checklist

- [ ] Tạo `app/tools/__init__.py`
- [ ] Tạo `app/tools/definitions.py` với 5 tools
- [ ] Tạo `app/tools/executor.py`
- [ ] Implement các tool handlers
- [ ] Tạo `app/agents/travel_agent.py`
- [ ] Test Ollama function calling với qwen2.5
- [ ] Cập nhật `pipeline.py`
- [ ] Test end-to-end với 4 regions
- [ ] Giữ backup SemanticRouter nếu cần
