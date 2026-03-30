"""Authentication middleware: JWT validation via Supabase or dev bypass."""

from __future__ import annotations

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)

SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})

DEV_USER_ID = "dev-local-user"
DEV_USER_ROLE = "admin"


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    """Validate Supabase JWT tokens on incoming requests.

    In local mode, bypasses auth and injects a dev user into request state.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        # Skip auth for specific paths
        path = request.url.path
        if path in SKIP_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Local mode: bypass auth with dev user
        if settings.USE_LOCAL_MODE:
            request.state.user_id = DEV_USER_ID
            request.state.user_role = DEV_USER_ROLE
            return await call_next(request)

        # Production mode: validate JWT
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]  # Strip "Bearer "

        try:
            from jose import jwt, JWTError, ExpiredSignatureError

            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

            request.state.user_id = payload.get("sub", "")
            request.state.user_role = (
                payload.get("app_metadata", {}).get("role", "controller")
            )

            if not request.state.user_id:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token: missing subject"},
                )

        except ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"},
            )
        except JWTError as e:
            logger.warning("JWT validation failed: %s", e)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )

        return await call_next(request)
