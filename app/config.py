from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Auction Lab"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # MariaDB/MySQL only. Example:
    # mysql+pymysql://auction_app:change_me@127.0.0.1:3306/auction_lab?charset=utf8mb4
    database_url: str = (
        "mysql+pymysql://auction_app:change_me@127.0.0.1:3306/auction_lab?charset=utf8mb4"
    )
    auto_create_tables: bool = True

    # Change this in .env before deployment.
    app_secret_key: str = "change-this-secret-in-env"
    access_token_expire_minutes: int = 60 * 24
    cookie_secure: bool = False
    min_bid_increment: float = 1.0
    catalog_page_size: int = 9

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.database_url.startswith(("mysql+pymysql://", "mariadb+pymysql://")):
        raise RuntimeError(
            "DATABASE_URL должен использовать MariaDB/MySQL через PyMySQL "
            "(mysql+pymysql://... или mariadb+pymysql://...)."
        )
    return settings
