"""Image download and storage utilities."""

import hashlib
import io
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from src.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded Supabase client
_supabase_client = None


def get_supabase_client():
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is None and settings.is_supabase_configured():
        from supabase import create_client
        _supabase_client = create_client(
            settings.supabase_project_url,
            settings.supabase_project_api
        )
    return _supabase_client


def download_image(url: str, save_dir: Optional[Path] = None) -> Optional[str]:
    """
    Download an image from URL and save to storage (local or Supabase).

    Args:
        url: Image URL
        save_dir: Directory to save image (only used for local storage)

    Returns:
        Storage path/URL if successful, None otherwise
    """
    if settings.use_supabase_storage():
        return _download_image_supabase(url)
    else:
        return _download_image_local(url, save_dir)


def _download_image_supabase(url: str) -> Optional[str]:
    """Download image and upload to Supabase Storage."""
    try:
        # Generate filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        parsed_url = urlparse(url)
        extension = Path(parsed_url.path).suffix or ".jpg"

        if extension not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            extension = ".jpg"

        filename = f"{url_hash}{extension}"
        bucket = settings.supabase_storage_bucket

        client = get_supabase_client()
        if not client:
            logger.error("Supabase client not available")
            return None

        # Check if image already exists in Supabase
        try:
            existing = client.storage.from_(bucket).list()
            if any(f.get("name") == filename for f in existing):
                public_url = client.storage.from_(bucket).get_public_url(filename)
                logger.debug(f"Image already exists in Supabase: {filename}")
                return public_url
        except Exception:
            pass  # Bucket might not exist yet or other issue, continue with upload

        # Download image
        logger.info(f"Downloading image from {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image_data = response.content

        # Verify it's a valid image
        try:
            img = Image.open(io.BytesIO(image_data))
            img.verify()
        except Exception as e:
            logger.warning(f"Downloaded file is not a valid image: {e}")
            return None

        # Determine content type
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(extension, "image/jpeg")

        # Upload to Supabase Storage
        client.storage.from_(bucket).upload(
            filename,
            image_data,
            file_options={"content-type": content_type}
        )

        public_url = client.storage.from_(bucket).get_public_url(filename)
        logger.info(f"Image uploaded to Supabase: {public_url}")
        return public_url

    except requests.RequestException as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error uploading image to Supabase: {e}")
        return None


def _download_image_local(url: str, save_dir: Optional[Path] = None) -> Optional[str]:
    """Download image and save to local filesystem."""
    if save_dir is None:
        save_dir = settings.image_storage_path

    try:
        # Generate filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        parsed_url = urlparse(url)
        extension = Path(parsed_url.path).suffix or ".jpg"

        # Ensure extension is valid
        if extension not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            extension = ".jpg"

        filename = f"{url_hash}{extension}"
        filepath = save_dir / filename

        # Check if already downloaded
        if filepath.exists():
            logger.debug(f"Image already exists: {filepath}")
            return str(filepath)

        # Download image
        logger.info(f"Downloading image from {url}")
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()

        # Save image
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify it's a valid image
        try:
            with Image.open(filepath) as img:
                img.verify()
        except Exception as e:
            logger.warning(f"Downloaded file is not a valid image: {e}")
            filepath.unlink()  # Delete invalid file
            return None

        logger.info(f"Image saved to {filepath}")
        return str(filepath)

    except requests.RequestException as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


def download_images(urls: List[str], max_images: int = 5) -> List[str]:
    """
    Download multiple images and return their local paths.

    Args:
        urls: List of image URLs
        max_images: Maximum number of images to download

    Returns:
        List of local file paths for successfully downloaded images
    """
    local_paths = []

    for url in urls[:max_images]:
        path = download_image(url)
        if path:
            local_paths.append(path)

        # Stop if we have enough images
        if len(local_paths) >= max_images:
            break

    logger.info(f"Downloaded {len(local_paths)} out of {len(urls[:max_images])} images")
    return local_paths


def get_image_info(filepath: str) -> Optional[dict]:
    """
    Get information about an image file.

    Args:
        filepath: Path to image file

    Returns:
        Dictionary with image metadata
    """
    try:
        with Image.open(filepath) as img:
            return {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
            }
    except Exception as e:
        logger.error(f"Error getting image info for {filepath}: {e}")
        return None
