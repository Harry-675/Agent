"""Application settings and configuration."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database Configuration
    database_url: str = "postgresql://postgres:password@localhost:5432/news_aggregator"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "news_aggregator"
    db_user: str = "postgres"
    db_password: str = "password"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Alibaba Bailian API Configuration
    bailian_api_key: str = "dummy"
    bailian_api_endpoint: str = "http://10.240.98.184:8080/v1"
    bailian_model: str = "qwen3.5-397b-a17b-fp8"
    
    # Application Configuration
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    
    # News Crawler Configuration
    crawler_timeout: int = 30
    crawler_interval_minutes: int = 15
    
    # AI Processing Configuration
    similarity_threshold: float = 0.85
    dedup_timeout: int = 5
    classification_timeout: int = 3
    max_categories: int = 3
    
    # Performance Configuration
    max_concurrent_crawls: int = 10
    cache_ttl_seconds: int = 300
    max_concurrent_users: int = 100
    
    # Reports Configuration
    reports_dir: str = "reports"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_database_url() -> str:
    """Get the database connection URL."""
    settings = get_settings()
    return settings.database_url
