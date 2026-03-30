"""Tests for authentication middleware."""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.middleware.auth import SupabaseAuthMiddleware


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with auth middleware for testing."""
    app = FastAPI()
    app.add_middleware(SupabaseAuthMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/protected")
    async def protected(request: Request):
        return {
            "user_id": request.state.user_id,
            "user_role": request.state.user_role,
        }

    return app


class TestAuthMiddlewareLocalMode:
    """Tests for local development mode (auth bypassed)."""

    def setup_method(self):
        os.environ["USE_LOCAL_MODE"] = "true"
        # Clear settings cache
        from app.config import get_settings
        get_settings.cache_clear()

    def teardown_method(self):
        from app.config import get_settings
        get_settings.cache_clear()

    def test_health_no_auth_needed(self):
        app = _create_test_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_route_bypassed_in_local_mode(self):
        app = _create_test_app()
        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "dev-local-user"
        assert data["user_role"] == "admin"


class TestAuthMiddlewareProductionMode:
    """Tests for production mode (JWT validation)."""

    def setup_method(self):
        os.environ["USE_LOCAL_MODE"] = "false"
        os.environ["SUPABASE_JWT_SECRET"] = "test-secret-key-for-jwt-validation"
        from app.config import get_settings
        get_settings.cache_clear()

    def teardown_method(self):
        os.environ.pop("SUPABASE_JWT_SECRET", None)
        os.environ["USE_LOCAL_MODE"] = "true"
        from app.config import get_settings
        get_settings.cache_clear()

    def test_missing_auth_header(self):
        app = _create_test_app()
        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    def test_invalid_token(self):
        app = _create_test_app()
        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_skip_paths(self):
        app = _create_test_app()
        client = TestClient(app)
        # Health should be accessible without auth
        response = client.get("/health")
        assert response.status_code == 200

    def test_options_request_passes(self):
        app = _create_test_app()
        client = TestClient(app)
        response = client.options("/protected")
        # OPTIONS should pass through (CORS preflight)
        assert response.status_code in (200, 405)
