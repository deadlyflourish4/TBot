# import streamlit as st
# import uuid
# from Database.db import DatabaseConnector
# from Agent.SQLagent import SQLAgent
# from Agent.Answeragent import AnswerAgent   # ✅ import thêm AnswerAgent
# from SystemPrompt.SQLprompt import sql_prompt
# from SystemPrompt.Ansprompt import ans_prompt  # prompt AnswerAgent

# # ========== INIT ==========
# st.set_page_config(page_title="SQL Chatbot", layout="wide")

# if "conversations" not in st.session_state:
#     st.session_state.conversations = {}
# if "current_session" not in st.session_state:
#     st.session_state.current_session = None
# if "sql_agent" not in st.session_state:
#     db = DatabaseConnector(server="localhost", database="Orpheo")
#     st.session_state.sql_agent = SQLAgent(system_prompt=sql_prompt, db=db)
# if "answer_agent" not in st.session_state:
#     st.session_state.answer_agent = AnswerAgent(system_prompt=ans_prompt)

# # ========== SIDEBAR ==========
# with st.sidebar:
#     st.title("💬 Lịch sử trò chuyện")

#     if st.button("➕ Cuộc trò chuyện mới"):
#         new_id = str(uuid.uuid4())[:8]
#         st.session_state.conversations[new_id] = {
#             "name": f"Chat {len(st.session_state.conversations)+1}",
#             "messages": []
#         }
#         st.session_state.current_session = new_id
#         st.rerun()

#     if st.session_state.conversations:
#         for sid, data in st.session_state.conversations.items():
#             if st.button(data["name"], key=sid):
#                 st.session_state.current_session = sid
#                 st.rerun()
#     else:
#         st.info("Chưa có cuộc trò chuyện nào")

# # ========== MAIN ==========
# st.title("🤖 Orpheo Chatbot")

# if st.session_state.current_session is None:
#     st.warning("👉 Hãy tạo hoặc chọn một cuộc trò chuyện từ sidebar.")
# else:
#     session_data = st.session_state.conversations[st.session_state.current_session]

#     # Hiển thị lịch sử chat
#     for msg in session_data["messages"]:
#         with st.chat_message(msg["role"]):
#             if isinstance(msg["content"], dict):  # assistant message chứa cả SQL + answer
#                 st.markdown(f"**SQL:**\n```sql\n{msg['content']['sql']}\n```")
#                 if isinstance(msg["content"]["result"], list):
#                     st.dataframe(msg["content"]["result"])
#                 else:
#                     st.write(msg["content"]["result"])
#                 st.markdown(f"**Trả lời:** {msg['content']['answer']}")
#             else:
#                 st.markdown(msg["content"])

#     # Input chat
#     user_input = st.chat_input("Nhập câu hỏi...")
#     if user_input:
#         # User message
#         session_data["messages"].append({"role": "user", "content": user_input})
#         with st.chat_message("user"):
#             st.markdown(user_input)

#         # Bot xử lý
#         with st.chat_message("assistant"):
#             placeholder = st.empty()

#             # B1: SQLAgent sinh SQL + chạy DB
#             res_sql = st.session_state.sql_agent.get_query(
#                 session_id=st.session_state.current_session,
#                 query=user_input
#             )

#             # B2: AnswerAgent sinh câu trả lời tự nhiên
#             res_answer = st.session_state.answer_agent.get_answer(
#                 session_id=st.session_state.current_session,
#                 user_question=user_input,
#                 sql_query=res_sql["sql"],
#                 query_result=res_sql["result"]
#             )

#             # B3: Gộp kết quả
#             result = {
#                 "sql": res_sql["sql"],
#                 "result": res_sql["result"],
#                 "answer": res_answer
#             }

#             # Hiển thị ra màn hình
#             placeholder.markdown(f"**SQL:**\n```sql\n{result['sql']}\n```")
#             if isinstance(result["result"], list):
#                 st.dataframe(result["result"])
#             else:
#                 st.write(result["result"])
#             st.markdown(f"**Trả lời:** {result['answer']}")

#             # Lưu vào history
#             session_data["messages"].append({"role": "assistant", "content": result})
import streamlit as st
import uuid
from pipeline import GraphOrchestrator   # ✅ multi-agent orchestrator

# ========== INIT ==========
st.set_page_config(page_title="Orpheo Chatbot", layout="wide")

if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = GraphOrchestrator()

# ========== SIDEBAR ==========
with st.sidebar:
    st.title("💬 Lịch sử trò chuyện")

    if st.button("➕ Cuộc trò chuyện mới"):
        new_id = str(uuid.uuid4())[:8]
        st.session_state.conversations[new_id] = {
            "name": f"Chat {len(st.session_state.conversations)+1}",
            "messages": []
        }
        st.session_state.current_session = new_id
        st.rerun()

    if st.session_state.conversations:
        for sid, data in st.session_state.conversations.items():
            if st.button(data["name"], key=sid):
                st.session_state.current_session = sid
                st.rerun()
    else:
        st.info("Chưa có cuộc trò chuyện nào")

# ========== MAIN ==========
st.title("🤖 Orpheo Multi-Agent Chatbot")

if st.session_state.current_session is None:
    st.warning("👉 Hãy tạo hoặc chọn một cuộc trò chuyện từ sidebar.")
else:
    session_data = st.session_state.conversations[st.session_state.current_session]

    # Hiển thị lịch sử chat
    for msg in session_data["messages"]:
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], dict):  # assistant message (multi-agent output)
                st.markdown(f"**Route:** `{msg['content']['route']}`")

                if msg["content"].get("sql_query"):
                    st.markdown(f"**SQL:**\n```sql\n{msg['content']['sql_query']}\n```")

                if msg["content"].get("db_result"):
                    if isinstance(msg["content"]["db_result"], list):
                        st.dataframe(msg["content"]["db_result"])
                    else:
                        st.write(msg["content"]["db_result"])

                if msg["content"].get("search_result"):
                    st.markdown("**Search Result (rút gọn):**")
                    st.write(str(msg["content"]["search_result"])[:300] + "...")

                st.markdown(f"**Trả lời cuối:** {msg['content']['final_answer']}")
            else:
                st.markdown(msg["content"])

    # Input chat
    user_input = st.chat_input("Nhập câu hỏi...")
    if user_input:
        # User message
        session_data["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Bot xử lý
        with st.chat_message("assistant"):
            placeholder = st.empty()

            output = st.session_state.orchestrator.run(
                session_id=st.session_state.current_session,
                user_question=user_input
            )

            # Hiển thị kết quả
            placeholder.markdown(f"**Route:** `{output['route']}`")

            if output.get("sql_query"):
                st.markdown(f"**SQL:**\n```sql\n{output['sql_query']}\n```")

            if output.get("db_result"):
                if isinstance(output["db_result"], list):
                    st.dataframe(output["db_result"])
                else:
                    st.write(output["db_result"])

            if output.get("search_result"):
                st.markdown("**Search Result (rút gọn):**")
                st.write(str(output["search_result"])[:300] + "...")

            st.markdown(f"**Trả lời cuối:** {output['final_answer']}")

            # Lưu vào history
            session_data["messages"].append({"role": "assistant", "content": output})
