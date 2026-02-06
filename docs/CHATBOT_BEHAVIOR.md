# 🤖 Hành Vi Chatbot Sau Upgrade

## So Sánh Trước vs Sau

### Ví dụ 1: Hỏi thông tin địa điểm

**User**: "Bà Nà Hills có gì hay?"

| V1 (Hiện tại) | V2 (Sau upgrade) |
|---------------|------------------|
| 1. SemanticRouter → RAG | 1. TravelAgent nhận query |
| 2. QueryStore match template "attractions" | 2. LLM quyết định: gọi `get_attractions()` |
| 3. SQL cố định | 3. Tool thực thi SQL |
| 4. Nếu không khớp → fail | 4. Nếu không khớp → `search_places()` (vector) |
| 5. Response | 5. LLM tổng hợp → Response |

**Response V2**:
```
Dạ, Bà Nà Hills có nhiều điểm tham quan thú vị ạ:
1. Cầu Vàng - Cây cầu nổi tiếng với bàn tay khổng lồ
2. Fantasy Park - Khu vui chơi trong nhà lớn nhất Việt Nam
3. Làng Pháp - Kiến trúc châu Âu cổ điển
4. Vườn hoa Le Jardin D'Amour - Vườn hoa đẹp

Bạn muốn biết thêm về điểm nào không nhé?
```

---

### Ví dụ 2: Query mơ hồ

**User**: "có gì vui ở Đà Nẵng?"

| V1 | V2 |
|----|----|
| Không tìm thấy "Đà Nẵng" trong SubProjects | LLM gọi `search_places("Đà Nẵng")` |
| → Trả lời generic hoặc fail | → Vector search tìm Bà Nà, Ngũ Hành Sơn... |
| | → LLM tổng hợp kết quả |

**Response V2**:
```
Dạ, ở Đà Nẵng có nhiều nơi thú vị lắm ạ:
- Bà Nà Hills với Cầu Vàng nổi tiếng
- Ngũ Hành Sơn với các hang động đẹp
- Biển Mỹ Khê được xếp hạng đẹp nhất thế giới
- Phố cổ Hội An chỉ cách 30 phút

Bạn muốn tìm hiểu chi tiết về nơi nào nhé?
```

---

### Ví dụ 3: Multi-step reasoning

**User**: "Tôi muốn xem video về Hội An và biết cách đi đến đó"

| V1 | V2 |
|----|----|
| Chỉ match được 1 template | LLM gọi 2 tools: |
| Mất thông tin | 1. `get_place_media("Hội An")` |
| | 2. `get_place_location("Hội An")` |
| | → Tổng hợp cả 2 kết quả |

**Response V2**:
```
Dạ, em có video về Hội An cho bạn xem:
📹 https://media.tbot.com/hoian/intro.mp4

Về cách đi ạ:
📍 Hội An nằm cách Đà Nẵng khoảng 30km về phía Nam
🚗 Đi xe từ sân bay Đà Nẵng khoảng 40 phút
🚌 Có bus số 1 từ trung tâm Đà Nẵng

Bạn cần thông tin gì thêm không nhé?
```

---

### Ví dụ 4: Chitchat (không đổi)

**User**: "Xin chào"

**Response**: "Xin chào bạn! Mình là T-Bot, hướng dẫn viên du lịch AI. Bạn muốn tìm hiểu về địa điểm nào không ạ? 😊"

---

## Hành Vi Mới

### ✅ Những gì TỐT HƠN

| Feature | Mô tả |
|---------|-------|
| **Thông minh hơn** | LLM tự chọn tool phù hợp thay vì match template |
| **Fallback tốt hơn** | Vector search khi SQL không tìm thấy |
| **Multi-step** | Có thể gọi nhiều tools trong 1 lượt |
| **Context aware** | Nhớ conversation history |
| **Async TTS** | Không blocking khi generate audio |

### ⚠️ Những điều CẦN LƯU Ý

| Aspect | Note |
|--------|------|
| **Latency** | Có thể chậm hơn ~0.5s do thêm LLM reasoning |
| **Token cost** | Dùng nhiều token hơn cho function calling |
| **Dependency** | Cần Ollama model hỗ trợ function calling |

---

## Flow Diagram Chi Tiết

```
User: "Bà Nà có gì vui?"
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    TravelAgent                           │
│                                                          │
│  System: "Bạn là T-Bot, hướng dẫn viên du lịch..."      │
│  User: "Bà Nà có gì vui?"                               │
│  Tools: [get_place_info, get_attractions, ...]          │
│                                                          │
│  → LLM thinks: "User hỏi về attractions"                │
│  → LLM returns: tool_call("get_attractions",            │
│                           {place_name: "Bà Nà"})        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    ToolExecutor                          │
│                                                          │
│  SELECT TOP 5 sp.SubProjectName, a.AttractionName...   │
│  FROM SubProjects sp                                    │
│  JOIN SubProjectAttractions a ON ...                    │
│  WHERE sp.SubProjectName LIKE '%Bà Nà%'                 │
│                                                          │
│  Result: [{name: "Cầu Vàng"}, {name: "Fantasy Park"}]   │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    TravelAgent (tiếp)                    │
│                                                          │
│  Tool result: [{name: "Cầu Vàng"}, ...]                 │
│                                                          │
│  → LLM synthesizes response                             │
│  → Returns: "Dạ, Bà Nà Hills có nhiều điểm vui..."     │
└─────────────────────────────────────────────────────────┘
         │
         ▼
User nhận response: "Dạ, Bà Nà Hills có nhiều điểm vui..."
```

---

## Capabilities Matrix

| Query Type | V1 | V2 |
|------------|:--:|:--:|
| "X ở đâu?" | ✅ | ✅ |
| "Giới thiệu X" | ✅ | ✅ |
| "Video về X" | ✅ | ✅ |
| "X có gì?" | ✅ | ✅ |
| "Có gì ở thành phố Y?" | ❌ | ✅ (vector search) |
| "Video X và cách đi đến" | ❌ | ✅ (multi-tool) |
| Follow-up questions | ⚠️ | ✅ (context memory) |
| Chitchat | ✅ | ✅ |
