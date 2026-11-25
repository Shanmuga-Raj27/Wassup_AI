# DDGS (Dux Distributed Global Search) Metasearch Service
# An open-source metasearch library aggregating multi-engine results without API keys.

from typing import List, Dict, Any, Optional
from ddgs import DDGS


def search_web(
    query: str,
    category: str = "text",
    timelimit: Optional[str] = None,
    max_results: int = 4,
) -> List[Dict[str, Any]]:
    # Search via DDGS metasearch with multi-engine fallback
    # Backends: bing -> duckduckgo -> yahoo for news; duckduckgo -> yahoo -> brave for text
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
        except Exception as exc:
            error_msg = str(exc)
            if "No results found" in error_msg:
                continue
            # Continue to next backend if current one fails or times out
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


def format_search_results(results: List[Dict[str, Any]]) -> str:
    # Format search results into a clean context block for Gemini.
    if not results:
        return "No search results found. Please answer directly using your existing knowledge or state that information is unavailable."

    formatted_items = []
    for index, item in enumerate(results, start=1):
        title = item.get("title", "No Title")
        link = item.get("href") or item.get("url", "")
        body = item.get("body", "No summary available.")
        date = item.get("date")
        source = item.get("source")

        metadata_parts = []
        if source:
            metadata_parts.append(f"Source: {source}")
        if date:
            metadata_parts.append(f"Date: {date}")

        metadata_str = f" ({', '.join(metadata_parts)})" if metadata_parts else ""

        formatted_items.append(
            f"[{index}] {title}{metadata_str}\nURL: {link}\nSummary: {body}"
        )

    return "\n\n".join(formatted_items)


def search_web_tool(
    query: str,
    category: str = "text",
    timelimit: Optional[str] = None,
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


# Quick standalone test if you run: python backend/app/services/web_search.py
if __name__ == "__main__":
    print("Testing category='text':")
    print(search_web_tool("FastAPI Python", category="text", max_results=2))
    print("\nTesting category='news':")
    print(search_web_tool("Python programming news", category="news", timelimit="w", max_results=2))
