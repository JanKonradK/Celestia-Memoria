"""LLM provider abstraction: OpenRouter (production) or Ollama (local)."""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

# Model slug -> OpenRouter model ID mapping
MODEL_MAP = {
    "default": None,  # Uses OPENROUTER_DEFAULT_MODEL from settings
    "router": None,   # Uses OPENROUTER_ROUTER_MODEL from settings
}


def get_llm(model_slug: str = "default") -> ChatOpenAI:
    """Get a ChatOpenAI instance configured for the specified model.

    In production: routes through OpenRouter to access various models.
    In local mode: connects to Ollama's OpenAI-compatible API.

    Args:
        model_slug: One of 'default', 'router', or a full model ID string.

    Returns:
        A configured ChatOpenAI instance.
    """
    settings = get_settings()

    if settings.USE_LOCAL_MODE:
        return _get_ollama_llm(model_slug)

    return _get_openrouter_llm(model_slug)


def _get_openrouter_llm(model_slug: str) -> ChatOpenAI:
    """Create a ChatOpenAI configured for OpenRouter."""
    settings = get_settings()

    if model_slug == "router":
        model_id = settings.OPENROUTER_ROUTER_MODEL
    elif model_slug == "default":
        model_id = settings.OPENROUTER_DEFAULT_MODEL
    else:
        model_id = model_slug

    llm = ChatOpenAI(
        model=model_id,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        temperature=0.1,
        max_tokens=4096,
        model_kwargs={
            "extra_headers": {
                "HTTP-Referer": settings.FRONTEND_URL,
                "X-Title": "Celestia Memoria",
            },
        },
    )

    logger.debug("Created OpenRouter LLM: %s", model_id)
    return llm


def _get_ollama_llm(model_slug: str) -> ChatOpenAI:
    """Create a ChatOpenAI configured for local Ollama."""
    settings = get_settings()

    # In local mode, use the same Ollama model for everything
    model_id = settings.OLLAMA_MODEL

    llm = ChatOpenAI(
        model=model_id,
        openai_api_key="ollama",  # Ollama doesn't need a real key
        openai_api_base=f"{settings.OLLAMA_BASE_URL}/v1",
        temperature=0.1,
        max_tokens=4096,
    )

    logger.debug("Created Ollama LLM: %s", model_id)
    return llm
