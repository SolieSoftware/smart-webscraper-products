"""Page scraping utilities."""

import logging
from typing import Optional, Dict, Any

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def scrape_page(page: Page) -> Dict[str, Any]:
    """
    Scrape content from a page.

    Args:
        page: Playwright page object

    Returns:
        Dictionary containing page content and metadata
    """
    try:
        # Get page title
        title = await page.title()

        # Get page URL
        url = page.url

        # Get page HTML content (limited to body to reduce size)
        body_html = await page.content()

        # Try to extract structured data (JSON-LD)
        structured_data = await extract_structured_data(page)

        # Get all image URLs on the page
        image_urls = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                return images.map(img => img.src).filter(src => src && src.startsWith('http'));
            }
        """)

        # Get all links on the page
        links = await page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                return anchors.map(a => a.href);
            }
        """)

        result = {
            "url": url,
            "title": title,
            "html": body_html,
            "structured_data": structured_data,
            "image_urls": image_urls[:50],  # Limit to first 50 images
            "links": links[:100],  # Limit to first 100 links
        }

        logger.info(f"Successfully scraped page: {url}")
        return result

    except Exception as e:
        logger.error(f"Error scraping page: {e}")
        return {
            "url": page.url if page else "unknown",
            "error": str(e),
            "html": "",
            "image_urls": [],
            "links": [],
        }


async def extract_structured_data(page: Page) -> Optional[Dict[str, Any]]:
    """
    Extract structured data (JSON-LD, microdata) from page.

    Args:
        page: Playwright page object

    Returns:
        Structured data dictionary or None
    """
    try:
        # Try to extract JSON-LD
        json_ld = await page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                return scripts.map(script => {
                    try {
                        return JSON.parse(script.textContent);
                    } catch {
                        return null;
                    }
                }).filter(data => data !== null);
            }
        """)

        if json_ld:
            return {"json_ld": json_ld}

        return None

    except Exception as e:
        logger.debug(f"Could not extract structured data: {e}")
        return None


async def find_product_links(page: Page) -> list[str]:
    """
    Find product page links on the current page.

    Args:
        page: Playwright page object

    Returns:
        List of product URLs
    """
    try:
        product_links = await page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                const productKeywords = ['product', 'item', 'p/', '/pd/', '/dp/', 'shop'];

                return anchors
                    .map(a => a.href)
                    .filter(href => {
                        const lowerHref = href.toLowerCase();
                        return productKeywords.some(keyword => lowerHref.includes(keyword));
                    })
                    .filter((href, index, self) => self.indexOf(href) === index); // Unique
            }
        """)

        logger.info(f"Found {len(product_links)} potential product links")
        return product_links[:20]  # Limit to first 20 product links

    except Exception as e:
        logger.error(f"Error finding product links: {e}")
        return []


async def extract_text_content(page: Page, selector: str) -> Optional[str]:
    """
    Extract text content from page using CSS selector.

    Args:
        page: Playwright page object
        selector: CSS selector

    Returns:
        Extracted text or None
    """
    try:
        element = await page.query_selector(selector)
        if element:
            return await element.inner_text()
        return None
    except Exception as e:
        logger.debug(f"Could not extract text from selector {selector}: {e}")
        return None
