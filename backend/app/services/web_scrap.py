# backend/app/services/web_scrap.py
# Deep Web Scraping Service using Trafilatura for static HTML content extraction

from urllib.parse import urlparse
from trafilatura import fetch_url, extract, extract_metadata


def scrape_webpage(url: str, max_chars: int = 6000) -> str:
    # Reject invalid schemes before issuing network requests
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "Invalid URL provided. Only valid http or https links can be scraped."

    try:
        html = fetch_url(url)
    except Exception as exc:
        return f"Failed to fetch webpage: {exc}"

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


# Quick standalone test if you run: python backend/app/services/web_scrap.py
if __name__ == "__main__":
    print("Testing invalid URL:")
    print(scrape_url_tool("ftp://invalid-url"))
    print("\nTesting valid URL:")
    print(scrape_url_tool("https://httpbin.org/html")[:500])
