"""Browser management using Playwright."""

import asyncio
import logging
import time
from typing import Optional

from playwright.async_api import Browser, Page, Playwright, async_playwright

from src.config import settings

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instances for web scraping."""

    def __init__(self):
        """Initialize browser manager."""
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._is_running = False

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the browser."""
        if self._is_running:
            return

        logger.info("Starting Playwright browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        self._is_running = True
        logger.info("Browser started successfully")

    async def stop(self) -> None:
        """Stop the browser and cleanup."""
        if not self._is_running:
            return

        logger.info("Stopping browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._is_running = False
        logger.info("Browser stopped")
    
    async def route_intercept(self, route):
        request = route.request
        resource_type = request.resource_type
        url = request.url

        blocked_domains = [
            "google-analytics", "doubleclick", "facebook.com/tr", "criteo", "hotjar", "sentry"
        ]

        if any(domain in url for domain in blocked_domains):
            await route.abort()
            return 
        
        if resource_type in ["image", "media"]:
            await route.abort()
            return
    
        if resource_type == "font":
            await route.continue_()
            return
        
        await route.continue_90

    async def new_page(self) -> Page:
        """
        Create a new browser page with anti-detection measures.

        Returns:
            New browser page
        """
        if not self.browser:
            await self.start()
        
        page = await self.browser.new_page()

        # Set realistic user agent
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # Remove webdriver property
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        return page

    async def navigate_to_url(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30000,
        retries: int = None
    ) -> tuple[Optional[Page], Optional[str]]:
        """
        Navigate to a URL with retry logic.

        Args:
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Navigation timeout in milliseconds
            retries: Number of retry attempts (defaults to settings.max_retries)

        Returns:
            Tuple of (page, error_message)
        """
        if retries is None:
            retries = settings.max_retries

        page = None
        last_error = None

        for attempt in range(retries):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{retries})")
                page = await self.new_page()
                await page.goto(url, wait_until=wait_until, timeout=timeout)

                # Add a small delay to be respectful
                await asyncio.sleep(settings.request_delay)

                logger.info(f"Successfully loaded {url}")
                return page, None

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Navigation failed (attempt {attempt + 1}/{retries}): {e}")

                if page:
                    await page.close()
                    page = None

                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    await asyncio.sleep(wait_time)

        logger.error(f"Failed to navigate to {url} after {retries} attempts: {last_error}")
        return None, last_error

    async def screenshot(self, page: Page, path: Optional[str] = None) -> Optional[bytes]:
        """
        Take a screenshot of the page.

        Args:
            page: Page to screenshot
            path: Optional path to save screenshot

        Returns:
            Screenshot bytes
        """
        try:
            screenshot_bytes = await page.screenshot(path=path, full_page=True)
            return screenshot_bytes
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
