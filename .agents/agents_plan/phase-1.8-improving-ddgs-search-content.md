# Phase 1.8 Step-by-Step Implementation Plan: Improving DDGS Web Search Content

**Document Target:** `.agents/agents_plan/phase-1.8-improving-ddgs-search-content.md`  
**Audience:** AI Coding Agents and Human Backend Developers  
**Status:** Complete  
**Objective:** Enhance search snippet quality, temporal freshness, and dynamic source targeting without hardcoding domain-specific rules.

---

## 1. Pre-Flight & Baseline Verification

Before modifying any source code, verify that the current environment and baseline services are intact:

1. **Verify Python Virtual Environment & Dependencies:**
   - Command: `backend/.venv/bin/python -m py_compile backend/app/services/*.py backend/streamlit/*.py`
   - Expected: All modules compile without syntax or import errors.
2. **Verify Metasearch Library Support:**
   - Ensure `ddgs` library exposes both `ddgs.text()` and `ddgs.news()`.
   - Verify that news search supports backends `['bing', 'duckduckgo', 'yahoo']` and text search supports `['duckduckgo', 'yahoo', 'brave']`.
3. **Verify Baseline Tool Calling Flow:**
   - Ensure `backend/app/services/gemini.py` runs and cleanly exits with `printf "exit\n" | backend/.venv/bin/python backend/app/services/gemini.py`.

---

## 2. Ordered Implementation Steps

### Step 1: Upgrade Metasearch Engine with Multi-Category and Density Filtering

* **Goal & Scope:**
  - Add `category` (`"text"` vs `"news"`) and `timelimit` (`"d"`, `"w"`, `"m"`, or `None`) support to `search_web()`.
  - Route `"news"` queries through `ddgs.news()` (using fallback cascade `bing -> duckduckgo -> yahoo`).
  - Route `"text"` queries through `ddgs.text()` (using fallback cascade `duckduckgo -> yahoo -> brave`).
  - Over-fetch candidate results (e.g., 6 to 8 items) and filter out shallow root homepages (e.g., `https://example.com/`) and snippets shorter than 80 characters.
  - Enrich formatted context with publication dates and sources when available.
  - Out of scope: Web scraping or DOM parsing (reserved for Phase 2).

* **Target File:**
  - `backend/app/services/web_search.py`

* **Before Changes:**
  - The function hardcodes `ddgs.text()` with no `timelimit` and no `category` selection.
  - Snippets from root landing pages are passed unconditionally into the prompt context.

```python
# Before: Fixed to text search without category, date, or density filtering
def search_web(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    backends = ["duckduckgo", "yahoo", "brave"]
    for backend in backends:
        try:
            with DDGS(timeout=8) as ddgs:
                results = list(ddgs.text(query, max_results=max_results, backend=backend))
                if results:
                    return results
        except Exception:
            continue
    return []

def search_web_tool(query: str, max_results: int = 3) -> str:
    raw_results = search_web(query=query, max_results=max_results)
    return format_search_results(raw_results)
```

* **After Changes:**
  - `search_web()` routes between `ddgs.news()` and `ddgs.text()` dynamically based on caller parameters.
  - Candidate results are filtered by URL depth and minimum snippet length.
  - `format_search_results()` renders publication timestamps and source names.

```python
# After: Dynamic category routing, time limits, and content density filtering
def search_web(
    query: str,
    category: str = "text",
    timelimit: str | None = None,
    max_results: int = 4,
) -> List[Dict[str, Any]]:
    # Select engine backends based on category
    backends = ["bing", "duckduckgo", "yahoo"] if category == "news" else ["duckduckgo", "yahoo", "brave"]
    overfetch_count = max_results * 2

    for backend in backends:
        try:
            with DDGS(timeout=8) as ddgs:
                if category == "news":
                    results = list(ddgs.news(query, max_results=overfetch_count, timelimit=timelimit, backend=backend))
                else:
                    results = list(ddgs.text(query, max_results=overfetch_count, timelimit=timelimit, backend=backend))
                if results:
                    return results
        except Exception:
            continue
    return []

def filter_dense_results(results: List[Dict[str, Any]], min_length: int = 70) -> List[Dict[str, Any]]:
    # Discard shallow root homepages and low-density snippets
    filtered = []
    for item in results:
        body = item.get("body", "")
        url = item.get("href") or item.get("url", "")
        path_segments = [p for p in url.split("/") if p and not p.startswith("http")]
        # Keep items with adequate content length or deep article paths
        if len(body) >= min_length or len(path_segments) >= 2:
            filtered.append(item)
    return filtered if filtered else results

def search_web_tool(
    query: str,
    category: str = "text",
    timelimit: str | None = None,
    max_results: int = 4,
) -> str:
    # Metasearch tool looking up real-time web facts, news, and documentation
    # Parameter query: Concise search keywords formulated to locate relevant facts
    # Parameter category: Use "text" for technical docs, general knowledge, or coding; use "news" for breaking news, current events, or sports updates
    # Parameter timelimit: Use "d" (day) or "w" (week) for recent time-sensitive queries; leave None for static topics
    # Parameter max_results: Number of web results to return
    raw = search_web(query=query, category=category, timelimit=timelimit, max_results=max_results)
    dense = filter_dense_results(raw)
    return format_search_results(dense[:max_results])
```

* **Verification / Done Criteria:**
  - Execute standalone test: `backend/.venv/bin/python backend/app/services/web_search.py`
  - Verify that `category="news"` returns structured dictionaries containing `title`, `body`, `date`, `source`, and deep article links.
  - Verify that `category="text"` continues to function normally for technical queries without regressions.

---

### Step 2: Update System Steering Prompt for Model-Governed Routing

* **Goal & Scope:**
  - Update `SYSTEM_PROMPT` in `prompt.py` to instruct Gemini on selecting `category="news"` and `timelimit="d"` for breaking events, current dates, or live updates.
  - Guide the model on prompt-driven query rewriting using `site:` operators when targeting official documentation or authoritative sources (e.g., `python.org`, `.gov`, `.edu`).
  - Out of scope: Hardcoding specific website names in Python code.

* **Target File:**
  - `backend/app/services/prompt.py`

* **Before Changes:**
  - Prompt only instructs on query length and basic tool calling conditions; does not describe parameter options (`category`, `timelimit`) or source targeting.

```python
# Before: Generic search trigger rule without parameter steering
SYSTEM_PROMPT = """You are a fast, helpful, and accurate AI web agent designed for general chat.
### 1. When to Use `search_web_tool`
* Call `search_web_tool` for: Recent events, live news, current facts, sports scores...
### 2. Search Query Rules
* Write short, keyword-focused queries (3 to 6 words)...
"""
```

* **After Changes:**
  - Prompt explicitly steers the model on when to use `category="news"`, when to pass `timelimit="d"`, and how to target primary official domains.

```python
# After: Guides autonomous selection of category, timelimit, and authoritative sources
SYSTEM_PROMPT = """You are a fast, helpful, and accurate AI web agent designed for general chat.

### 1. When to Use `search_web_tool`
* Call `search_web_tool` for: Live news, recent events, sports scores, weather, software releases, or current documentation.
* Do NOT call `search_web_tool` for: Greetings, logic, creative writing, or basic programming theory that does not depend on recent updates.

### 2. Tool Parameter Selection
* **Category:** Set `category="news"` for breaking stories, current events, or sports updates. Set `category="text"` for technical docs, general knowledge, or recipes.
* **Timelimit:** Set `timelimit="d"` (past 24h) or `"w"` (past week) for time-sensitive queries; leave `None` for evergreen topics.
* **Authoritative Source Targeting:** When answering queries regarding official library documentation, legal regulations, or company press releases, deduce the primary domain and include `site:<domain>` in the query (e.g. `query="FastAPI middleware site:fastapi.tiangolo.com"`).

### 3. Response Format & Citations
* Keep responses tight, direct, and under 70 words.
* Base factual claims strictly on retrieved snippets and cite source URLs as markdown links.
* If search results contain no relevant facts, state that current information could not be found instead of guessing.
"""
```

* **Verification / Done Criteria:**
  - Compile with `backend/.venv/bin/python -m py_compile backend/app/services/prompt.py`.
  - Validate that `SYSTEM_PROMPT` contains clear parameter descriptions matching the `search_web_tool` signature.

---

### Step 3: Update Agent Orchestration Layer to Pass Search Dimensions

* **Goal & Scope:**
  - Update `run_chat_turn()` in `gemini.py` to inspect `tool_call.args` for `category` and `timelimit`.
  - Pass these extracted arguments into `search_web_tool()`.
  - Update console/debug logging to display the selected category and timelimit.
  - Out of scope: Modifying the `GenerateContentConfig` retry options or client initialization.

* **Target File:**
  - `backend/app/services/gemini.py`

* **Before Changes:**
  - The tool loop only extracts `query` and `max_results`, ignoring any additional model-supplied arguments.

```python
# Before: Only extracts query and max_results
if tool_call.name == "search_web_tool":
    tool_executed = True
    query = tool_call.args.get("query", user_prompt)
    max_results = int(tool_call.args.get("max_results", 3))
    search_context = search_web_tool(query=query, max_results=max_results)
```

* **After Changes:**
  - The tool loop extracts `category` and `timelimit` dynamically from `tool_call.args`.

```python
# After: Extracts category and timelimit and passes them to search_web_tool
if tool_call.name == "search_web_tool":
    tool_executed = True
    query = tool_call.args.get("query", user_prompt)
    category = tool_call.args.get("category", "text")
    timelimit = tool_call.args.get("timelimit", None)
    max_results = int(tool_call.args.get("max_results", 4))

    search_context = search_web_tool(
        query=query,
        category=category,
        timelimit=timelimit,
        max_results=max_results,
    )
    tool_details = {
        "tool_name": tool_call.name,
        "query": query,
        "category": category,
        "timelimit": timelimit,
        "search_context": search_context,
    }
```

* **Verification / Done Criteria:**
  - Compile and test startup: `printf "exit\n" | backend/.venv/bin/python backend/app/services/gemini.py`.
  - Run test query in CLI with breaking news (e.g., `"current news today in Tamil Nadu"`):
    - Verify that `category="news"` and `timelimit="d"` appear in `[Tool Arguments]`.
    - Verify that retrieved snippets contain specific article titles and timestamps rather than root homepages.

---

### Step 4: Update Streamlit UI Dynamic Status and Debug Display

* **Goal & Scope:**
  - Update the dynamic status indicator in `stream_app.py` to display the active search category (e.g., `"Searched DDGS (News) for: '...'"`).
  - Ensure the debug expander renders the publication source and timestamp alongside retrieved URLs.
  - Out of scope: Restyling UI components or altering session state keys.

* **Target File:**
  - `backend/streamlit/stream_app.py`

* **Before Changes:**
  - Status box displays a generic label without category or timelimit details.

```python
# Before: Generic search label in status box
if tool_used and tool_info:
    status_box.update(
        label=f"Searched DDGS for: '{tool_info['query']}'",
        state="complete",
        expanded=False
    )
```

* **After Changes:**
  - Status label reflects the model-selected category and temporal constraint.

```python
# After: Displays category and query details in status box
if tool_used and tool_info:
    category_label = tool_info.get("category", "text").capitalize()
    status_box.update(
        label=f"Searched DDGS ({category_label}) for: '{tool_info['query']}'",
        state="complete",
        expanded=False
    )
```

* **Verification / Done Criteria:**
  - Verify syntax with `backend/.venv/bin/python -m py_compile backend/streamlit/stream_app.py`.
  - Verify that both text queries and news queries display appropriate category badges in the Streamlit UI.

---

## 3. Human Review & Handoff Checkpoints

Before considering Phase 1.8 complete and proceeding to Phase 2 (Trafilatura Web Scraping), human developers must verify three checkpoints:

| Checkpoint | Review Criteria | Verification Test |
| :--- | :--- | :--- |
| **CP-1: Tool Contract Alignment** | The signature in `web_search.py`, the docstring parameters, and the extraction in `gemini.py` must use matching argument names (`query`, `category`, `timelimit`, `max_results`). | Inspect function signatures across files for name parity. |
| **CP-2: Zero-Hardcoding Audit** | No file under `backend/app/services/` may contain hardcoded keyword rules (e.g. `if "news" in query:` or hardcoded lists of media domains). Routing must remain strictly model-driven. | Run `grep -ri "if .*news.* in" backend/app/` to verify zero matches. |
| **CP-3: Information Density Acceptance** | Querying a current event (e.g., `"latest sports scores"` or `"local news headlines"`) must return specific event summaries and timestamps, NOT generic homepages (`timesofindia.indiatimes.com/india` or `dailythanthi.com`). | Run test prompt in CLI and verify returned snippet bodies are > 70 characters and cite deep URLs. |
