"""Configuration management for the web scraper."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM API Keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")

    # Search API
    serpapi_api_key: str = Field(..., description="SerpAPI key for web search")

    # Database
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection string (used if Supabase not configured)"
    )

    # Supabase Configuration
    supabase_project_url: Optional[str] = Field(
        default=None,
        description="Supabase project URL"
    )
    supabase_project_api: Optional[str] = Field(
        default=None,
        description="Supabase API key (anon/public key)"
    )
    supabase_db_password: Optional[str] = Field(
        default=None,
        description="Supabase database password for direct PostgreSQL connection"
    )
    supabase_storage_bucket: str = Field(
        default="product-images",
        description="Supabase storage bucket name for images"
    )

    # Storage
    image_storage_path: Path = Field(
        default=Path("data/images"),
        description="Path to store downloaded images"
    )

    # Scraping settings
    max_retries: int = Field(default=3, description="Maximum retry attempts for failed requests")
    request_delay: float = Field(default=2.0, description="Delay between requests in seconds")

    # LLM settings
    llm_model: str = Field(default="gpt-4", description="LLM model to use")
    llm_temperature: float = Field(default=0.0, description="LLM temperature")

    @field_validator("image_storage_path", mode="before")
    @classmethod
    def validate_image_path(cls, v):
        """Ensure image storage path exists."""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("openai_api_key", "anthropic_api_key", mode="after")
    @classmethod
    def check_llm_key(cls, v, info):
        """Validate that at least one LLM API key is provided."""
        # This will be checked after all fields are validated
        return v

    def model_post_init(self, __context) -> None:
        """Post-initialization validation."""
        if not self.openai_api_key and not self.anthropic_api_key:
            raise ValueError(
                "At least one LLM API key must be provided "
                "(OPENAI_API_KEY or ANTHROPIC_API_KEY)"
            )

    def get_llm_provider(self) -> str:
        """Determine which LLM provider to use."""
        if self.openai_api_key:
            return "openai"
        elif self.anthropic_api_key:
            return "anthropic"
        else:
            raise ValueError("No LLM API key configured")

    def is_supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_project_url and self.supabase_project_api)

    def get_database_url(self) -> str:
        """Get the database URL, preferring Supabase if configured."""
        if self.is_supabase_configured() and self.supabase_db_password:
            # Extract project ref from Supabase URL
            # URL format: https://<project_ref>.supabase.co
            project_ref = self.supabase_project_url.replace("https://", "").replace(".supabase.co", "")
            # Supabase PostgreSQL connection string format
            return self.database_url
        elif self.database_url:
            return self.database_url
        else:
            raise ValueError(
                "No database configured. Set DATABASE_URL or Supabase credentials "
                "(SUPABASE_PROJECT_URL, SUPABASE_PROJECT_API, SUPABASE_DB_PASSWORD)"
            )

    def use_supabase_storage(self) -> bool:
        """Check if Supabase storage should be used for images."""
        return self.is_supabase_configured()


# Global settings instance
settings = Settings()
