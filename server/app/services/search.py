# ==============================================================================
# File: server/app/services/search.py
# Purpose: Provider-independent web search service using Tavily Search API.
#
# What this service does:
# 1. Takes a search query (e.g., "LangGraph documentation").
# 2. Uses the official TavilyClient to search the web for high-quality resources.
# 3. Normalizes Tavily-specific fields (like 'content') into our standard SearchResult schema.
# 4. Extracts clean domain sources (e.g., 'docs.langchain.com') for user presentation.
# 5. Keeps the rest of the application decoupled from the underlying search engine.
#
# Future LangGraph Integration:
# Because search_web() takes (query: str) and returns list[SearchResult], we will be
# able to wrap this exact function with @tool in LangGraph with zero changes to this file!
# ==============================================================================

import os
from pathlib import Path
from typing import List
from urllib.parse import urlparse
from dotenv import load_dotenv
from tavily import TavilyClient

from app.schemas import SearchResult

# Resolve path to server directory
SERVER_DIR = Path(__file__).resolve().parent.parent.parent


def get_tavily_api_key() -> str:
    """
    Dynamically reloads server/.env and retrieves the TAVILY_API_KEY.
    
    Raises:
        ValueError: If TAVILY_API_KEY is missing or contains placeholder text.
    """
    load_dotenv(SERVER_DIR / ".env", override=True)
    load_dotenv(override=True)
    
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    
    if not api_key or api_key == "your_tavily_api_key_here":
        raise ValueError(
            "TAVILY_API_KEY is not set. Please add your Tavily API key to server/.env: "
            "TAVILY_API_KEY=tvly-your_key"
        )
        
    return api_key


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
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Search query cannot be empty.")

    api_key = get_tavily_api_key()
    
    try:
        client = TavilyClient(api_key=api_key)
        # Call Tavily Search API
        response = client.search(
            query=cleaned_query,
            max_results=max_results,
            search_depth="basic",
        )
    except Exception as exc:
        raise RuntimeError(f"Tavily search API error: {str(exc)}") from exc

    raw_results = response.get("results", []) if isinstance(response, dict) else []
    normalized_results: List[SearchResult] = []

    for item in raw_results:
        raw_url = item.get("url", "").strip()
        raw_title = item.get("title", "").strip() or "Untitled Resource"
        raw_content = item.get("content", "").strip() or "No description provided."
        source = extract_source_domain(raw_url)

        normalized_results.append(
            SearchResult(
                title=raw_title,
                url=raw_url,
                description=raw_content,
                source=source,
            )
        )

    return normalized_results
