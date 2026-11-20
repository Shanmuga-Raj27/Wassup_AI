
#DuckDuckGo Web Search Service using ddgs

from typing import List, Dict, Any
from ddgs import DDGS


def search_web(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    
    # Search DuckDuckGo and return a list of search result dictionaries:
    # Each dict contains: 'title', 'href' (link), 'body' (snippet).

    try:
        # DDGS context manager handles opening and closing sessions cleanly
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except Exception as exc:
        print(f"[Search Error] Failed to search for '{query}': {exc}")
        return []


def format_search_results(results: List[Dict[str, Any]]) -> str:
    
    # Format search results into a clean context block for Gemini.
    
    if not results:
        return "No search results found."

    formatted_items = []
    for index, item in enumerate(results, start=1):
        title = item.get("title", "No Title")
        link = item.get("href", "")
        body = item.get("body", "No summary available.")
        
        formatted_items.append(
            f"[{index}] {title}\nURL: {link}\nSummary: {body}"
        )

    return "\n\n".join(formatted_items)


# Quick standalone test if you run: python backend/app/services/web_search.py
if __name__ == "__main__":
    test_query = "FastAPI Python"
    results = search_web(test_query, max_results=2)
    print(format_search_results(results))