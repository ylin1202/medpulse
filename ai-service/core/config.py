import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration and environment variable bindings."""

    PROJECT_NAME: str = "Medical Agent Dual-RAG API"
    VERSION: str = "2.3.0"
    DEBUG: bool = False

    # LLM & Embedding Model Configuration
    MODEL_PATH: str | None = None
    LLM_MODEL_FILE: str = Field(default="gemma-3-4b-it.Q4_K_M.gguf", alias="LLM_MODEL_FILE")
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # PostgreSQL Database Configuration
    DB_USER: str = Field(default="postgres", alias="DB_USER")
    DB_PASSWORD: str = Field(default="", alias="DB_PASSWORD")
    DB_HOST: str = Field(default="localhost", alias="DB_HOST")
    DB_PORT: int = Field(default=5432, alias="DB_PORT")
    DB_NAME: str = Field(default="med_db", alias="DB_NAME")

    # Redis Cache & Rate Limiting Configuration
    REDIS_HOST: str = Field(default="localhost", alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT")
    REDIS_URL: str | None = None

    @property
    def asyncpg_dsn_dict(self) -> dict:
        """Construct dictionary payload for AsyncPG connection pool creation."""
        return {
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
        }

    @property
    def redis_connection_url(self) -> str:
        """Construct canonical Redis connection URI."""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()