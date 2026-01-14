"""
Configuration management for business analytics agent.

Loads settings from environment variables and provides domain constants.
"""
from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API Keys
    openai_api_key: str = ""

    # Model Configuration
    model_id: str = "gpt-4o"

    # Data Paths
    data_dir: str = "."


# Domain constants - derived from data schema
VALID_CATEGORIES: frozenset[str] = frozenset(
    ["electronics", "clothing", "home", "grocery", "sports"]
)
VALID_REGIONS: frozenset[str] = frozenset(["north", "south", "east", "west"])
VALID_SEGMENTS: frozenset[str] = frozenset(["new", "regular", "vip"])
VALID_PAYMENT_METHODS: frozenset[str] = frozenset(
    ["credit_card", "debit_card", "paypal", "apple_pay"]
)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
