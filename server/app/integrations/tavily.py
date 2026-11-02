# ==============================================================================
# File: server/app/integrations/tavily.py
# Purpose: Tavily Search API client initialization and low-level search execution.
# ==============================================================================

import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from tavily import TavilyClient

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


def execute_tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> List[Dict[str, Any]]:
    """
    Executes a web search query via the official Tavily Search API client.
    
    Args:
        query: Search keywords or technical topic.
        max_results: Maximum results to retrieve.
        search_depth: "basic" or "advanced".
        
    Returns:
        List[Dict[str, Any]]: Raw search result items from Tavily API.
        
    Raises:
        ValueError: If query is blank or API key is missing.
        RuntimeError: If Tavily API request fails.
    """
    cleaned_query = query.strip() if query else ""
    if not cleaned_query:
        raise ValueError("Search query cannot be empty.")

    api_key = get_tavily_api_key()

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=cleaned_query,
            max_results=max_results,
            search_depth=search_depth,
        )
    except Exception as exc:
        raise RuntimeError(f"Tavily search API error: {str(exc)}") from exc

    return response.get("results", []) if isinstance(response, dict) else []

