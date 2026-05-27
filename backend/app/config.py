from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения, загружаемая из .env файла."""
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # По умолчанию 24 часа
    DEBUG: bool = False
    BASE_URL: str = "http://localhost:8000"
    COOKIE_SECURE: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:8000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()