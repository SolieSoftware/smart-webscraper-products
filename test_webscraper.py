#!/usr/bin/env python3
"""Main CLI entry point for the smart web scraper."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.scraper_agent import run_scraper_agent
from src.config import settings
from src.storage.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """
    Main async function to run the scraper.

    Args:
        prompt: User prompt for scraping
    """
    prompt = """
    Collect product information for popular clothing websites including: 
    UK Clothing Sites:
    - https://www.next.co.uk/shop/gender-women-productaffiliation-clothing
    - https://www.boohoo.com/womens/clothing
    - https://www.prettylittlething.us/sale-us.html
    - https://www.riverisland.com/women/clothing
    """
    try:
        # Run the agent
        logger.info("Starting web scraper agent...")
        logger.info(f"Prompt: {prompt}")

        result = asyncio.run(run_scraper_agent(prompt))

        # Display results
        print("\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)

        if result["success"]:
            print(f"\nSuccess: {result['message']}")
            print(f"Websites scraped: {result.get('websites_scraped', 0)}")
            print(f"Products found: {result.get('products_found', 0)}")
            print(f"Products saved: {result.get('products_saved', 0)}")

            # Show sample products
            if result.get("products"):
                print("\n" + "-" * 60)
                print("SAMPLE PRODUCTS (first 10):")
                print("-" * 60)

                for i, product in enumerate(result["products"][:10], 1):
                    print(f"\n{i}. {product['name']}")
                    print(f"   Company: {product['company_name']}")
                    print(f"   Price: {product.get('price', 'N/A')} {product.get('currency', '')}")
                    print(f"   Images: {len(product.get('image_paths', []))}")
                    print(f"   URL: {product.get('source_url', 'N/A')}")

        else:
            print(f"\nFailed: {result['message']}")

        print("\n" + "=" * 60)

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        print("\n\nScraping interrupted.")
    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()