import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Medical Agent Dual-RAG API"
    VERSION: str = "2.3.0"
    DEBUG: bool = False

    # 模型檔案配置
    MODEL_PATH: str | None = None
    LLM_MODEL_FILE: str = Field(default="gemma-3-4b-it.Q4_K_M.gguf", alias="LLM_MODEL_FILE")
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    
    # PostgreSQL 連線設定 (相容原本 DB_CONFIG)
    DB_USER: str = Field(default="yilin", alias="DB_USER")
    DB_PASSWORD: str = Field(default="", alias="DB_PASSWORD")
    DB_HOST: str = Field(default="localhost", alias="DB_HOST")
    DB_PORT: int = Field(default=5432, alias="DB_PORT")
    DB_NAME: str = Field(default="med_db", alias="DB_NAME")

    # Redis 連線設定
    REDIS_HOST: str = Field(default="localhost", alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT")
    REDIS_URL: str | None = None

    # 模型檔案配置
    LLM_MODEL_FILE: str = Field(default="gemma-3-4b-it.Q4_K_M.gguf", alias="LLM_MODEL_FILE")
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    @property
    def asyncpg_dsn_dict(self) -> dict:
        return {
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
        }

    @property
    def redis_connection_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()