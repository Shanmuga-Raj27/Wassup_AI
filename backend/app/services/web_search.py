
# DDGS (Dux Distributed Global Search) Metasearch Service
# An open-source metasearch library aggregating multi-engine results without API keys.

from typing import List, Dict, Any
from ddgs import DDGS


def search_web(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    # Search via DDGS metasearch with multi-engine fallback (duckduckgo -> yahoo -> brave)
    # Each dict contains: 'title', 'href' (link), 'body' (snippet).
    backends = ["duckduckgo", "yahoo", "brave"]
    for backend in backends:
        try:
            with DDGS(timeout=8) as ddgs:
                results = list(ddgs.text(query, max_results=max_results, backend=backend))
                if results:
                    return results
        except Exception as exc:
            error_msg = str(exc)
            if "No results found" in error_msg:
                continue
            # Continue to next backend if current one fails or times out
            continue
    return []


def format_search_results(results: List[Dict[str, Any]]) -> str:
    # Format search results into a clean context block for Gemini.
    if not results:
        return "No search results found. Please answer directly using your existing knowledge or state that information is unavailable."

    formatted_items = []
    for index, item in enumerate(results, start=1):
        title = item.get("title", "No Title")
        link = item.get("href", "")
        body = item.get("body", "No summary available.")
        
        formatted_items.append(
            f"[{index}] {title}\nURL: {link}\nSummary: {body}"
        )

    return "\n\n".join(formatted_items)


def search_web_tool(query: str, max_results: int = 3) -> str:
    # Metasearch tool looking up live facts, news, and external documentation
    # Parameter query: Concise search keywords formulated to find relevant factual information
    # Parameter max_results: Number of web results to retrieve (default is 3)
    raw_results = search_web(query=query, max_results=max_results)
    return format_search_results(raw_results)


# Quick standalone test if you run: python backend/app/services/web_search.py
if __name__ == "__main__":
    test_query = "FastAPI Python"
    print(search_web_tool(test_query, max_results=2))
