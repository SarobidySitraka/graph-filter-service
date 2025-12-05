"""Application configuration management"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Neo4j Configuration
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j uri")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j database name")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j database password")

    # Application Configuration
    APP_NAME: str = "Neo4j Filter Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000:",
    ]

    # Pagination Defaults
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()