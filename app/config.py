from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./content-motor.db"
    media_dir: str = "./media"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    openai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    magic_link_ttl_days: int = 30
    image_max_width: int = 1600

    allowed_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
