"""LangChain tools for web scraping agent."""

import asyncio
import logging
from typing import Type, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from src.extractors.llm_extractor import extract_company_name, extract_products_from_html
from src.scrapers.browser import BrowserManager
from src.scrapers.page_scraper import scrape_page
from src.search.serp_search import search_websites
from src.storage.database import get_db, save_products
from src.storage.image_storage import download_images

logger = logging.getLogger(__name__)


# Input schemas for tools
class SearchInput(BaseModel):
    """Input for SearchTool."""
    query: str = Field(..., description="Search query to find company websites")
    num_results: int = Field(default=5, description="Number of search results to return")


class ScrapeInput(BaseModel):
    """Input for ScrapeTool."""
    url: str = Field(..., description="URL to scrape")


class ExtractInput(BaseModel):
    """Input for ExtractProductsTool."""
    html: str = Field(..., description="HTML content to extract products from")
    url: str = Field(..., description="Source URL of the HTML")
    company_name: Optional[str] = Field(None, description="Company name")


class SaveInput(BaseModel):
    """Input for SaveProductsTool."""
    products_json: str = Field(..., description="JSON string of products to save")
    company_name: Optional[str] = Field(None, description="Company name")


# Tool implementations
class SearchTool(BaseTool):
    """Tool to search for company websites."""

    name: str = "search_websites"
    description: str = (
        "Search for company websites using a search query. "
        "Input should be a search query like 'UK clothing retailers' or 'electronics stores USA'. "
        "Returns a list of relevant website URLs with titles and descriptions."
    )
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, num_results: int = 5) -> str:
        """Execute the search."""
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


class ScrapeTool(BaseTool):
    """Tool to scrape a webpage."""

    name: str = "scrape_page"
    description: str = (
        "Scrape content from a webpage URL. "
        "Input should be a valid URL. "
        "Returns the HTML content, images, and links from the page."
    )
    args_schema: Type[BaseModel] = ScrapeInput

    def _run(self, url: str) -> str:
        """Execute the scrape."""
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_run(url))
            loop.close()
            return result

        except Exception as e:
            logger.error(f"Scrape tool error: {e}")
            return f"Error scraping page: {str(e)}"

    async def _async_run(self, url: str) -> str:
        """Async scrape implementation."""
        async with BrowserManager() as browser:
            page, error = await browser.navigate_to_url(url)

            if error or not page:
                return f"Failed to load page: {error}"

            # Scrape the page
            page_data = await scrape_page(page)

            # Close the page
            await page.close()

            # Return compact summary (not full HTML to save tokens)
            output = f"Successfully scraped: {page_data['url']}\n"
            output += f"Title: {page_data['title']}\n"
            output += f"Images found: {len(page_data['image_urls'])}\n"
            output += f"Links found: {len(page_data['links'])}\n"
            output += f"\nHTML content available for extraction ({len(page_data['html'])} characters)"

            # Store HTML in tool context for extraction (we'll return full data)
            self.last_scraped_data = page_data

            return output


class ExtractProductsTool(BaseTool):
    """Tool to extract products from HTML using LLM."""

    name: str = "extract_products"
    description: str = (
        "Extract product information (names, prices, images) from scraped HTML content. "
        "This tool uses AI to intelligently parse product data from e-commerce pages. "
        "Input should include the HTML content and source URL."
    )
    args_schema: Type[BaseModel] = ExtractInput

    def _run(self, html: str, url: str, company_name: Optional[str] = None) -> str:
        """Execute product extraction."""
        try:
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

            # Store products for saving
            self.last_extracted_products = products
            self.last_company_name = company_name

            # Format output
            output = f"Extracted {len(products)} products from {company_name}:\n\n"
            for i, product in enumerate(products, 1):
                output += f"{i}. {product.name}\n"
                output += f"   Price: {product.price} {product.currency}\n"
                output += f"   Images: {len(product.image_urls)}\n"
                if product.product_url:
                    output += f"   URL: {product.product_url}\n"
                output += "\n"

            return output

        except Exception as e:
            logger.error(f"Extract tool error: {e}")
            return f"Error extracting products: {str(e)}"


class SaveProductsTool(BaseTool):
    """Tool to save products to database."""

    name: str = "save_products"
    description: str = (
        "Save extracted products to the database with downloaded images. "
        "Input should be the products data from extraction and company name. "
        "This will download product images and store everything in PostgreSQL."
    )
    args_schema: Type[BaseModel] = SaveInput

    def _run(self, products_json: str, company_name: Optional[str] = None) -> str:
        """Execute save operation."""
        try:
            import json

            # Parse products from JSON
            products_data = json.loads(products_json)

            if not products_data:
                return "No products to save."

            # Process and save products
            saved_count = 0
            with get_db() as db:
                for product in products_data:
                    # Download images
                    image_urls = product.get("image_urls", [])
                    local_image_paths = download_images(image_urls, max_images=3)

                    # Prepare product data for database
                    product_dict = {
                        "name": product.get("name"),
                        "price": product.get("price"),
                        "currency": product.get("currency", "USD"),
                        "image_paths": local_image_paths,
                        "source_url": product.get("product_url") or product.get("url", ""),
                        "company_name": company_name or "Unknown",
                        "metadata": {
                            "original_image_urls": image_urls,
                        },
                    }

                    # Save using database function
                    count = save_products([product_dict], db)
                    saved_count += count

            return f"Successfully saved {saved_count} products to database with images downloaded."

        except Exception as e:
            logger.error(f"Save tool error: {e}")
            return f"Error saving products: {str(e)}"
