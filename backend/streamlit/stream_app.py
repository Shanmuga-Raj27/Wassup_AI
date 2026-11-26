# backend/streamlit/stream_app.py
# Streamlit UI for testing, debugging, and prototyping the Web Agent

import sys
from pathlib import Path
import streamlit as st

# Configure system paths for module discovery
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
for dir_path in (CURRENT_DIR, BACKEND_DIR):
    if str(dir_path) not in sys.path:
        sys.path.insert(0, str(dir_path))

from app.services.gemini import create_agent_chat, run_chat_turn

# Configure Streamlit page metadata and layout
st.set_page_config(
    page_title="Wassup AI",
    page_icon="🌐",
    layout="wide"
)

# Header Section
st.title("🌐 Wassup AI")
st.caption("Web Agent Search, Scrape & Understand Pages")

# Sidebar Configuration and Debugging Controls
with st.sidebar:
    st.header("⚙️ Agent Controls")

    # Button to reset conversation history and create a fresh chat session
    if st.button("🗑️ Clear Chat & Memory", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat = create_agent_chat()
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Session Debug Info")
    st.caption("Model: `gemini-3.5-flash-lite`")
    st.caption("Execution Mode: `Manual Tool Calling (Disabled AFC)`")
    st.caption("Tools: `DDGS Metasearch + Trafilatura Scraper`")

# Initialize persistent chat session in session state
if "chat" not in st.session_state:
    st.session_state.chat = create_agent_chat()

# Initialize persistent message history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing chat history on each script rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("debug_context"):
            with st.expander("🔍 View Retrieved Web Context"):
                st.text(message["debug_context"])

# Capture new user input from the chat input box
if user_prompt := st.chat_input("Ask anything (e.g. 'What is the latest release of Python?')..."):
    # 1. Display and record user message
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # 2. Generate and display assistant response
    with st.chat_message("assistant"):
        status_placeholder = st.empty()

        # Visual status indicator updating dynamically based on tool execution
        with status_placeholder.status("Thinking...", expanded=True) as status_box:
            ai_reply, tool_used, tool_info = run_chat_turn(
                chat=st.session_state.chat,
                user_prompt=user_prompt
            )

            if tool_used and tool_info and tool_info.get("steps"):
                step_labels = []
                debug_sections = []
                for step in tool_info["steps"]:
                    if step["tool_name"] == "search_web_tool":
                        cat = step.get("category", "text").capitalize()
                        step_labels.append(f"Searched DDGS ({cat}): '{step['query']}'")
                        debug_sections.append(f"--- DDGS Search ({cat}): {step['query']} ---\n{step['output']}")
                    elif step["tool_name"] == "scrape_url_tool":
                        step_labels.append(f"Scraped: {step['url']}")
                        debug_sections.append(f"--- Trafilatura Scrape: {step['url']} ---\n{step['output']}")

                status_box.update(
                    label=" -> ".join(step_labels),
                    state="complete",
                    expanded=False
                )
                debug_text = "\n\n".join(debug_sections)
            else:
                status_box.update(
                    label="Answered directly (no tools needed)",
                    state="complete",
                    expanded=False
                )
                debug_text = None

        # Render final grounded AI response
        st.markdown(ai_reply)

        # Render debug expander if external web context was retrieved
        if debug_text:
            with st.expander("🔍 View Retrieved Web Context"):
                st.text(debug_text)

        # Store assistant response in session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_reply,
            "debug_context": debug_text,
        })
