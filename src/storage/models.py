"""Database models for product storage."""

import uuid
from datetime import datetime


from sqlalchemy import DECIMAL, TIMESTAMP, Column, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Product(Base):
    """Product model for storing scraped product information."""

    __tablename__ = "products"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Product information
    name = Column(Text, nullable=False, index=True)
    price = Column(DECIMAL(10, 2), nullable=True)
    currency = Column(String(3), nullable=True, default="USD")

    # Image storage (array of local file paths)
    image_paths = Column(JSONB, nullable=True, default=list)

    # Source information
    source_url = Column(Text, nullable=False)
    company_name = Column(String(255), nullable=True, index=True)

    # Metadata
    scraped_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    # metadata = Column(JSONB, nullable=True, default=dict)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_product_company_url", "company_name", "source_url"),
        Index("idx_product_scraped_at", "scraped_at"),
    )

    def __repr__(self) -> str:
        """String representation of Product."""
        return (
            f"<Product(id={self.id}, name='{self.name}', "
            f"price={self.price}, company='{self.company_name}')>"
        )

