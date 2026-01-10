"""Database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.storage.models import Base


# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database by creating all tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.

    Usage:
        with get_db() as db:
            products = db.query(Product).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_products(products: list, db: Session) -> int:
    """
    Save a list of product dictionaries to the database.

    Args:
        products: List of product data dictionaries
        db: Database session

    Returns:
        Number of products saved
    """
    from src.storage.models import Product

    saved_count = 0
    for product_data in products:
        # Check if product already exists (by URL and company)
        existing = db.query(Product).filter(
            Product.source_url == product_data.get("source_url"),
            Product.company_name == product_data.get("company_name")
        ).first()

        if not existing:
            product = Product(**product_data)
            db.add(product)
            saved_count += 1

    db.commit()
    return saved_count
