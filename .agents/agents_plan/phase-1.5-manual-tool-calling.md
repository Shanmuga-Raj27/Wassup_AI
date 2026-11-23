# Phase 1.5 Technical Implementation Plan: Autonomous Manual Tool Calling

**Document Target:** `.agents/agents_plan/phase-1.5-manual-tool-calling.md`  
**Audience:** AI Agents and Human Developers (AI-Assisted Engineering Workflow)  
**Status:** Approved Technical Plan  
**Objective:** Transition Web Agent from Phase 1 (Eager RAG Metasearch) to Phase 1.5 (Autonomous LLM-Governed Manual Tool Calling) using `ddgs` and Google GenAI SDK (`google-genai`).

---

## 1. Architectural Overview & Boundaries

### 1.1 Scope of Phase 1.5
- **Goal:** Enable the LLM to autonomously evaluate user intent, decide whether an external web search is needed, formulate optimized search keywords, and cite source URLs in its grounded response.
- **Manual Tool Calling Principle:** The system disables Automatic Function Calling (`automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)`). The Python host application intercepts the model's tool calls, executes the local DDGS search, and passes a `FunctionResponse` back to the model in an explicit second turn.
- **Non-Goals (Deferred to Phase 2):**
  - Full-page text scraping via Trafilatura / Crawl4AI.
  - Multi-hop search loops (searching, evaluating, re-searching).
  - Database persistence for chat threads.

### 1.2 Strict UI Layer Separation
To maintain clean architecture, presentation layers remain completely independent:
- **CLI Presentation Layer (`backend/app/services/gemini.py`):** Standalone terminal REPL running its own chat session, handling command-line input, printing tool call metadata, and displaying grounded outputs.
- **Streamlit Presentation Layer (`backend/streamlit/`):** Web UI (`stream_app.py`) driven by an isolated service module (`stream_ai.py`), maintaining state in `st.session_state` and rendering real-time UI status widgets.
- **Shared Foundation (`backend/app/services/`):** Both UIs consume identical, decoupled backend services (`web_search.py` and `prompt.py`). Neither UI imports or couples with the other.

---

## 2. Component Responsibility & Target File Map

| Component Layer | File Path | Phase 1 Role | Phase 1.5 Role |
| :--- | :--- | :--- | :--- |
| **Shared Service: Metasearch** | `backend/app/services/web_search.py` | Standalone DDGS execution & formatting | Exports `search_web_tool(query, max_results)` for Gemini SDK tool registration |
| **Shared Service: Prompt & Rules** | `backend/app/services/prompt.py` | Augmented prompt string concatenator | Defines `SYSTEM_PROMPT` with autonomous tool routing, query distillation, and citation guidelines |
| **Presentation: Terminal CLI** | `backend/app/services/gemini.py` | CLI loop with eager search & Interactions API | Interactive CLI with `chats.create` and manual two-turn tool interception |
| **Streamlit Service Layer** | `backend/streamlit/stream_ai.py` | Eager search generator with Interactions API | Provides `create_agent_chat()` factory and `run_chat_turn()` manual execution handler |
| **Presentation: Streamlit UI** | `backend/streamlit/stream_app.py` | Chat UI with static search status block | Chat UI with dynamic status indicators (`st.status`) reflecting real-time tool decisions |

---

## 3. Step-by-Step Implementation Sequence

The implementation proceeds in strict dependency order: foundation services first, followed by independent presentation layers.

```text
Step 1: Metasearch Tool Wrapper (backend/app/services/web_search.py)
   │
   ▼
Step 2: System Steering Prompt (backend/app/services/prompt.py)
   │
   ├──────────────────────────────┬──────────────────────────────┐
   ▼                                                             ▼
Step 3: CLI Interface                                         Step 4: Streamlit AI Service
(backend/app/services/gemini.py)                              (backend/streamlit/stream_ai.py)
                                                                 │
                                                                 ▼
                                                              Step 5: Streamlit Web UI
                                                              (backend/streamlit/stream_app.py)
```

---

## 4. Code Specifications: Before vs. After (Key Snippets Only)

### Step 1: Update Metasearch Tool Wrapper (`backend/app/services/web_search.py`)

#### Purpose
Expose a single callable tool function `search_web_tool` with clean parameter typing that Gemini can register in its tool catalog, wrapping existing `search_web` and `format_search_results` functions.

#### Before (Phase 1)
```python
# Standalone functions; no single tool entrypoint for Gemini
def search_web(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    # ... executes DDGS search ...
    pass

def format_search_results(results: List[Dict[str, Any]]) -> str:
    # ... formats list into markdown string ...
    pass
```

#### After (Phase 1.5)
```python
# Added callable tool wrapper registered with Gemini
def search_web_tool(query: str, max_results: int = 3) -> str:
    # Metasearch tool looking up live facts, news, and external documentation
    # Parameter query: Concise search keywords formulated to find relevant factual information
    # Parameter max_results: Number of web results to retrieve (default is 3)
    raw_results = search_web(query=query, max_results=max_results)
    return format_search_results(raw_results)
```

#### Key Technical Notes
- Do not modify existing `search_web()` or `format_search_results()` logic; keep timeout safeguards (`timeout=5`) intact.
- Use single-line `#` comments for all documentation and explanations per project guidelines.

---

### Step 2: Update System Steering Prompt (`backend/app/services/prompt.py`)

#### Purpose
Replace Phase 1 eager prompt assumptions with agentic routing rules instructing Gemini when to invoke `search_web_tool`, how to formulate search keywords, and how to cite source URLs.

#### Before (Phase 1)
```python
# Assumes search results are unconditionally concatenated into every prompt
SYSTEM_PROMPT = """You are a fast, concise, and helpful AI web agent.
Rules:
1. Keep your answers brief, direct, and factual (2-4 sentences or clear bullet points).
2. When web search results are provided, use them as your primary source of truth.
..."""

def augmented_prompt(user_question: str, search_context: str) -> str:
    # Manually concatenates search context and query
    return f"Web Search Results:\n{search_context}\n\nUser Question:\n{user_question}"
```

#### After (Phase 1.5)
```python
# Autonomous tool steering prompt; augmented_prompt is deprecated in tool calling
SYSTEM_PROMPT = """You are a fast, factual, and concise AI web agent.

Decision & Tool Guidelines:
1. When asked about recent events, current information, real-time facts, sports scores, or external documentation, call the `search_web_tool`.
2. Do NOT invoke search for basic conversational greetings, general logic, arithmetic, or programming theory that does not require external web data.
3. Formulate concise, high-signal keyword queries when invoking `search_web_tool` (e.g., convert "Can you tell me who won the cricket match yesterday?" to "cricket match result yesterday").
4. Inspect the URLs provided in the search results and cite them as markdown links when delivering factual answers.
5. If the search results do not contain the answer, explicitly state that the information was not found rather than guessing.
6. Keep final answers concise, direct, and well-structured (2 to 4 sentences or bullet points).
"""
```

#### Key Technical Notes
- `augmented_prompt()` can remain in the file for backwards compatibility with legacy tests, but is not used in Phase 1.5 tool calling flows.

---

### Step 3: Implement CLI Interface with Manual Tool Calling (`backend/app/services/gemini.py`)

#### Purpose
Refactor the terminal CLI from the single-turn Interactions API with eager search to a multi-turn chat session (`client.chats.create`) with manual tool interception.

#### Before (Phase 1)
```python
# Eager search executed on every user prompt before contacting Gemini
search_data = search_web(prompt, max_results=3)
search_context = format_search_results(search_data)
final_input = augmented_prompt(user_question=prompt, search_context=search_context)

response = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input=final_input,
    system_instruction=SYSTEM_PROMPT,
    previous_interaction_id=previous_id
)
previous_id = response.id
print("AI:", response.output_text)
```

#### After (Phase 1.5)
```python
# Chat session with manual tool calling disabled from auto-executing
config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[search_web_tool],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)
chat = client.chats.create(model="gemini-2.5-flash", config=config)

# Turn 1: Dispatch user prompt to model
response = chat.send_message(user_prompt)

# Turn 2: Intercept and execute tool manually if requested
if response.function_calls:
    for tool_call in response.function_calls:
        if tool_call.name == "search_web_tool":
            search_query = tool_call.args.get("query", user_prompt)
            max_res = int(tool_call.args.get("max_results", 3))
            
            print(f"[Executing DDGS] Searching for: '{search_query}'...")
            tool_output = search_web_tool(query=search_query, max_results=max_res)
            
            # Send tool execution result back to Gemini
            response = chat.send_message(
                types.Part.from_function_response(
                    name=tool_call.name,
                    response={"result": tool_output}
                )
            )

print("\nAI:", response.text)
```

#### Key Technical Notes
- Model configured as `gemini-2.5-flash` for reliable function calling support.
- Loop gracefully handles turns where `response.function_calls` is empty (direct parametric answers).

---

### Step 4: Refactor Streamlit AI Service (`backend/streamlit/stream_ai.py`)

#### Purpose
Decouple the chat session creation and turn resolution into reusable service functions, returning execution metadata (`tool_executed`, `tool_details`) to power the Streamlit UI.

#### Before (Phase 1)
```python
# Monolithic function tying search and model call together
def generate_agent_response(prompt: str, previous_interaction_id: str | None = None, max_results: int = 3):
    search_data = search_web(prompt, max_results=max_results)
    search_context = format_search_results(search_data)
    final_input = augmented_prompt(user_question=prompt, search_context=search_context)
    response = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=final_input,
        system_instruction=SYSTEM_PROMPT,
        previous_interaction_id=previous_interaction_id
    )
    return response.output_text, search_context, response.id
```

#### After (Phase 1.5)
```python
# Factory creating a tool-enabled chat session
def create_agent_chat():
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[search_web_tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )
    return client.chats.create(model="gemini-2.5-flash", config=config)

# Turn execution handler with manual tool interception and metadata capture
def run_chat_turn(chat, user_prompt: str):
    response = chat.send_message(user_prompt)
    tool_executed = False
    tool_details = None

    if response.function_calls:
        tool_call = response.function_calls[0]
        if tool_call.name == "search_web_tool":
            tool_executed = True
            query = tool_call.args.get("query", user_prompt)
            max_results = int(tool_call.args.get("max_results", 3))
            search_context = search_web_tool(query=query, max_results=max_results)
            
            tool_details = {
                "tool_name": tool_call.name,
                "query": query,
                "search_context": search_context
            }
            
            response = chat.send_message(
                types.Part.from_function_response(
                    name=tool_call.name,
                    response={"result": search_context}
                )
            )

    return response.text, tool_executed, tool_details
```

#### Key Technical Notes
- Returns a 3-element tuple `(ai_reply, tool_executed, tool_details)` allowing the UI layer to conditionally display status badges and debug drawers.

---

### Step 5: Update Streamlit Presentation Layer (`backend/streamlit/stream_app.py`)

#### Purpose
Update the Streamlit interface to store the persistent `chat` session in `st.session_state` and dynamically render status boxes based on whether a tool was called.

#### Before (Phase 1)
```python
# Stored raw string token previous_id; ran status box unconditionally
if "previous_id" not in st.session_state:
    st.session_state.previous_id = None

with st.status("Searching the web & generating answer...", expanded=False) as status_box:
    ai_reply, search_context, new_interaction_id = generate_agent_response(
        prompt=user_prompt,
        previous_interaction_id=st.session_state.previous_id,
        max_results=max_search_results
    )
    st.session_state.previous_id = new_interaction_id
    status_box.update(label="Response generated successfully!", state="complete")
```

#### After (Phase 1.5)
```python
# Stores active chat object in session state
if "chat" not in st.session_state:
    st.session_state.chat = create_agent_chat()

# In chat input handler:
with status_placeholder.status("Thinking...", expanded=True) as status_box:
    ai_reply, tool_used, tool_info = run_chat_turn(
        chat=st.session_state.chat,
        user_prompt=user_prompt
    )
    if tool_used and tool_info:
        status_box.update(
            label=f"Searched DDGS for: '{tool_info['query']}'",
            state="complete",
            expanded=False
        )
    else:
        status_box.update(
            label="Answered directly (no search needed)",
            state="complete",
            expanded=False
        )

# Render debug expander only when search was actually performed
debug_text = tool_info["search_context"] if (tool_used and tool_info) else None
if debug_text:
    with st.expander("🔍 View Retrieved Web Context"):
        st.text(debug_text)
```

#### Key Technical Notes
- Clear chat button in sidebar now resets `st.session_state.chat = create_agent_chat()` and empties `st.session_state.messages`.
- No search queries are executed during basic chat or theory questions.

---

## 5. Verification & Acceptance Criteria

To validate Phase 1.5 implementation across both interfaces:

| Test ID | Test Category | Prompt Input | Expected Decision & Behavior | Verification Check |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Conversational Chat | `"Hello! How are you?"` | No tool called (`tool_executed=False`). Model answers from weights. | Response time < 1.5s; Streamlit displays *"Answered directly (no search needed)"*; CLI shows no search logs. |
| **TC-02** | General Knowledge | `"Explain recursion in Python with a brief example."` | No tool called. Model answers parametric programming theory directly. | Zero DDGS requests sent; no web links in output. |
| **TC-03** | Real-Time Factual Query | `"What is the latest stable release of Python?"` | Tool triggered (`tool_executed=True`). Model distills query (e.g. `"latest stable release Python"`). | DDGS executes; output contains markdown links with verified URLs; Streamlit status shows exact distilled query. |
| **TC-04** | Current News / Sports | `"Who won the latest Premier League match between Arsenal and Chelsea?"` | Tool triggered. Specific search keywords used. | Search context retrieved; model cites match facts and primary source link. |
| **TC-05** | Fallback / Negative Search | `"What is the exact secret codename of project X9999Z9999?"` | Tool triggered; DDGS returns empty/no results. | Model explicitly states information was not found rather than hallucinating facts. |

---

## 6. Agent Rules & Operational Compliance Checklist

- [x] **Context Lookup:** Read `.agents/agent-rules.md` and `.agents/agent-memory.md` before designing plan.
- [x] **Dependency Discipline:** No new Python dependencies added (uses existing `google-genai`, `ddgs`, `fastapi`, `streamlit`).
- [x] **UI Decoupling:** CLI (`gemini.py`) and Streamlit (`stream_app.py`) are strictly separated and do not cross-import.
- [x] **No Diagrams:** Pure structured text, markdown tables, and code snippets only; zero Mermaid or ASCII box diagrams.
- [x] **Code Explanation Syntax:** Important Before/After snippets only (no full code dumps); strictly single-line `#` comments used in code snippets.
- [x] **Privacy & Path Discipline:** Repository-relative paths used throughout; zero secrets or device usernames exposed.
