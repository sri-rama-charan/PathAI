# ==============================================================================
# File: server/app/services/search.py
# Purpose: Web search domain service for discovering educational resources.
# ==============================================================================

from typing import List
from urllib.parse import urlparse

from app.schemas.plan import SearchResult
from app.integrations.tavily import get_tavily_api_key, execute_tavily_search


def extract_source_domain(url: str) -> str:
    """
    Extracts the clean domain name from a URL to use as the source identifier.
    
    Example:
        'https://docs.langchain.com/docs/intro' -> 'docs.langchain.com'
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "") or "web"
    except Exception:
        return "web"


def search_web(query: str, max_results: int = 5) -> List[SearchResult]:
    """
    Executes a web search and returns a list of normalized SearchResult objects.
    
    Args:
        query (str): The search topic or technical keywords.
        max_results (int): Maximum number of results to retrieve (default: 5).
        
    Returns:
        List[SearchResult]: Standardized, provider-independent search results.
        
    Raises:
        ValueError: If the query is empty or TAVILY_API_KEY is missing.
        RuntimeError: If the Tavily API call fails due to network or authentication issues.
    """
    cleaned_query = query.strip() if query else ""
    if not cleaned_query:
        raise ValueError("Search query cannot be empty.")

    raw_results = execute_tavily_search(
        query=cleaned_query,
        max_results=max_results,
        search_depth="basic",
    )

    normalized_results: List[SearchResult] = []
    for item in raw_results:
        url = item.get("url", "")
        title = item.get("title", "Untitled Resource")
        content = item.get("content", "")

        # Domain name acts as source
        source = extract_source_domain(url)

        normalized_results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=content,
                source=source,
            )
        )

    return normalized_results
