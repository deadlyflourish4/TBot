# Phase 1: LangGraph Agent Core

## Overview

Phase này migrate từ custom TravelAgent sang LangGraph - một state machine framework cho AI agents.

**Thời gian dự kiến**: 1 tuần

---

## Objectives

1. Định nghĩa AgentState
2. Implement các Nodes (chatbot, tools)
3. Compile và test Graph
4. Integrate với FastAPI endpoints

---

## 1. Architecture

### Graph Flow

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
             ┌──────│  chatbot    │◄─────────┐
             │      │   node      │          │
             │      └──────┬──────┘          │
             │             │                 │
             │      ┌──────▼──────┐          │
             │      │  decision   │          │
             │      │ (has tools?)│          │
             │      └──────┬──────┘          │
             │             │                 │
             │    ┌────────┴────────┐        │
             │    │                 │        │
             │   YES               NO        │
             │    │                 │        │
             │    ▼                 ▼        │
             │ ┌──────┐      ┌──────────┐    │
             │ │tools │      │   END    │    │
             │ │ node │      └──────────┘    │
             │ └──┬───┘                      │
             │    │                          │
             │    └──────────────────────────┘
             │
             └────────► (loop back to chatbot)
```

---

## 2. File Structure

```
app/agents/
├── __init__.py      # Module exports
├── state.py         # AgentState definition
├── nodes.py         # chatbot_node, ToolNode
└── graph.py         # Graph compilation
```

---

## 3. Implementation

### 3.1 State Definition (`state.py`)

```python
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """State được truyền qua các nodes trong graph."""
    
    # Messages sử dụng operator.add để nối thêm (không ghi đè)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Context từ request
    context: Dict[str, Any]
    # context = {
    #     "region_id": 0,
    #     "project_id": 1,
    #     "user_id": "abc123"
    # }
```

### 3.2 Nodes Definition (`nodes.py`)

```python
import json
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_community.chat_models import ChatOllama

from tools.definitions import TRAVEL_TOOLS
from tools.executor import ToolExecutor
from .state import AgentState

# Initialize LLM với tools
llm = ChatOllama(model="qwen2.5:7b", temperature=0.2)
llm_with_tools = llm.bind_tools(TRAVEL_TOOLS)

SYSTEM_PROMPT = """Bạn là T-Bot, hướng dẫn viên du lịch AI.
Dùng tools để tìm thông tin, không được bịa.
Trả lời thân thiện, ngắn gọn."""

async def chatbot_node(state: AgentState) -> dict:
    """Node gọi LLM để sinh response hoặc tool calls."""
    messages = state["messages"]
    
    # Thêm system prompt nếu chưa có
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


class ToolNode:
    """Node thực thi tools."""
    
    def __init__(self, executor: ToolExecutor):
        self.executor = executor
    
    async def __call__(self, state: AgentState) -> dict:
        last_message = state["messages"][-1]
        context = state.get("context", {})
        
        results = []
        for tool_call in last_message.tool_calls:
            result = await self.executor.execute(
                tool_call["name"],
                tool_call["args"],
                context
            )
            results.append(ToolMessage(
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
                content=json.dumps(result, ensure_ascii=False)
            ))
        
        return {"messages": results}


def should_continue(state: AgentState) -> str:
    """Router: Nếu có tool calls thì chạy tools, không thì kết thúc."""
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"
```

### 3.3 Graph Compilation (`graph.py`)

```python
from langgraph.graph import StateGraph, END

from database.db import MultiDBManager
from tools.executor import ToolExecutor
from .state import AgentState
from .nodes import chatbot_node, ToolNode, should_continue

def create_travel_graph():
    """Build và compile LangGraph cho TBot."""
    
    # 1. Initialize dependencies
    db_manager = MultiDBManager()
    tool_executor = ToolExecutor(db_manager=db_manager)
    
    # 2. Create graph
    workflow = StateGraph(AgentState)
    
    # 3. Add nodes
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", ToolNode(executor=tool_executor))
    
    # 4. Set entry point
    workflow.set_entry_point("chatbot")
    
    # 5. Add edges
    workflow.add_conditional_edges(
        "chatbot",
        should_continue,
        {"tools": "tools", "end": END}
    )
    workflow.add_edge("tools", "chatbot")
    
    # 6. Compile
    return workflow.compile()


# Global instance
travel_graph = create_travel_graph()
```

---

## 4. FastAPI Integration

### Update main.py

```python
from langchain_core.messages import HumanMessage
from agents.graph import travel_graph

@app.post("/v2/chat")
async def chat_v2(request: ChatRequest):
    """New endpoint using LangGraph."""
    
    initial_state = {
        "messages": [HumanMessage(content=request.text)],
        "context": {
            "region_id": request.region_id,
            "project_id": request.project_id,
        }
    }
    
    result = await travel_graph.ainvoke(initial_state)
    
    # Get final AI message
    final_message = result["messages"][-1]
    return {"response": final_message.content}
```

---

## 5. Testing

### Unit Test Graph

```python
import pytest
from langchain_core.messages import HumanMessage
from agents.graph import travel_graph

@pytest.mark.asyncio
async def test_chitchat():
    """Test chitchat không cần tools."""
    state = {
        "messages": [HumanMessage(content="Xin chào")],
        "context": {"region_id": 0}
    }
    result = await travel_graph.ainvoke(state)
    
    assert "chào" in result["messages"][-1].content.lower()

@pytest.mark.asyncio
async def test_place_query():
    """Test query cần gọi tool."""
    state = {
        "messages": [HumanMessage(content="Giới thiệu Bà Nà Hills")],
        "context": {"region_id": 0, "project_id": 1}
    }
    result = await travel_graph.ainvoke(state)
    
    # Should have called get_place_info tool
    assert len(result["messages"]) > 2  # Human + Tool calls + AI response
```

---

## 6. Debugging với LangGraph Studio

LangGraph Studio cho phép visualize graph execution:

```bash
pip install langgraph-cli
langgraph dev --host 0.0.0.0 --port 8123
```

Mở `http://localhost:8123` để xem graph visualization.

---

## Acceptance Criteria

- [ ] `state.py` định nghĩa AgentState đúng
- [ ] `nodes.py` có chatbot_node và ToolNode
- [ ] `graph.py` compile thành công
- [ ] Test chitchat pass
- [ ] Test tool calling pass
- [ ] `/v2/chat` endpoint hoạt động

---

## Next Steps

Sau khi Phase 1 hoàn thành → Chuyển sang [Phase 2: Hybrid RAG](./PHASE2_HYBRID_RAG.md)
