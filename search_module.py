"""
search_module.py
Real-Time Web Search & Source Retrieval Engine
Supports DuckDuckGo Search (free/keyless) with optional Tavily API integration.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("search_module")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()


def detect_search_intent(query: str) -> bool:
    """
    Detects if the query asks for live/current web information,
    real-time facts, recent news, or explicit web search.
    """
    if not query:
        return False
    
    q = query.lower()

    # Explicit search triggers
    search_keywords = [
        "search", "lookup", "look up", "google", "find online",
        "latest", "current", "news", "today", "yesterday", "recent",
        "update", "who won", "score", "stock price", "weather",
        "release date", "price of", "who is currently", "what happened",
        "تلاش کرو", "تازہ ترین", "خبریں", "آج کا", "موجودہ"
    ]

    for kw in search_keywords:
        if kw in q:
            return True

    # Questions about specific real-time entities / dates (e.g. 2025, 2026)
    if re.search(r"\b(2025|2026|live|trending|breaking)\b", q):
        return True

    return False


def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Performs real-time web search via DuckDuckGo."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                title = item.get("title", "").strip()
                url = item.get("href", item.get("url", "")).strip()
                snippet = item.get("body", item.get("snippet", "")).strip()
                if title and url:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    return results


def search_tavily(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Performs real-time search via Tavily API if key is configured."""
    key = os.getenv("TAVILY_API_KEY", "").strip() or TAVILY_API_KEY
    if not key:
        return []
    
    results = []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        response = client.search(query=query, max_results=max_results)
        for item in response.get("results", []):
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            snippet = item.get("content", "").strip()
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
    except Exception as e:
        logger.warning(f"Tavily search error: {e}")
    return results


def perform_web_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Orchestrates web search:
    1. Tries Tavily if API key is provided.
    2. Fallbacks to DuckDuckGo search (fast & free).
    Returns list of { "title": str, "url": str, "snippet": str }.
    """
    clean_q = re.sub(r"^(please\s+)?(search\s+for|look\s+up|find|search)\s+", "", query, flags=re.IGNORECASE).strip()
    if not clean_q:
        clean_q = query

    logger.info(f"Executing web search for: '{clean_q}'")

    # 1. Try Tavily if key present
    if os.getenv("TAVILY_API_KEY", "").strip():
        tavily_results = search_tavily(clean_q, max_results)
        if tavily_results:
            return tavily_results

    # 2. DuckDuckGo Search (Primary keyless engine)
    ddg_results = search_duckduckgo(clean_q, max_results)
    if ddg_results:
        return ddg_results

    # 3. Fallback retry with raw query if cleaned query had no matches
    if clean_q != query:
        return search_duckduckgo(query, max_results)

    return []


def format_search_context(sources: List[Dict[str, str]]) -> str:
    """Formats retrieved sources into structured context for the Groq LLM."""
    if not sources:
        return ""

    lines = ["[LIVE REAL-TIME WEB SEARCH RESULTS]:"]
    for i, src in enumerate(sources, start=1):
        lines.append(f"{i}. Title: {src['title']}")
        lines.append(f"   URL: {src['url']}")
        lines.append(f"   Snippet: {src['snippet']}")
    lines.append(
        "\nInstruction: Answer the user's question accurately using these real-time search results. "
        "Keep your response concise and conversational for voice output."
    )
    return "\n".join(lines)

