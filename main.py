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


def setup_database():
    """Initialize the database."""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


async def main_async(prompt: str):
    """
    Main async function to run the scraper.

    Args:
        prompt: User prompt for scraping
    """
    try:
        # Run the agent
        logger.info("Starting web scraper agent...")
        logger.info(f"Prompt: {prompt}")

        result = await run_scraper_agent(prompt)

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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Smart Web Scraper - AI-powered product information extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            python main.py "Retrieve Clothing products in the UK"
            python main.py "Find electronics from US retailers"
            python main.py "Search for furniture stores in Canada"

            The scraper will:
            1. Search for relevant company websites
            2. Scrape product information (names, prices, images)
            3. Store data in PostgreSQL database
            4. Download product images locally
        """,
    )

    parser.add_argument(
        "prompt",
        type=str,
        help="Natural language prompt describing what to scrape",
    )

    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize/reset the database before scraping",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Display configuration info
    print("=" * 60)
    print("SMART WEB SCRAPER")
    print("=" * 60)
    print(f"LLM Provider: {settings.get_llm_provider()}")
    print(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    print(f"Image Storage: {settings.image_storage_path}")
    print("=" * 60 + "\n")

    # Initialize database if requested
    if args.init_db:
        setup_database()

    # Run the scraper
    try:
        asyncio.run(main_async(args.prompt))
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
