"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Mode ---
    USE_LOCAL_MODE: bool = False
    ENABLE_WATCHER: bool = False

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # --- OpenRouter ---
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "anthropic/claude-sonnet-4-5"
    OPENROUTER_ROUTER_MODEL: str = "google/gemini-flash-1.5"

    # --- Pinecone ---
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "celestia-memoria"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"

    # --- Cohere ---
    COHERE_API_KEY: str = ""
    COHERE_RERANK_MODEL: str = "rerank-english-v3.0"
    COHERE_RERANK_TOP_N: int = 10

    # --- Ollama (local mode) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # --- LangSmith ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "celestia-memoria"

    # --- CORS ---
    FRONTEND_URL: str = "http://localhost:3000"

    # --- Server ---
    PORT: int = 8000

    def validate_production_keys(self) -> list[str]:
        """Return a list of missing keys required for production mode."""
        if self.USE_LOCAL_MODE:
            return []
        missing: list[str] = []
        if not self.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not self.SUPABASE_SERVICE_ROLE_KEY:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not self.SUPABASE_JWT_SECRET:
            missing.append("SUPABASE_JWT_SECRET")
        if not self.OPENROUTER_API_KEY:
            missing.append("OPENROUTER_API_KEY")
        if not self.PINECONE_API_KEY:
            missing.append("PINECONE_API_KEY")
        if not self.COHERE_API_KEY:
            missing.append("COHERE_API_KEY")
        return missing


@lru_cache
def get_settings() -> Settings:
    return Settings()
