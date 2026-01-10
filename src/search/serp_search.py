"""Search engine integration using SerpAPI."""

import logging
from typing import List, Dict, Any

from serpapi import GoogleSearch

from src.config import settings

logger = logging.getLogger(__name__)


def search_websites(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for company websites using SerpAPI.

    Args:
        query: Search query (e.g., "UK clothing retailers")
        num_results: Maximum number of results to return

    Returns:
        List of search results with URL and metadata
    """
    try:
        search = GoogleSearch({
            "q": query,
            "api_key": settings.serpapi_api_key,
            "num": num_results,
        })

        results = search.get_dict()
        organic_results = results.get("organic_results", [])

        # Extract relevant information
        websites = []
        for result in organic_results[:num_results]:
            website = {
                "url": result.get("link"),
                "title": result.get("title"),
                "snippet": result.get("snippet"),
                "domain": result.get("displayed_link", "").split(" › ")[0],
            }
            websites.append(website)

        logger.info(f"Found {len(websites)} websites for query: {query}")
        return websites

    except Exception as e:
        logger.error(f"Error searching websites: {e}")
        return []


def is_ecommerce_url(url: str) -> bool:
    """
    Heuristic to determine if a URL is likely an e-commerce site.

    Args:
        url: URL to check

    Returns:
        True if URL appears to be e-commerce related
    """
    ecommerce_indicators = [
        "/products",
        "/shop",
        "/store",
        "/catalog",
        "/collection",
        "/buy",
        "product",
        "shop",
        "store",
    ]

    url_lower = url.lower()
    return any(indicator in url_lower for indicator in ecommerce_indicators)
