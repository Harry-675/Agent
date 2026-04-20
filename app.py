import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from model import run_chat_round

st.set_page_config(page_title="工具增强聊天助手", page_icon="💬", layout="centered")
st.title("💬 工具增强聊天助手")
st.caption("支持多轮对话 + 网页搜索 + 股票查询")

if "history" not in st.session_state:
    st.session_state.history = []

history: list[BaseMessage] = st.session_state.history

for msg in history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.write(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.write(msg.content)

prompt = st.chat_input("例如：查一下 AAPL 最新股价，再告诉我上海明天天气")
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            reply = run_chat_round(history, prompt)
        st.write(reply)
