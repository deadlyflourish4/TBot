import streamlit as st
from PIL import Image

st.title("Chatbot upload ảnh kiểu ChatGPT")

# Lưu hội thoại
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render lại hội thoại
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image" in msg:
            st.image(msg["image"], use_column_width=True)

# Ô chat text
if prompt := st.chat_input("Nhập tin nhắn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Upload ảnh ngay dưới khung chat
uploaded_file = st.file_uploader("📷 Upload ảnh", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
if uploaded_file:
    img = Image.open(uploaded_file)
    st.session_state.messages.append(
        {"role": "user", "content": "Đã gửi một ảnh:", "image": img}
    )
    with st.chat_message("user"):
        st.image(img, use_column_width=True)
