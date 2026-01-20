"""LLM-based product data extraction."""

import json
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

from src.config import settings

logger = logging.getLogger(__name__)


class ProductData(BaseModel):
    """Structured product data model."""

    name: str = Field(..., description="Product name")
    price: Optional[float] = Field(None, description="Product price as a number")
    currency: str = Field(default="USD", description="Currency code (e.g., USD, GBP, EUR)")
    image_urls: List[str] = Field(default_factory=list, description="Product image URLs")
    product_url: Optional[str] = Field(None, description="Direct product page URL")

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, v):
        """Parse price from string or number."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Remove currency symbols and commas
            price_str = re.sub(r"[^\d.]", "", v)
            try:
                return float(price_str) if price_str else None
            except ValueError:
                return None
        return None


def get_llm_client():
    """Get the appropriate LLM client based on configuration."""
    provider = settings.get_llm_provider()

    if provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    elif provider == "anthropic":
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def clean_html(html: str, max_length: int = 50000) -> str:
    """
    Clean and simplify HTML for LLM processing.

    Args:
        html: Raw HTML content
        max_length: Maximum length of cleaned HTML

    Returns:
        Cleaned HTML string
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        # Remove script, style, and other non-content tags
        for tag in soup(["script", "style", "meta", "link", "noscript"]):
            tag.decompose()

        # Get text with some structure preserved
        text = soup.get_text(separator="\n", strip=True)

        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "...[truncated]"

        return text

    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}")
        return html[:max_length]


async def extract_products_from_html(
    html: str,
    url: str,
    company_name: Optional[str] = None
) -> List[ProductData]:
    """
    Extract product information from HTML using LLM.

    Args:
        html: HTML content of the page
        url: URL of the page
        company_name: Optional company name

    Returns:
        List of extracted products
    """
    try:
        # Clean HTML for LLM processing
        cleaned_html = clean_html(html)

        # Debug: log cleaned HTML sample
        logger.debug(f"Cleaned HTML length: {len(cleaned_html)}")
        logger.debug(f"Cleaned HTML sample (first 1000 chars): {cleaned_html[:1000]}")

        # Create LLM client
        llm = get_llm_client()

        # System message with instructions
        system_msg = SystemMessage(content="""You are an expert at extracting product information from e-commerce websites.

Your task is to analyze the provided HTML content and extract all product listings you can find.

For each product, extract:
1. Product name (required)
2. Price (as a number, required if available)
3. Currency (e.g., USD, GBP, EUR)
4. Image URLs (list of product image URLs)
5. Product URL (direct link to product page, if available)

Return the data as a JSON array of products. Each product should be a JSON object with the fields: name, price, currency, image_urls, product_url.

If no products are found, return an empty array [].

Example format:
[
  {
    "name": "Cotton T-Shirt",
    "price": 29.99,
    "currency": "USD",
    "image_urls": ["https://example.com/img1.jpg"],
    "product_url": "https://example.com/product/123"
  }
]

Only return the JSON array, nothing else.""")

        # User message with HTML content
        user_msg = HumanMessage(content=f"""Extract all products from this e-commerce page.

URL: {url}
Company: {company_name or "Unknown"}

HTML Content:
{cleaned_html}

Return only the JSON array of products.""")

        # Invoke LLM
        logger.info(f"Extracting products from {url} using LLM...")
        response = llm.invoke([system_msg, user_msg])

        # Parse response
        response_text = response.content.strip()

        # Debug: log LLM response
        logger.debug(f"LLM response: {response_text[:2000]}")

        # Try to extract JSON from response
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text

        # Parse JSON
        products_data = json.loads(json_str)

        # Validate and create ProductData objects
        products = []
        for product_dict in products_data:
            try:
                product = ProductData(**product_dict)
                products.append(product)
            except Exception as e:
                logger.warning(f"Failed to validate product: {e}")
                continue

        logger.info(f"Extracted {len(products)} products from {url}")
        return products

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Response: {response_text[:500]}")
        return []
    except Exception as e:
        logger.error(f"Error extracting products: {e}")
        return []


def extract_company_name(url: str) -> str:
    """
    Extract company name from URL.

    Args:
        url: Website URL

    Returns:
        Company name
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        # Remove TLD
        company = domain.split(".")[0]
        return company.title()
    except Exception:
        return "Unknown"
