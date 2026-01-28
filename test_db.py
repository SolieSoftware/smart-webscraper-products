
from src.storage.database import get_db, save_products
from src.storage.image_storage import download_images

import logging

logger = logging.getLogger(__name__)

products = [
{
    "name": "Wireless Headphones",
    "price": 49.99,
    "currency": "USD",
    "image_paths": [],
    "source_url": "www.test_headphones.com",
    "company_name": "AudioTech Inc",
    "image_urls": []
},
{
    "name": "USB-C Cable",
    "price": 12.50,
    "currency": "EUR",
    "image_paths": [],
    "source_url": "www.test_cables.com",
    "company_name": "CablePro Ltd",
    "image_urls": []
},
{
    "name": "Laptop Stand",
    "price": 35.00,
    "currency": "GBP",
    "image_paths": [],
    "source_url": "www.test_stands.com",
    "company_name": "DeskGear Co",
    "image_urls": []
},
{
    "name": "Phone Case",
    "price": 15.99,
    "currency": "USD",
    "image_paths": [],
    "source_url": "www.test_cases.com",
    "company_name": "ProtectPhone",
    "image_urls": []
},
{
    "name": "Mechanical Keyboard",
    "price": 79.99,
    "currency": "GBP",
    "image_paths": [],
    "source_url": "www.test_keyboards.com",
    "company_name": "KeyMaster Industries",
    "image_urls": []
}
]

all_products = []

with get_db() as db:
    for product in products:
        # Download images
        # local_images = download_images(
        #     product.image_urls,
        #     max_images=3
        # )

        # Prepare product dict
        product_dict = {
            "name": product["name"],
            "price": product["price"],
            "currency": product["currency"],
            "image_paths": product["image_paths"],
            "source_url": product["source_url"],
            "company_name": product["company_name"],
            "metadata": {
                "original_image_urls": product["image_urls"],
            },
        }

        # Save to database
        saved = save_products([product_dict], db)
        total_saved += saved
        all_products.append(product_dict)

logger.info(f"Saved {len(products)} products from {company_name}")
