"""Main LangChain agent orchestrator for web scraping."""

import asyncio
import json
import logging
from typing import List, Optional

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from src.agents.tools import get_scraper_tools
from src.config import settings
from src.extractors.llm_extractor import extract_company_name, extract_products_from_html
from src.scrapers.browser import BrowserManager
from src.scrapers.page_scraper import scrape_page
from src.search.serp_search import search_websites
from src.storage.database import get_db, save_products
from src.storage.image_storage import download_images

logger = logging.getLogger(__name__)


# System prompt for the agent
SYSTEM_PROMPT = """You are an intelligent web scraping agent specialized in extracting product information from e-commerce websites.

Your goal is to help users find and extract product data (names, prices, images) from company websites based on their requests.

When given a task like "Retrieve Clothing products in the UK", follow this workflow:

1. Use search_websites_tool to find relevant company websites
2. For each promising website:
   - Use scrape_page_tool to get the page content
   - Use extract_products_tool to parse product information using AI
   - Use save_products_tool to store the data in the database
3. Report a summary of products found and saved

Be systematic and thorough. Handle errors gracefully and try alternative approaches if something fails."""


def create_scraper_agent():
    """
    Create the web scraper agent with all tools using the modern LangGraph-based approach.

    Returns:
        CompiledStateGraph - a runnable agent graph
    """
    # Get LLM based on configuration
    provider = settings.get_llm_provider()

    if provider == "openai":
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    elif provider == "anthropic":
        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    # Get tools
    tools = get_scraper_tools()

    # Create agent using the new LangGraph-based create_agent
    # This returns a CompiledStateGraph that can be invoked directly
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    return agent


def invoke_scraper_agent(prompt: str) -> dict:
    """
    Invoke the scraper agent with a user prompt using the LangGraph agent.

    Args:
        prompt: User prompt like "Retrieve Clothing products in the UK"

    Returns:
        Dictionary with agent response
    """
    agent = create_scraper_agent()

    # Invoke the agent - LangGraph agents use messages format
    result = agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    return result


async def run_scraper_agent(prompt: str) -> dict:
    """
    Run the scraper agent with a user prompt.

    This is a simplified version that directly orchestrates the scraping
    without using the full agent (for better control and reliability).

    Args:
        prompt: User prompt like "Retrieve Clothing products in the UK"

    Returns:
        Dictionary with results
    """
    logger.info(f"Starting scraper agent with prompt: {prompt}")

    try:
        # Step 1: Search for websites
        logger.info("Searching for relevant websites...")
        search_query = prompt  # Use prompt directly as search query
        websites = search_websites(search_query, num_results=10)

        if not websites:
            return {
                "success": False,
                "message": "No websites found for the search query",
                "products_saved": 0,
            }

        logger.info(f"Found {len(websites)} websites to scrape")

        # Step 2: Scrape and extract from each website
        all_products = []
        total_saved = 0

        async with BrowserManager() as browser:
            for website in websites:
                url = website["url"]
                company_name = extract_company_name(url)

                logger.info(f"Scraping {company_name} at {url}")

                try:
                    # Navigate to page
                    page, error = await browser.navigate_to_url(url)
                    if error or not page:
                        logger.warning(f"Failed to load {url}: {error}")
                        continue

                    # Scrape page content
                    page_data = await scrape_page(page)
                    await page.close()

                    # Extract products using LLM
                    logger.info(f"Extracting products from {company_name}")
                    products = await extract_products_from_html(
                        page_data["html"],
                        url,
                        company_name
                    )

                    if not products:
                        logger.info(f"No products found on {company_name}")
                        continue

                    logger.info(f"Found {len(products)} products on {company_name}")

                    # Save products to database
                    with get_db() as db:
                        for product in products:
                            # Download images
                            local_images = download_images(
                                product.image_urls,
                                max_images=3
                            )

                            # Prepare product dict
                            product_dict = {
                                "name": product.name,
                                "price": product.price,
                                "currency": product.currency,
                                "image_paths": local_images,
                                "source_url": product.product_url or url,
                                "company_name": company_name,
                                "metadata": {
                                    "original_image_urls": product.image_urls,
                                },
                            }

                            # Save to database
                            saved = save_products([product_dict], db)
                            total_saved += saved
                            all_products.append(product_dict)

                    logger.info(f"Saved {len(products)} products from {company_name}")

                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    continue

        # Return summary
        return {
            "success": True,
            "message": f"Successfully scraped {len(websites)} websites",
            "websites_scraped": len(websites),
            "products_found": len(all_products),
            "products_saved": total_saved,
            "products": all_products[:10],  # Sample of products
        }

    except Exception as e:
        logger.error(f"Agent error: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "products_saved": 0,
        }
