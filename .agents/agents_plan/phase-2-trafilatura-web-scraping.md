# Phase 2 Step-by-Step Implementation Plan: Trafilatura Web Scraping

**Document Target:** `.agents/agents_plan/phase-2-trafilatura-web-scraping.md`  
**Reference Architecture:** `documentation/dev_docs/phases/phase-2-trafilatura-web-scraping.md`  
**Audience:** AI Coding Agents and Human Backend Developers  
**Status:** Complete  
**Scope:** Phase 2 — Add on-demand static webpage extraction via `trafilatura` (`crawl4ai` explicitly excluded for a future JS/SPA phase).

---

## 1. Repository & Architecture Discovery Summary

### Verified Current State
- **Configuration (`backend/app/core/config.py`):** Loads `GEMINI_API_KEY` from `.env` via `Settings`.
- **Error & Retry Handling (`backend/app/services/error_handler.py`):** Provides `get_default_http_options()` (4 retry attempts, 2.0s initial delay, HTTP `[408, 429, 500, 502, 503, 504]`), `handle_api_error()`, and `handle_unexpected_error()`.
- **Web Search (`backend/app/services/web_search.py`):** Exposes `search_web_tool(query, category, timelimit, max_results)` using DDGS with density filtering (`filter_dense_results`).
- **Orchestration (`backend/app/services/gemini.py`):** Exports `create_agent_chat()` and `run_chat_turn(chat, user_prompt)` using `google-genai` (`gemini-3.5-flash-lite`), `automatic_function_calling` disabled, and a manual tool loop (`max_tool_turns = 3`). Also acts as the terminal CLI entrypoint.
- **UI Communication (`backend/streamlit/stream_app.py`):** Imports `create_agent_chat` and `run_chat_turn` directly from `app.services.gemini` (not via HTTP/FastAPI; `backend/app/apis/` is currently empty and `backend/main.py` only serves `/` and `/health`).
- **Installed Dependencies (`backend/pyproject.toml`):** `trafilatura>=2.3.1` is already installed and tested in `backend/temp-test/test-trafilatura.py`.

### Identified Gaps vs. Phase 2 Architecture
1. `backend/app/services/web_scrap.py` exists as an empty placeholder (`0` bytes).
2. `gemini.py` only registers `[search_web_tool]` and stores a single `tool_details` dict, which overwrites earlier calls if Gemini chains Search $\rightarrow$ Scrape in one turn.
3. `backend/app/services/prompt.py` has no instructions for `scrape_url_tool` and enforces a strict `< 70 words` cap that conflicts with summarizing scraped articles.
4. `backend/streamlit/stream_app.py` expects a single-tool `tool_info` dict (`query`, `category`, `search_context`) and cannot display multi-step Search + Scrape traces.
5. `backend/streamlit/stream_ai.py` duplicates `gemini.py` functions (`create_agent_chat`, `run_chat_turn`) but is unused by `stream_app.py`, risking drift if left out of sync.

---

## 2. Pre-Flight & Baseline Check

Before modifying any source file, verify the baseline environment and existing modules:

1. **Syntax & Import Check:**
   - Command: `backend/.venv/bin/python -m py_compile backend/app/services/*.py backend/streamlit/*.py`
   - Expected: Exit code `0` with no syntax or import errors.
2. **Trafilatura Availability Check:**
   - Command: `backend/.venv/bin/python -c "import trafilatura; print(trafilatura.__version__)"`
   - Expected: Prints installed `trafilatura` version (`>=2.3.1`) without installing new packages.
3. **CLI Startup Baseline:**
   - Command: `printf "exit\n" | backend/.venv/bin/python backend/app/services/gemini.py`
   - Expected: Cleanly starts and exits without errors.

---

## 3. Ordered Implementation Steps

### Step 1: Implement Trafilatura Scraper Service

* **Goal & Scope:**
  - Implement URL validation, HTML fetching, main-content extraction, metadata lookup, and token-safe character truncation in `web_scrap.py`.
  - Expose `scrape_url_tool(url: str) -> str` for Gemini tool registration.
  - Out of scope: `crawl4ai`, headless browsers, async scraping, or multi-URL crawling.
* **Target File:**
  - `backend/app/services/web_scrap.py` `[EMPTY PLACEHOLDER]`
* **Before Changes:**
  - File is completely empty (`0` bytes); no scraping functions exist.
* **After Changes:**
  - Adds `scrape_webpage()` with HTTP(S) validation, graceful failure messages when `fetch_url()` returns `None` (blocked/JS sites), and `max_chars` capping to protect LLM latency and token budget.

```python
# After: Core Trafilatura extraction and tool wrapper in backend/app/services/web_scrap.py
from urllib.parse import urlparse
from trafilatura import fetch_url, extract, extract_metadata


def scrape_webpage(url: str, max_chars: int = 6000) -> str:
    # Reject invalid schemes before issuing network requests
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "Invalid URL provided. Only valid http or https links can be scraped."

    html = fetch_url(url)
    if not html:
        return "Unable to download webpage (the site may block automated requests or require JavaScript)."

    # Strip boilerplate/comments and retain readable tables
    text = extract(html, url=url, include_comments=False, include_tables=True)
    if not text:
        return "No readable article content could be extracted from this page."

    metadata = extract_metadata(html, default_url=url)
    title = metadata.title if metadata and metadata.title else "Untitled Page"
    trimmed = text[:max_chars] + ("\n...[truncated]" if len(text) > max_chars else "")
    return f"Title: {title}\nURL: {url}\n\nContent:\n{trimmed}"


def scrape_url_tool(url: str) -> str:
    # Extracts clean main text from a webpage URL for deep reading or summarization
    # Parameter url: Full http or https URL of the webpage to scrape
    return scrape_webpage(url=url)
```

* **Verification / Done Criteria:**
  - Compile: `backend/.venv/bin/python -m py_compile backend/app/services/web_scrap.py`.
  - Add a `__main__` smoke check verifying invalid URLs return the validation string and valid static URLs return formatted `Title / URL / Content` output capped at `max_chars`.

---

### Step 2: Update System Steering Prompt for Dual-Tool Routing

* **Goal & Scope:**
  - Teach Gemini when to call `scrape_url_tool` vs. `search_web_tool`, when to skip scraping to preserve speed, and how to handle page summaries cleanly.
  - Out of scope: Modifying `augmented_prompt()` (kept deprecated for backwards compatibility).
* **Target File:**
  - `backend/app/services/prompt.py`
* **Before Changes:**
  - `SYSTEM_PROMPT` only documents `search_web_tool` and enforces a strict `< 70 words` cap on all replies.

```python
# Before: Single-tool rules and rigid length cap
### 3. Response Format & Citations
* Keep responses tight, direct, and under 70 words.
```

* **After Changes:**
  - Adds a dedicated `scrape_url_tool` section instructing Gemini to scrape direct user URLs or thin search snippets, skip scraping if snippets suffice, and allow structured summaries for scraped pages.

```python
# After: Dual-tool steering and conditional summary length
### 3. When to Use `scrape_url_tool`
* **Direct URLs:** Call `scrape_url_tool(url)` immediately when the user includes a specific webpage URL.
* **Search Follow-Up:** After `search_web_tool`, call `scrape_url_tool(url)` only if the snippets lack required details, steps, or facts.
* **Avoid Unnecessary Scraping:** Do NOT scrape if snippets already answer the question or if the URL is a generic homepage.
* **Fallback:** If `scrape_url_tool` fails or is blocked, rely on retrieved search snippets or clearly state the page could not be read.

### 4. Response Format & Citations
* Keep normal answers tight, direct, and under 70 words; use structured bullet summaries when summarizing a scraped page.
```

* **Verification / Done Criteria:**
  - Compile: `backend/.venv/bin/python -m py_compile backend/app/services/prompt.py`.
  - Inspect `SYSTEM_PROMPT` to confirm exact parameter/tool name parity (`search_web_tool`, `scrape_url_tool`).

---

### Step 3: Register Second Tool & Multi-Step History in Orchestrator

* **Goal & Scope:**
  - Register `scrape_url_tool` in `create_agent_chat()`, handle `scrape_url_tool` execution in `run_chat_turn()`, increase `max_tool_turns` to `4`, and return all tool steps in `tool_details["steps"]`.
  - Keep `stream_ai.py` in sync so no stale duplicate remains.
  - Out of scope: Changing retry config (`get_default_http_options`) or FastAPI routes.
* **Target Files:**
  - `backend/app/services/gemini.py`
  - `backend/streamlit/stream_ai.py`
* **Before Changes:**
  - `tools=[search_web_tool]`, `max_tool_turns = 3`, and `tool_details` is overwritten if more than one tool runs.

```python
# Before: Single tool registration and single-dict tracking
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[search_web_tool],
        ...
    )
# Inside run_chat_turn:
    tool_details = None
    max_tool_turns = 3
    ...
    tool_details = {"tool_name": tool_call.name, "query": query, ...}
```

* **After Changes:**
  - Registers `[search_web_tool, scrape_url_tool]`, dispatches both tool names inside the loop, records every step in `tool_history`, and updates CLI debug output to print all steps.

```python
# After: Dual-tool config and non-destructive multi-step history
from app.services.web_scrap import scrape_url_tool

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[search_web_tool, scrape_url_tool],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        http_options=get_default_http_options(),
    )

# Inside run_chat_turn:
    tool_history = []
    max_tool_turns = 4
    ...
                if tool_call.name == "search_web_tool":
                    ...
                    tool_history.append({
                        "tool_name": tool_call.name,
                        "query": query,
                        "category": category,
                        "timelimit": timelimit,
                        "output": search_context,
                    })
                elif tool_call.name == "scrape_url_tool":
                    tool_executed = True
                    target_url = tool_call.args.get("url", "")
                    scraped_content = scrape_url_tool(url=target_url)
                    tool_history.append({
                        "tool_name": tool_call.name,
                        "url": target_url,
                        "output": scraped_content,
                    })
                    response_parts.append(
                        types.Part.from_function_response(
                            name=tool_call.name,
                            response={"result": scraped_content},
                        )
                    )
    ...
    tool_details = {"steps": tool_history} if tool_history else None
```

* **Verification / Done Criteria:**
  - Compile both files and verify clean CLI startup (`printf "exit\n" | backend/.venv/bin/python backend/app/services/gemini.py`).
  - Test two CLI prompts: (1) a direct URL prompt triggering `scrape_url_tool` only, and (2) an in-depth query triggering `search_web_tool` $\rightarrow$ `scrape_url_tool` without overwriting search trace data.

---

### Step 4: Update Streamlit UI for Multi-Step Status & Context Display

* **Goal & Scope:**
  - Update `stream_app.py` to consume the new `tool_info["steps"]` list so `status_box` summarizes all executed tools (e.g., Search + Scrape) and the debug expander renders every tool output cleanly.
  - Out of scope: Changing Streamlit page layout, sidebar buttons, or session state key names (`chat`, `messages`).
* **Target File:**
  - `backend/streamlit/stream_app.py`
* **Before Changes:**
  - Reads `tool_info['query']` and `tool_info['search_context']` directly, which breaks once `tool_details` stores a `steps` list.

```python
# Before: Assumes a single search_web_tool dict
if tool_used and tool_info:
    category_label = tool_info.get("category", "text").capitalize()
    status_box.update(
        label=f"Searched DDGS ({category_label}) for: '{tool_info['query']}'",
        state="complete",
        expanded=False
    )
...
debug_text = tool_info["search_context"] if (tool_used and tool_info) else None
```

* **After Changes:**
  - Formats a concise combined status label across all steps and joins each step's labeled output for `debug_context`.

```python
# After: Summarizes all search/scrape steps in status_box and debug expander
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

    status_box.update(label=" -> ".join(step_labels), state="complete", expanded=False)
    debug_text = "\n\n".join(debug_sections)
else:
    status_box.update(label="Answered directly (no tools needed)", state="complete", expanded=False)
    debug_text = None
```

* **Verification / Done Criteria:**
  - Compile: `backend/.venv/bin/python -m py_compile backend/streamlit/stream_app.py`.
  - Launch with `backend/.venv/bin/streamlit run backend/streamlit/stream_app.py` and verify:
    1. Greeting (`"Hi"`) shows `"Answered directly (no tools needed)"`.
    2. Direct URL prompt shows `"Scraped: <url>"` and scraped body in the debug expander.
    3. Multi-hop query shows `"Searched DDGS (...) -> Scraped: ..."` with both outputs preserved in the debug expander.

---

## 4. Human Review & Handoff Checkpoints

| Checkpoint | Decision / Audit Focus | Pass Criteria |
| :--- | :--- | :--- |
| **CP-1: Scope & Dependency Boundary** | Confirm `crawl4ai` is completely untouched | `grep -ri "crawl4ai" backend/app/` returns zero matches; only `trafilatura` and stdlib are used in `web_scrap.py`. |
| **CP-2: Comment & Safety Rules** | Verify `#` comment rule & URL guardrails | No `"""` docstrings used as comments; `scrape_webpage()` blocks non-`http(s)` schemes and caps text via `max_chars`. |
| **CP-3: Contract Parity (`gemini.py` $\leftrightarrow$ `stream_app.py`)** | Verify `tool_details["steps"]` schema | `gemini.py`, `stream_ai.py`, and `stream_app.py` all read/write the exact same `steps` list keys (`tool_name`, `output`, `query`/`url`). |
| **CP-4: Graceful Block Fallback** | Test a protected or invalid URL | Returning `None` from `fetch_url()` produces a clean fallback message to Gemini without crashing CLI or Streamlit. |
