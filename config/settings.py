"""
Central configuration using Pydantic Settings.
All values are loaded from environment variables / .env file.
"""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    database_url: str = Field(..., alias="DATABASE_URL")
    database_pool_size: int = Field(10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(20, alias="DATABASE_MAX_OVERFLOW")

    # --- Redis ---
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # --- LLM ---
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")

    # --- X (Twitter) ---
    twitter_bearer_token: str = Field("", alias="TWITTER_BEARER_TOKEN")
    twitter_api_key: str = Field("", alias="TWITTER_API_KEY")
    twitter_api_secret: str = Field("", alias="TWITTER_API_SECRET")
    twitter_access_token: str = Field("", alias="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: str = Field("", alias="TWITTER_ACCESS_SECRET")

    # --- TikTok ---
    tiktok_client_key: str = Field("", alias="TIKTOK_CLIENT_KEY")
    tiktok_client_secret: str = Field("", alias="TIKTOK_CLIENT_SECRET")
    tiktok_access_token: str = Field("", alias="TIKTOK_ACCESS_TOKEN")

    # --- LinkedIn ---
    linkedin_client_id: str = Field("", alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str = Field("", alias="LINKEDIN_CLIENT_SECRET")
    linkedin_access_token: str = Field("", alias="LINKEDIN_ACCESS_TOKEN")
    linkedin_person_urn: str = Field("", alias="LINKEDIN_PERSON_URN")

    # --- Instagram ---
    instagram_access_token: str = Field("", alias="INSTAGRAM_ACCESS_TOKEN")
    instagram_business_account_id: str = Field("", alias="INSTAGRAM_BUSINESS_ACCOUNT_ID")
    instagram_app_id: str = Field("", alias="INSTAGRAM_APP_ID")
    instagram_app_secret: str = Field("", alias="INSTAGRAM_APP_SECRET")

    # --- Agent ---
    george_env: str = Field("production", alias="GEORGE_ENV")
    george_cycle_mode: str = Field("full", alias="GEORGE_CYCLE_MODE")
    george_log_level: str = Field("INFO", alias="GEORGE_LOG_LEVEL")
    george_max_retries: int = Field(3, alias="GEORGE_MAX_RETRIES")
    george_retry_base_seconds: int = Field(2, alias="GEORGE_RETRY_BASE_SECONDS")

    # --- Content ---
    content_niches: str = Field(
        "entrepreneurship,financial_freedom,network_marketing,anti_system",
        alias="CONTENT_NICHES",
    )
    content_languages: str = Field("en", alias="CONTENT_LANGUAGES")
    max_posts_per_platform_per_day: int = Field(3, alias="MAX_POSTS_PER_PLATFORM_PER_DAY")

    # --- Alerts ---
    alert_email: str = Field("", alias="ALERT_EMAIL")
    smtp_host: str = Field("", alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_user: str = Field("", alias="SMTP_USER")
    smtp_password: str = Field("", alias="SMTP_PASSWORD")

    @property
    def niches(self) -> List[str]:
        return [n.strip() for n in self.content_niches.split(",") if n.strip()]

    @property
    def is_semi_autonomous(self) -> bool:
        return self.george_cycle_mode == "semi"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
