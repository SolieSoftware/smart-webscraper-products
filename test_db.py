
from src.storage.database import get_db, save_products
from src.storage.image_storage import download_images

products = [
    {
        "name": "Test Vest",
     "price": 2.05,
     "currency": "GBP",
     "image_paths": [],
     "source_url": "www.test_my_vest.com",
     "company_name": "I am a Vest and I am here to Test",
     "image_urls" = []
     },
     {
         
     }
]


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
            "company_name": product.company_name,
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