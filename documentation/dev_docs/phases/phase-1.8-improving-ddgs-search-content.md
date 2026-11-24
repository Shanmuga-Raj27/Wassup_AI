# Phase 1.8 Architecture & Implementation Plan: Improving DDGS Web Search Content

**Document Target:** `documentation/dev_docs/implement_plan/phase-1.8-improving-ddgs-search-content.md`  
**Audience:** Human Developers and Engineers  
**Status:** Pre-Execution Architecture & Design Reference  
**Scope:** Phase 1.8 — Enhancing Search Snippet Quality, Temporal Accuracy, and Dynamic Source Targeting without Hardcoding Domain Rules

---

## 1. Executive Summary & Objective

In **Phase 1.5**, the Web Agent successfully transitioned to autonomous, manual tool calling (`search_web_tool`). However, real-world testing revealed an inherent limitation of raw search engine results:

* **The SEO Snippet Problem:** Broad or temporal queries (such as breaking news or current events) frequently return newspaper homepages or category landing pages instead of specific articles.
* **Low Information Density:** The resulting snippets contain generic marketing descriptions (e.g., *"Get the latest news and updates across politics and sports..."*) rather than actual factual information.
* **AI Hallucination vs. Refusal:** Faced with zero substantive facts in the context, the **AI model** either refuses to answer or simply directs the user to visit the portal homepage.

**Phase 1.8 Objective:** Optimize the web search layer to extract rich, dense, and source-authoritative snippets from **ddgs web search** *before* introducing full-page scraping in Phase 2. 

Crucially, because the Web Agent is a **general-purpose system**, this must be achieved **without hardcoding query-specific rules** (such as `if "news" in query:` or a fixed list of news URLs) in the Python backend.

---

## 2. Core Architectural Principles

```text
+-----------------------------------------------------------------------------------+
|                        PHASE 1.8 ARCHITECTURAL PRINCIPLES                         |
+-----------------------------------------------------------------------------------+
| 1. General-Purpose Invariance                                                     |
|    The Python backend must remain agnostic to the user's topic. It treats code    |
|    documentation, historical research, recipes, and live news with identical      |
|    generic execution logic.                                                       |
|                                                                                   |
| 2. Model-Governed Search Parameters                                               |
|    The AI model's natural language understanding decides whether a search needs   |
|    general text or dedicated news, what time window applies, and which domains    |
|    are authoritative.                                                             |
|                                                                                   |
| 3. Information-Density Quality Gates                                              |
|    The backend applies content heuristics (snippet length, deep URL checks) to    |
|    discard empty landing-page boilerplate before injecting text into the prompt.  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Key Concepts & System Design

### Concept 1: Model-Governed Tool Parameters
Instead of forcing every query through a static `ddgs.text()` call, the tool signature is expanded to expose search dimensions directly to the **AI model**.

```python
# Conceptual Tool Signature for Phase 1.8
def search_web_tool(
    query: str,
    category: str = "text",      # Options: "text" | "news"
    timelimit: str = None,       # Options: "d" (day) | "w" (week) | "m" (month) | None
    max_results: int = 5
) -> str:
    # Searches the live web using DDGS metasearch.
    # Parameter query: Concise, high-signal search keywords.
    # Parameter category: Select "text" for technical docs, general knowledge, or recipes. Select "news" for breaking news, live events, or sports updates.
    # Parameter timelimit: Select "d" or "w" for recent/time-sensitive queries; leave None for timeless topics.
    ...
```

#### How the AI Model Routes Dynamically:
* **Coding Query:** `"How to configure CORS in FastAPI?"`  
  ➔ `category="text"`, `timelimit=None` (Queries general web index).
* **Breaking News Query:** `"Latest developments in Tamil Nadu politics today"`  
  ➔ `category="news"`, `timelimit="d"` (Queries news index with past 24-hour filter).
* **Recent Tech Announcement:** `"Nvidia Blackwell benchmark results released this month"`  
  ➔ `category="news"`, `timelimit="m"` (Queries news index with past 30-day filter).

---

### Concept 2: Dynamic Authoritative Source Targeting
Rather than maintaining a hardcoded list of trusted websites in Python, the **AI model** dynamically identifies primary sources based on context.

```text
User Question ──> [AI Model Analyzes Intent]
                         │
                         ├─ Technical Lib  ──> Identifies official docs (e.g. python.org)
                         ├─ Government Reg ──> Identifies official portals (e.g. .gov domains)
                         └─ Corporate News ──> Identifies primary press sites (e.g. nvidia.com)
                                 │
                                 ▼
         Appends dynamic filter to query or specifies target_domains
```

#### Mechanisms for Model-Driven Source Selection:
1. **Prompt-Guided Query Rewriting (`site:` operators):**  
   The system prompt steers the model to deduce the primary authority for specialized queries:
   * User: *"Python 3.13 deprecation list"* ➔ Query: `"Python 3.13 deprecations site:docs.python.org"`
   * User: *"CDC travel vaccines 2026"* ➔ Query: `"travel vaccine advisory site:cdc.gov"`
2. **Domain Candidate Hints in Tool Responses:**  
   The backend provides the model with candidate domains extracted from search results, allowing the model to prioritize or filter links from recognized official sources.

---

### Concept 3: Snippet Density & Content Filtering
A common reason for low-quality answers is that the search results contain shallow, boilerplate text. Phase 1.8 introduces a domain-agnostic **information-density pipeline**:

1. **Candidate Over-Fetching:**  
   The backend requests 6 to 8 candidate results from DDGS instead of only 3.
2. **Deep-Link Preference (Discarding Homepages):**  
   URLs that are root homepages (e.g., `https://www.dailythanthi.com/`) or generic category portals (e.g., `.../news/`) are filtered out or down-ranked in favor of deep article paths containing specific slugs (e.g., `.../tamil-nadu/cyclone-warning-update-12345.cms`).
3. **Snippet Length Threshold:**  
   Snippets with fewer than 80 characters or those matching common SEO boilerplate phrases are discarded.
4. **Structured Metadata Enrichment:**  
   When available (especially from `ddgs.news()`), snippets are formatted with publisher names and publication timestamps:
   ```text
   [1] Heavy Rain Alert Issued for Coastal Districts
   Source: The Hindu | Published: 3 hours ago
   URL: https://www.thehindu.com/news/national/...
   Summary: The meteorological department issued an alert on Tuesday regarding heavy rainfall...
   ```

---

## 4. End-to-End Data Flow Architecture

```text
[User Prompt]
      │
      ▼
[1. AI Model Intent Evaluation]
      ├─ Deduces search keywords (e.g., "Tamil Nadu weather alert")
      ├─ Chooses category: "news" vs "text"
      └─ Chooses timelimit: "d", "w", or None
      │
      ▼ Emits Tool Call: search_web_tool(query, category, timelimit)
[2. Backend Router & Multi-Engine Dispatch]
      ├─ If category == "news" ──> ddgs.news(query, timelimit=timelimit)
      │                            (Fallbacks: bing ➔ duckduckgo ➔ yahoo)
      └─ If category == "text" ──> ddgs.text(query, timelimit=timelimit)
                                   (Fallbacks: duckduckgo ➔ yahoo ➔ brave)
      │
      ▼ (6–8 Raw Candidates Retrieved)
[3. Information Density & Deep-Link Filter]
      ├─ Discards root homepages / section landing pages
      ├─ Discards snippets under 80 characters
      └─ Retains top 3–4 high-density results
      │
      ▼
[4. Structured Context Serialization]
      └─ Formats headlines, timestamps, source names, and deep URLs
      │
      ▼ Sends FunctionResponse
[5. AI Model Grounded Synthesis]
      └─ Delivers factual, dated, source-linked answer to User
```

---

## 5. Transition to Phase 2 (Deep Web Scraping)

Phase 1.8 does not replace Phase 2; it **enables** Phase 2 to succeed.

```text
+-------------------------------------------------------------------------------+
| PHASE 1.8: DISCOVERY & FILTERING (DDGS)                                       |
| - Finds relevant candidate pages.                                             |
| - Filters out homepages to guarantee deep, scrapeable article URLs.          |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼ (Passes clean deep URL)
+-------------------------------------------------------------------------------+
| PHASE 2: DEEP CONTENT EXTRACTION (Trafilatura / Crawl4AI)                     |
| - AI Model inspects snippet: if shallow, triggers scrape_url_tool(url).      |
| - Scraper extracts complete 800-word article body text.                       |
| - Model synthesizes comprehensive, in-depth reports.                          |
+-------------------------------------------------------------------------------+
```

If Phase 1.8 did not filter out landing pages, Phase 2 would attempt to scrape the homepage of Times of India or Daily Thanthi, resulting in megabytes of navigation menus, ads, and broken text. 

By filtering search down to **deep article URLs with timestamps**, Phase 1.8 ensures that the upcoming scraper in Phase 2 receives valid, clean article pages.

---

## 6. Summary of Architectural Decisions for Developers

1. **Keep Python Agnostic:** Never write `if "news" in query` in Python. Put parameter options (`category`, `timelimit`) into the tool signature and let the **AI model** make routing decisions.
2. **Leverage Dedicated News Indexes:** Use `ddgs.news()` for live events and temporal updates; it provides real headlines, timestamps, and deep links that standard web indexes miss.
3. **Filter Out Root Domains:** Programmatically discard shallow root homepages when searching for specific topics.
4. **Enrich Metadata:** Include timestamps (`date`) and publisher names (`source`) in the context block so the AI model can cite current facts accurately.
