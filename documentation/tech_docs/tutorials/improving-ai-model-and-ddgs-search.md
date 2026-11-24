# Beginner's Guide: Improving AI Model Speed, Reliability, and Web Search

This guide explains two core backend engineering improvements made to the Web Agent system: making the **AI model** faster and more resilient, and making **ddgs web search** more accurate and dependable. It also covers how the system can dynamically target authoritative websites in future phases.

---

## Part 1: Improving AI Model Response Speed & Reliability

When building an application that communicates with a remote **AI model**, requests must travel over the public internet to external API servers. In distributed systems, temporary network disruptions and server-side traffic spikes are common.

```text
[User Request]
       │
       ▼
┌──────────────┐
│ Send to API  │
└──────┬───────┘
       │
       ├───────────────────────────────┐
       ▼ (HTTP 429 / 503 error)        ▼ (Success / HTTP 200)
┌──────────────┐               ┌──────────────┐
│ Check Retry  │               │ Return Model │
│ Attempts     │               │ Response     │
└──────┬───────┘               └──────────────┘
       │
       ├─ Under max attempts (Wait delay) ──> [Retry Request]
       │
       └─ Exceeded max attempts ────────────> [Raise Handled Error]
```

### 1.1 Error Handlers: Preventing Crashes and Freezes
An *API (Application Programming Interface)* call can fail for multiple reasons:
* **Network Drops:** Temporary loss of internet connection between your server and the model provider.
* **Rate Limits (HTTP 429):** The provider temporarily limits incoming requests because too many calls were submitted in a short time frame.
* **Server Overload (HTTP 500 or 503):** The model provider's servers are temporarily busy or restarting.

Without explicit error handling, an unexpected HTTP status code raises an unhandled exception that crashes the Python process or causes the user interface to hang indefinitely. 

By implementing specific error handlers, the backend catches these exceptions immediately, logs the exact error code, and provides a readable status message instead of crashing.

### 1.2 Retry Attempts: Rapid Recovery vs. Long Timeouts
It may seem counterintuitive that retrying a failed request makes the system faster. However, retries dramatically improve user-perceived speed and system reliability:

1. **Transient Glitches Clear Quickly:** Most rate limits (HTTP 429) or gateway drops (HTTP 503) resolve within `2 to 3 seconds`. 
2. **Automated Recovery vs. Manual Restarts:** Without automated retries, a single network hiccup fails the request. The user must notice the failure, re-run the program, and re-enter their prompt. An automated retry recovers in 2 seconds without user intervention.
3. **Preventing Connection Hangs:** By defining targeted HTTP status codes and strict retry counts, the client quickly tears down stalled connections and requests a fresh network socket instead of waiting for standard operating system socket timeouts, which can take several minutes.

### 1.3 Implementation Snippet
The following Python snippet demonstrates how automated retry rules and specific API error handling are configured for the **AI model**:

```python
# backend/app/services/gemini.py
from google.genai import types, errors

# Configure automated retries for transient HTTP status codes
http_options = types.HttpOptions(
    retry_options=types.HttpRetryOptions(
        attempts=4,
        initial_delay=2.0,
        http_status_codes=[408, 429, 500, 502, 503, 504],
    )
)

# Catch model-specific errors gracefully
try:
    response = chat.send_message(user_prompt)
except errors.APIError as error:
    print(f"API Error ({error.code}): {error.message}")
    print("The AI model did not return a response. Please try again later.")
except Exception as error:
    print(f"Unexpected error: {error}")
```

*What this achieves:* The client automatically retries up to 4 times with an initial 2-second delay whenever it encounters temporary network congestion. If all retries fail, it catches `APIError` cleanly without terminating the application.

---

## Part 2: Improving `ddgs` Web Search Accuracy & AI Responses

The **AI model** has internal training data (called *parameter knowledge*), but it cannot know real-time facts, current news, or live sports scores without querying external search engines. We use **ddgs web search** to supply fresh information.

```text
TURN 1: INTENT & QUERY GENERATION
User Prompt ──> Backend ──> AI Model
                              │
                              ▼
                Emits Tool Call: search_web_tool(query="...")

TURN 2: EXECUTION & FINAL SYNTHESIS
Backend catches call ──> Runs ddgs web search ──> Formats snippets
                                                        │
                                                        ▼
User Answer <── AI Model Synthesizes Answer <── Sends Tool Output
```

### 2.1 The Two-Turn Tool Calling Cycle
When the **AI model** needs external data, communication happens in two distinct steps:

* **Turn 1 (Tool Request):** The user submits a prompt (e.g., *"Who won yesterday's cricket match?"*). The **AI model** evaluates the prompt, realizes it lacks real-time facts, and outputs a structured tool request: `search_web_tool(query="cricket match result yesterday")`. At this point, the model produces *no final text answer* because it has not seen the data yet.
* **Turn 2 (Execution and Answer):** The Python backend intercepts the tool request, executes **ddgs web search**, formats the retrieved web page titles and snippets, and sends them back to the **AI model** as a function response. The model reads the retrieved text and generates the final, grounded answer with links.

### 2.2 Explicit Search Backends (`"duckduckgo"`, `"yahoo"`, `"brave"`)
By default, the `ddgs` metasearch library uses an automated backend mode (`backend="auto"`). In recent library versions, this mode prioritizes Wikipedia and Grokipedia before querying general web search engines. 

For news, sports, or niche questions, Wikipedia often has no matching page title, causing searches to return zero results. Furthermore, single search scrapers often encounter bot protection or rate limits.

To fix this, our backend implements a sequential fallback cascade across explicit web backends:
1. First, search using `backend="duckduckgo"`.
2. If DuckDuckGo returns no results or fails, immediately attempt `backend="yahoo"`.
3. If Yahoo returns no results, attempt `backend="brave"`.

This multi-engine fallback ensures that temporary scraping blocks on one search service do not cause search failures.

### 2.3 Increasing the Search Timeout
Web search scrapers must perform DNS lookups, establish secure TLS connections, download HTML, and extract text snippets. Under network variance, a 5-second timeout is often too short and aborts right before the response packets arrive. 

Increasing the timeout to `timeout=8` gives the metasearch client sufficient time to complete its network cycle, preventing false "no results" errors while still protecting the backend from hanging indefinitely.

### 2.4 Fallback to Parameter Knowledge
When every search engine returns zero matching documents (such as for obscure queries or internal project names), throwing an exception confuses the **AI model**. 

Instead, the backend catches empty results and sends back a structured fallback message:
`"No search results found. Please answer directly using your existing knowledge or state that information is unavailable."`

This instructs the **AI model** to rely on its built-in *parameter knowledge* (its pre-trained memory) and clearly explain to the user that live web data was not found, rather than hallucinating false claims.

### 2.5 Implementation Snippet
The following Python snippet demonstrates the multi-engine fallback cascade and the parameter knowledge fallback check:

```python
# backend/app/services/web_search.py
from ddgs import DDGS

def search_web(query: str, max_results: int = 4) -> list[dict]:
    # Cascade across multiple free backends if one returns empty
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

def format_search_results(results: list[dict]) -> str:
    # Explicitly instruct the AI model if no live results exist
    if not results:
        return "No search results found. Please answer directly using your existing knowledge or state that information is unavailable."
    
    formatted = []
    for index, item in enumerate(results, start=1):
        formatted.append(f"[{index}] {item.get('title')}\nURL: {item.get('href')}\nSummary: {item.get('body')}")
    return "\n\n".join(formatted)
```

*What this achieves:* It searches across three distinct search services with an 8-second timeout, returns the first valid set of web snippets, and provides a clear fallback instruction if no results are found.

---

## Part 3: Future Phase — Dynamically Picking Authoritative Sites

In production applications, accuracy is improved when the **AI model** consults primary, authoritative domains (such as official documentation, `.gov`, or `.edu` domains) rather than general blog aggregators. 

Hardcoding website URLs in backend Python code is brittle because every question requires different sources. Instead, the system can allow the **AI model** to dynamically decide which sites to target based on the user's intent.

### Approach 1: Prompt-Guided `site:` Operators (Query Rewriting)
Most search engines support the `site:` filter operator (e.g., `site:python.org`). We can instruct the **AI model** in its system instructions to deduce the authoritative organization and include the `site:` operator in its search query.

* **User Prompt:** *"What are the new syntax features in Python 3.13?"*
* **AI Model Decision:** The model recognizes that the official authority for Python language changes is `python.org`.
* **Generated Tool Query:** `search_web_tool(query="python 3.13 new features site:python.org")`

*Advantage:* Zero backend code changes are required. The **AI model** uses natural language understanding to select the correct domain for any topic.

### Approach 2: Dedicated Tool Parameters for Domains
We can update the function signature of `search_web_tool` to include an explicit domain filter list:

```python
def search_web_tool(query: str, target_domains: list[str] = None, max_results: int = 3) -> str:
    # Parameter query: High-signal search keywords
    # Parameter target_domains: Optional list of authoritative websites chosen by the AI model
    ...
```

When registering this tool with the **AI model**, the model can supply structured arguments:
```json
{
  "query": "Blackwell GPU architecture specifications",
  "target_domains": ["nvidia.com", "anandtech.com"]
}
```

The backend then appends these domains to the search query or filters the returned list of results so only links matching those domains are passed into the model's context.

### Approach 3: Two-Phase Search-then-Scrape Pipeline
Rather than relying on search engine summaries alone, future architecture can split research into two complementary tools:

```text
[User Prompt]
      │
      ▼
[AI Model] ──(1. Query)──> [ddgs web search]
      │                            │
      │ <──(Returns Candidate URLs)─┘
      │
      ▼ (2. Selects Most Authoritative URL)
[AI Model] ──(3. Fetch URL)─> [Web Page Scraping Service]
      │                            │
      │ <──(Full Clean Text)───────┘
      │
      ▼ (4. Grounded Synthesis)
[Final Answer to User]
```

1. **Step 1:** The **AI model** uses **ddgs web search** to locate three candidate links.
2. **Step 2:** The model evaluates the candidate URLs and ignores low-relevance domains. It identifies the primary official URL.
3. **Step 3:** The model emits a second tool request: `scrape_url_tool(url="https://docs.python.org/3.13/whatsnew/3.13.html")`.
4. **Step 4:** The backend extracts the full body text of the selected page and returns it, allowing the **AI model** to synthesize a highly detailed, hallucination-free answer.

---

## Summary Checklist for Developers

* **Reliability:** Automated HTTP retry options (`HttpRetryOptions`) with exponential backoff recover from transient rate limits and network drops without crashing.
* **Two-Turn Tool Calling:** Turn 1 generates the tool query; Turn 2 submits web results back to the **AI model** to write the grounded answer.
* **Search Fallbacks:** Chaining search backends (`duckduckgo -> yahoo -> brave`) and increasing timeouts (`timeout=8`) prevents scraper blocks from failing queries.
* **Dynamic Domain Selection:** Using prompt-guided `site:` operators or tool parameters lets the **AI model** decide which authoritative domains to target dynamically for any question.
