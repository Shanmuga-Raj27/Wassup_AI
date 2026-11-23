# Technical Memory & Architecture

> Authoritative technical reference and system memory for AI agents working in this repository. Built directly from live source inspection. Do not rely on outdated external documentation or READMEs.

---

## 1. Project Overview & Current Tech Stack

- **Product Name:** **Web Agent**
- **System Purpose:** An AI agent system combining LLMs with live multi-engine metasearch and deep web extraction to generate factual, hallucination-free, and source-grounded answers.
- **Backend Stack:**
  - **Language / Runtime:** Python 3.12+
  - **Packaging / Dependency Tool:** `uv` with `pyproject.toml` (`hatchling` build system)
  - **API Framework:** FastAPI (`fastapi>=0.165.0`), Uvicorn (`uvicorn>=0.54.0`)
  - **AI / Model SDK:** Google GenAI SDK (`google-genai>=3.6.1`)
    - Primary Model: `gemini-3.5-flash-lite`
    - Interaction Pattern: Interactions API (`client.interactions.create`) with stateful thread continuation (`previous_interaction_id`)
  - **Metasearch Engine:** DDGS (`ddgs>=9.16.1` - Dux Distributed Global Search metasearch library)
  - **Web Extraction / Scraping:** Trafilatura (`trafilatura>=2.3.1`), Crawl4AI (`crawl4ai>=0.9.5`)
  - **Configuration:** `python-dotenv>=1.2.4` via `backend/app/core/config.py`
- **Frontend Stack:** *(Blank - reserved for future development phase)*
- **Database Stack:** *(Blank - reserved for future development phase)*

---

## 2. Directory Structure & File Lookup Map

### 2.1 Repository Layout
```text
web-agent/
├── .agents/
│   ├── agent-memory.md              # Technical system memory & architecture map
│   └── agent-rules.md               # Operational guidelines and safety constraints
├── backend/
│   ├── app/
│   │   ├── apis/                    # FastAPI route modules (reserved for HTTP endpoints)
│   │   ├── core/
│   │   │   └── config.py            # Environment configuration & settings validation
│   │   └── services/
│   │       ├── gemini.py            # Main conversation orchestration & GenAI interactions loop
│   │       ├── prompt.py            # System prompts & dynamic augmented prompt builders
│   │       ├── web_scrap.py         # URL extraction & full page text scraping service
│   │       └── web_search.py        # DDGS metasearch client & context serializer
│   ├── main.py                      # FastAPI application entrypoint & health routes
│   ├── pyproject.toml               # Project metadata & Python dependencies
│   ├── requirements.txt             # Pinned package requirements
│   ├── streamlit/                   # Streamlit interactive testing & prototyping
│   │   ├── stream_ai.py             # Streamlit AI generation service
│   │   └── stream_app.py            # Streamlit chat interface & debug UI
│   ├── temp-test/                   # Standalone extraction test scripts
│   └── uv.lock                      # uv dependency lockfile
├── documentation/
│   ├── guides/                      # Practical developer guides
│   ├── phases/
│   │   └── phase-1-ddgs-gemini-integration.md  # Phase 1 integration documentation
│   ├── system design/               # System design documents
│   └── tutorials/                   # Step-by-step tutorials
│       └── ai-agent-rag-and-tool-calling-guide.md  # Comprehensive RAG & Agent concepts tutorial
└── frontend/                        # Frontend workspace (reserved for client application)
```

### 2.2 Responsibility → Exact File Path Lookup Map

| Responsibility | Target File Path | Key Functions / Classes | Status |
| :--- | :--- | :--- | :--- |
| **Settings & Env Loading** | `backend/app/core/config.py` | `Settings`, `settings.GEMINI_API_KEY` | Operational |
| **Metasearch Execution** | `backend/app/services/web_search.py` | `search_web()`, `format_search_results()` | Operational |
| **Prompt Engineering** | `backend/app/services/prompt.py` | `SYSTEM_PROMPT`, `augmented_prompt()` | Operational |
| **Agent Chat Orchestration** | `backend/app/services/gemini.py` | `client.chats.create()`, interactive loop, manual tool execution | Operational |
| **Model Error & Retry Handling** | `backend/app/services/error_handler.py` | `get_default_http_options()`, `handle_api_error()`, `handle_gemini_error()` | Operational |
| **Web Content Scraping** | `backend/app/services/web_scrap.py` | Web scraping logic (`trafilatura` / `crawl4ai`) | In Progress |
| **FastAPI Root Server** | `backend/main.py` | `app`, `/`, `/health` endpoints | Operational |
| **Streamlit AI Service** | `backend/streamlit/stream_ai.py` | `generate_agent_response()` | Operational |
| **Streamlit Debug UI** | `backend/streamlit/stream_app.py` | Chat interface, debug expander, session state | Operational |
| **Phase 1 Specs & Reference** | `documentation/phases/phase-1-ddgs-gemini-integration.md` | System diagrams, RAG pipeline specs | Complete |
| **Phase 1.5 Implementation Plan** | `.agents/agents_plan/phase-1.5-manual-tool-calling.md` | Manual tool calling & DDGS step-by-step execution plan | Ready for Implementation |
| **Agent & RAG Tutorial** | `documentation/tutorials/ai-agent-rag-and-tool-calling-guide.md` | Concepts guide: RAG patterns, tools & agents | Complete |
| **Agent Operational Rules** | `.agents/agent-rules.md` | Tech stack bounds, privacy rules, bash limits | Active |

---

## 3. Overall System Architecture

```text
+=================================================================================+
|                              PRESENTATION LAYER                                 |
|  - Terminal CLI Loop (backend/app/services/gemini.py)                           |
|  - FastAPI HTTP Endpoints (backend/main.py)                                     |
|  - Streamlit UI / Web Client (Planned)                                          |
+=================================================================================+
                                       │
                                       ▼
+=================================================================================+
|                          APPLICATION SERVICES LAYER                             |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  | prompt.py                                                                 |  |
|  | - SYSTEM_PROMPT: Sets constraints, citation rules, and brevity guidelines |  |
|  | - augmented_prompt(): Merges search context with user questions           |  |
|  +---------------------------------------------------------------------------+  |
|        ▲                                                                        |
|        │ Formatted Context                                                      |
|  +-----------------------------------+   +-----------------------------------+  |
|  | web_search.py                     |   | web_scrap.py                      |  |
|  | - search_web(query, max_results)  |   | - URL detection in prompt         |  |
|  | - format_search_results(results)  |   | - Clean page text extraction      |  |
|  +-----------------------------------+   +-----------------------------------+  |
+=================================================================================+
       │ Keyword Query                                        │ Grounded Payload
       ▼                                                      ▼
+======================================+    +=====================================+
|       DDGS METASEARCH ENGINE         |    |    GOOGLE GENAI INTERACTIONS API    |
| - Multi-engine query aggregation     |    | - Stateful memory continuation      |
| - No API keys required               |    | - Uses previous_interaction_id      |
| - Output: title, href, body snippet  |    | - Model: gemini-3.5-flash-lite      |
+======================================+    +=====================================+
```

### Architectural Principles:
1. **Separation of Concerns:** Metasearch (`web_search.py`), page scraping (`web_scrap.py`), prompt composition (`prompt.py`), and LLM invocation (`gemini.py`) remain completely decoupled.
2. **Stateful Conversation via Interactions API:** Session history is tracked server-side by Google GenAI using `previous_interaction_id`, preventing the need to accumulate large chat histories in local memory.
3. **Fail-Safe Search Execution:** Metasearch queries run under strict timeout safeguards (`timeout=5`) to prevent backend hangs on slow proxy routes.

---

## 4. Current Data Flow Pipeline

```text
[1. User Input]
       │
       ▼
[2. Query Dispatch] ──────────> search_web(query, max_results=3)
       │                        └─ Queries DDGS across multiple search engines
       │                        └─ Returns list of dicts: {'title', 'href', 'body'}
       ▼
[3. Context Serialization] ───> format_search_results(search_data)
       │                        └─ Transforms dictionaries into numbered markdown context
       ▼
[4. Prompt Augmentation] ─────> augmented_prompt(user_question, search_context)
       │                        └─ Fuses context block + question into single payload string
       ▼
[5. Model Request] ───────────> client.interactions.create()
       │                        ├─ model: "gemini-3.5-flash-lite"
       │                        ├─ input: final_input (augmented prompt string)
       │                        ├─ system_instruction: SYSTEM_PROMPT
       │                        └─ previous_interaction_id: previous_id
       ▼
[6. Context Continuity] ──────> previous_id = response.id
       │                        └─ Saves interaction token for multi-turn conversational memory
       ▼
[7. Output Delivery] ─────────> print("AI:", response.output_text)
                                └─ Delivers concise, source-cited factual response
```
