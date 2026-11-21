# backend/streamlit/stream_app.py
# Streamlit UI for testing, debugging, and prototyping the Web Agent

import sys
from pathlib import Path
import streamlit as st

# Add current folder and backend directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
for dir_path in (CURRENT_DIR, BACKEND_DIR):
    if str(dir_path) not in sys.path:
        sys.path.insert(0, str(dir_path))

# Import AI generation function from sibling module stream_ai.py
from stream_ai import generate_agent_response

# Configure Streamlit page layout and appearance
st.set_page_config(
    page_title="Web Agent Prototype",
    page_icon="🌐",
    layout="wide"
)

# Header Section
st.title("🌐 Web Agent: Search & Chat Prototype")
st.caption("Testing and debugging interface powered by Google Gemini and DDGS Metasearch")

# Sidebar Configuration and Debugging Controls
with st.sidebar:
    st.header("⚙️ Agent Controls")
    
    # Slider to dynamically adjust the number of search results retrieved
    max_search_results = st.slider("Max Search Results (DDGS)", min_value=1, max_value=6, value=3)

    # Button to reset chat history and conversation memory
    if st.button("🗑️ Clear Chat & Memory", use_container_width=True):
        st.session_state.messages = []
        st.session_state.previous_id = None
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Session Debug Info")
    st.caption("Model: `gemini-3.5-flash-lite`")
    current_tid = st.session_state.get("previous_id", None)
    st.caption(f"Interaction ID: `{current_tid if current_tid else 'None (Fresh Thread)'}`")

# Initialize persistent session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize persistent session state for conversation memory thread id
if "previous_id" not in st.session_state:
    st.session_state.previous_id = None

# Render existing chat history on each script rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If debug context exists for this response, show it inside an expander
        if message.get("debug_context"):
            with st.expander("🔍 View Retrieved Web Context"):
                st.text(message["debug_context"])

# Capture new user input from the chat input box
if user_prompt := st.chat_input("Ask anything (e.g. 'What is the latest release of Python?')..."):
    # 1. Display user message in chat container
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # 2. Generate and display assistant response
    with st.chat_message("assistant"):
        # Visual status indicator while external search and LLM calls run
        with st.status("Searching the web & generating answer...", expanded=False) as status_box:
            st.write("Fetching live web snippets via DDGS metasearch...")
            
            # Execute backend agent service
            ai_reply, search_context, new_interaction_id = generate_agent_response(
                prompt=user_prompt,
                previous_interaction_id=st.session_state.previous_id,
                max_results=max_search_results
            )
            
            # Update conversation memory token in session state
            st.session_state.previous_id = new_interaction_id
            status_box.update(label="Response generated successfully!", state="complete")

        # Render the final AI answer text
        st.markdown(ai_reply)

        # Render collapsible debug box for the raw search context
        with st.expander("🔍 View Retrieved Web Context"):
            st.text(search_context)

        # Store assistant response and debug context in session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_reply,
            "debug_context": search_context
        })
