from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Auction Lab"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    database_url: str
    auto_create_tables: bool = True

    app_secret_key: str
    access_token_expire_minutes: int = 60 * 8
    cookie_secure: bool = False
    min_bid_increment: float = 1.0
    catalog_page_size: int = 9
    allowed_hosts: str = "127.0.0.1,localhost"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.database_url.startswith(("mysql+pymysql://", "mariadb+pymysql://")):
        raise RuntimeError(
            "DATABASE_URL должен использовать MariaDB/MySQL через PyMySQL "
            "(mysql+pymysql://... или mariadb+pymysql://...)."
        )
    if len(settings.app_secret_key) < 32 or settings.app_secret_key == "change-this-secret-in-env":
        raise RuntimeError("APP_SECRET_KEY должен содержать минимум 32 символа и быть уникальным.")
    if settings.app_env.lower() not in {"development", "dev", "local", "test"} and not settings.cookie_secure:
        raise RuntimeError("Для production COOKIE_SECURE должен быть true.")
    return settings
