# Query-Oriented RAG Pipeline

## Overview

A Retrieval-Augmented Generation system that selects and parameterizes **query templates** instead of generating free-form queries. This approach ensures controlled, auditable database access while leveraging LLM intelligence for intent classification.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INPUT                                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       INTENT CLASSIFIER                             │
│                    (Chitchat vs RAG)                                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
         ┌────────────┐                  ┌─────────────┐
         │  CHITCHAT  │                  │     RAG     │
         └─────┬──────┘                  │   BRANCH    │
               │                         └──────┬──────┘
               ▼                                │
         [Direct LLM]                           ▼
               │                         ┌─────────────┐
               │                         │ REFLECTION  │ → Synthesized Query
               │                         └──────┬──────┘
               │                                ▼
               │                         ┌─────────────┐
               │                         │     NER     │ → Extracted Entities
               │                         └──────┬──────┘
               │                                ▼
               │                         ┌─────────────┐
               │                         │   VECTOR    │ → Query Template
               │                         │  RETRIEVAL  │
               │                         └──────┬──────┘
               │                                ▼
               │                         ┌─────────────┐
               │                         │  VARIABLE   │ → Bound Query
               │                         │   BINDING   │
               │                         └──────┬──────┘
               │                                ▼
               │                         ┌─────────────┐
               │                         │ SQL SERVER  │ → Results
               │                         │   EXECUTE   │
               │                         └──────┬──────┘
               │                                │
               │                    ┌───────────┴───────────┐
               │                    ▼                       ▼
               │              results = []            results ≠ []
               │                    │                       │
               │                    ▼                       │
               │             ┌─────────────┐                │
               │             │   SEARCH    │ (Fallback)     │
               │             │   ENGINE    │                │
               │             └──────┬──────┘                │
               │                    │                       │
               │                    └───────────┬───────────┘
               │                                ▼
               │                         ┌─────────────┐
               │                         │     LLM     │ → Natural Response
               │                         │  RESPONSE   │
               │                         └──────┬──────┘
               │                                │
               └────────────────┬───────────────┘
                                ▼
                          ┌─────────────┐
                          │   OUTPUT    │
                          └─────────────┘
```

---

## Core Components

### 1. Reflection Module

**Purpose:** Summarize multi-turn conversation into a single, clear question.

| Input | Output |
|-------|--------|
| Conversation history | Synthesized query (standalone question) |

**Example:**
```
User: "Dinh Độc Lập ở đâu?"
User: "Giờ mở cửa thì sao?"
→ Synthesized: "Giờ mở cửa của Dinh Độc Lập là mấy giờ?"
```

---

### 2. NER Module (Fine-tuned)

**Purpose:** Extract domain-specific entities from synthesized query.

**Entity Types:**
| Entity | Example |
|--------|---------|
| `LOC` | "Dinh Độc Lập", "Bảo tàng Chứng tích" |
| `DATE` | "hôm nay", "thứ 7" |
| `TIME` | "sáng", "10 giờ" |

---

### 3. Query Template Store

**Schema:**
```json
{
  "key": "get_location_opening_hours",
  "intent": "location_hours_query",
  "description": "Get opening/closing hours for a location",
  "query_template": "SELECT opening_time, closing_time FROM attractions WHERE name = :location",
  "variables": ["location"],
  "required": ["location"]
}
```

**Storage:** JSON file or SQLite (for ~50 templates)

---

### 4. LLM Selector

**Input:**
- `user_query`: Synthesized question
- `extracted_entities`: From NER
- `retrieved_docs`: Top-k candidate templates

**Output:**
```json
{
  "intent": "location_hours_query",
  "query_key": "get_location_opening_hours",
  "compiled_query": "SELECT opening_time, closing_time FROM attractions WHERE name = :location",
  "parameters": {
    "location": "Independence Palace"
  },
  "ready_to_execute": true,
  "missing_variables": []
}
```

---

### 5. Search Engine Fallback

**Trigger:** When SQL query returns empty results

**Purpose:** Prevent LLM from using outdated knowledge by searching real-time data sources.

---

## Variable Binding

| Variable Type | Source | Example |
|---------------|--------|---------|
| **System vars** | Environment/Config | `{prefix}`, `{db_schema}` |
| **Session vars** | API context | `{project_id}`, `{user_id}` |
| **Extracted vars** | NER output | `{location}`, `{date}` |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Template-based queries | Prevents SQL injection, ensures auditability |
| Single query focus | Simpler pipeline, add multi-query later if needed |
| Search as fallback | Only invoked when RAG fails, reduces cost |
| Fine-tuned NER | Domain-specific entities need specialized model |

---

## Future Enhancements

1. **Multi-query support** - For comparison questions
2. **Query chaining** - When query B depends on result of query A
3. **Confidence scoring** - Reject low-confidence template matches
4. **Template versioning** - For schema migrations
