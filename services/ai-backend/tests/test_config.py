"""Tests for application configuration."""

from __future__ import annotations

import os
import pytest


def test_settings_loads_defaults():
    """Settings should load with defaults when env vars are not set."""
    # Clear cache to force reload
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        USE_LOCAL_MODE=True,
    )
    assert settings.USE_LOCAL_MODE is True
    assert settings.ENABLE_WATCHER is False
    assert settings.PORT == 8000
    assert settings.FRONTEND_URL == "http://localhost:3000"
    assert settings.PINECONE_INDEX_NAME == "celestia-memoria"


def test_validate_production_keys_local_mode():
    """Local mode should not require any production keys."""
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        USE_LOCAL_MODE=True,
    )
    missing = settings.validate_production_keys()
    assert missing == []


def test_validate_production_keys_missing():
    """Production mode should report missing keys."""
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        USE_LOCAL_MODE=False,
    )
    missing = settings.validate_production_keys()
    assert "SUPABASE_URL" in missing
    assert "OPENROUTER_API_KEY" in missing
    assert "PINECONE_API_KEY" in missing
    assert "COHERE_API_KEY" in missing


def test_validate_production_keys_all_set():
    """Production mode with all keys should report no missing."""
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        USE_LOCAL_MODE=False,
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-key",
        SUPABASE_JWT_SECRET="test-secret",
        OPENROUTER_API_KEY="sk-or-test",
        PINECONE_API_KEY="pcsk-test",
        COHERE_API_KEY="cohere-test",
    )
    missing = settings.validate_production_keys()
    assert missing == []
