"""LangChain tools for web scraping agent."""

import asyncio
import json
import logging
from typing import Optional, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.extractors.llm_extractor import extract_company_name, extract_products_from_html
from src.scrapers.browser import BrowserManager
from src.scrapers.page_scraper import scrape_page
from src.search.serp_search import search_websites
from src.storage.database import get_db, save_products
from src.storage.image_storage import download_images

logger = logging.getLogger(__name__)


# Shared state for passing data between tools
_tool_state = {
    "last_scraped_data": None,
    "last_extracted_products": None,
    "last_company_name": None,
}


@tool
def search_websites_tool(query: str, num_results: int = 5) -> str:
    """Search for company websites using a search query.

    Use this to find e-commerce websites based on user requests like
    'UK clothing retailers' or 'electronics stores USA'.

    Args:
        query: Search query to find company websites
        num_results: Number of search results to return (default: 5)

    Returns:
        A formatted list of relevant website URLs with titles and descriptions.
    """
    try:
        results = search_websites(query, num_results)

        if not results:
            return "No websites found for the query."

        # Format results as a string
        output = f"Found {len(results)} websites:\n\n"
        for i, result in enumerate(results, 1):
            output += f"{i}. {result['title']}\n"
            output += f"   URL: {result['url']}\n"
            output += f"   Snippet: {result['snippet']}\n\n"

        return output

    except Exception as e:
        logger.error(f"Search tool error: {e}")
        return f"Error searching websites: {str(e)}"


@tool
def scrape_page_tool(url: str) -> str:
    """Scrape content from a webpage URL.

    Use this to fetch HTML content, images, and links from an e-commerce page.
    The scraped data will be stored for subsequent extraction.

    Args:
        url: The URL to scrape

    Returns:
        A summary of the scraped page including title, image count, and link count.
    """
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_async_scrape(url))
        loop.close()
        return result

    except Exception as e:
        logger.error(f"Scrape tool error: {e}")
        return f"Error scraping page: {str(e)}"


async def _async_scrape(url: str) -> str:
    """Async scrape implementation."""
    async with BrowserManager() as browser:
        page, error = await browser.navigate_to_url(url)

        if error or not page:
            return f"Failed to load page: {error}"

        # Scrape the page
        page_data = await scrape_page(page)

        # Close the page
        await page.close()

        # Store data in shared state for extraction
        _tool_state["last_scraped_data"] = page_data

        # Return compact summary (not full HTML to save tokens)
        output = f"Successfully scraped: {page_data['url']}\n"
        output += f"Title: {page_data['title']}\n"
        output += f"Images found: {len(page_data['image_urls'])}\n"
        output += f"Links found: {len(page_data['links'])}\n"
        output += f"\nHTML content available for extraction ({len(page_data['html'])} characters)"
        output += "\n\nUse extract_products to parse the product information from this page."

        return output


@tool
def extract_products_tool(url: str, company_name: Optional[str] = None) -> str:
    """Extract product information from the most recently scraped page.

    This tool uses AI to intelligently parse product data (names, prices, images)
    from e-commerce pages. Call this after using scrape_page.

    Args:
        url: Source URL of the page (for reference)
        company_name: Optional company name (will be derived from URL if not provided)

    Returns:
        A formatted list of extracted products with names, prices, and image counts.
    """
    try:
        # Get scraped data from state
        page_data = _tool_state.get("last_scraped_data")

        if not page_data:
            return "No scraped data available. Please use scrape_page first."

        html = page_data.get("html", "")
        if not html:
            return "No HTML content available from the scraped page."

        # Derive company name if not provided
        if not company_name:
            company_name = extract_company_name(url)

        # Run async extraction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        products = loop.run_until_complete(
            extract_products_from_html(html, url, company_name)
        )
        loop.close()

        if not products:
            return "No products found on this page."

        # Store products in state for saving
        _tool_state["last_extracted_products"] = products
        _tool_state["last_company_name"] = company_name

        # Format output
        output = f"Extracted {len(products)} products from {company_name}:\n\n"
        for i, product in enumerate(products, 1):
            output += f"{i}. {product.name}\n"
            output += f"   Price: {product.price} {product.currency}\n"
            output += f"   Images: {len(product.image_urls)}\n"
            if product.product_url:
                output += f"   URL: {product.product_url}\n"
            output += "\n"

        output += "\nUse save_products to store these products in the database."

        return output

    except Exception as e:
        logger.error(f"Extract tool error: {e}")
        return f"Error extracting products: {str(e)}"


@tool
def save_products_tool(company_name: Optional[str] = None) -> str:
    """Save the most recently extracted products to the database.

    This will download product images and store everything in the database.
    Call this after using extract_products.

    Args:
        company_name: Optional company name override

    Returns:
        Confirmation of how many products were saved.
    """
    try:
        # Get extracted products from state
        products = _tool_state.get("last_extracted_products")

        if not products:
            return "No extracted products available. Please use extract_products first."

        # Use stored company name if not provided
        if not company_name:
            company_name = _tool_state.get("last_company_name", "Unknown")

        # Process and save products
        saved_count = 0
        with get_db() as db:
            for product in products:
                # Download images
                image_urls = product.image_urls if hasattr(product, 'image_urls') else []
                local_image_paths = download_images(image_urls, max_images=3)

                # Prepare product data for database
                product_dict = {
                    "name": product.name,
                    "price": product.price,
                    "currency": getattr(product, 'currency', 'USD'),
                    "image_paths": local_image_paths,
                    "source_url": getattr(product, 'product_url', '') or "",
                    "company_name": company_name,
                    "metadata": {
                        "original_image_urls": image_urls,
                    },
                }

                # Save using database function
                count = save_products([product_dict], db)
                saved_count += count

        # Clear state after saving
        _tool_state["last_extracted_products"] = None
        _tool_state["last_company_name"] = None

        return f"Successfully saved {saved_count} products to database with images downloaded."

    except Exception as e:
        logger.error(f"Save tool error: {e}")
        return f"Error saving products: {str(e)}"


def get_scraper_tools() -> List:
    """Get all scraper tools for the agent.

    Returns:
        List of tool functions
    """
    return [
        search_websites_tool,
        scrape_page_tool,
        extract_products_tool,
        save_products_tool,
    ]
