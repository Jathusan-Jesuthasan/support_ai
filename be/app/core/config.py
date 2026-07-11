from functools import lru_cache
from typing import Literal
# pyrefly: ignore [missing-import]
from pydantic import MongoDsn, RedisDsn
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General Application Settings
    APP_NAME: str = "SupportAI"
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database Configuration
    MONGODB_URI: MongoDsn
    MONGODB_DB_NAME: str = "supportai"
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_MAX_IDLE_TIME_MS: int = 50000

    # Cache & Queue Configuration
    REDIS_URI: RedisDsn

    # JWT Security Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Artificial Intelligence Config
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-004"
    GENERATIVE_MODEL: str = "gemini-1.5-flash"
    GENERATIVE_MODEL_PRO: str = "gemini-1.5-pro"
    CONFIDENCE_THRESHOLD: float = 0.65


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the system configurations.
    Enforces a single read pass of the environment variables.
    """
    return Settings()
