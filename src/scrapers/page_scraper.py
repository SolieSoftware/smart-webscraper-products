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
        # Scroll down the page to trigger lazy-loaded images
        await page.evaluate("""
            async () => {
                const delay = ms => new Promise(r => setTimeout(r, ms));
                for (let i = 0; i < document.body.scrollHeight; i += 400) {
                    window.scrollTo(0, i);
                    await delay(100);
                }
                window.scrollTo(0, 0);
            }
        """)

        # Get page title
        title = await page.title()

        # Get page URL
        url = page.url

        # Get page HTML content after lazy images have loaded
        body_html = await page.content()

        # Try to extract structured data (JSON-LD)
        structured_data = await extract_structured_data(page)

        # Get all image URLs on the page (including lazy-loaded attributes)
        image_urls = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                return images.map(img => {
                    return img.src
                        || img.getAttribute('data-src')
                        || img.getAttribute('data-lazy-src')
                        || img.getAttribute('data-original')
                        || (img.srcset ? img.srcset.split(',')[0].trim().split(' ')[0] : '')
                        || '';
                }).filter(src => src && src.startsWith('http'));
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


