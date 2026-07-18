"""
Centralized application configuration.

All runtime configuration is read from environment variables (with sane
local-dev defaults) so the same codebase runs identically in Docker,
CI, or a developer's laptop. See `.env.example` at the repo root.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "Enterprise RAG Knowledge Platform"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security / Auth ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://rag_user:rag_password@localhost:5432/rag_db"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Storage ---
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_MB: int = 25

    # --- Vector store (Qdrant) ---
    # Local/embedded mode by default: no separate Qdrant server required.
    # Set QDRANT_URL to use a real Qdrant server instead (e.g. in docker-compose).
    QDRANT_URL: Optional[str] = None
    QDRANT_LOCAL_PATH: str = "./storage/qdrant"
    QDRANT_COLLECTION: str = "documents"

    # --- Embeddings ---
    # Fully local by default -- no API key required.
    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384

    # --- Reranking ---
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANK_TOP_K: int = 5
    RETRIEVAL_TOP_K: int = 20

    # --- Chunking ---
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # --- LLM (generation step) ---
    # Pluggable: if no OPENAI_API_KEY is set, the pipeline falls back to a
    # deterministic extractive synthesizer so the whole system still runs
    # end-to-end with zero external API keys.
    LLM_PROVIDER: str = "auto"  # "auto" | "openai" | "extractive"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
