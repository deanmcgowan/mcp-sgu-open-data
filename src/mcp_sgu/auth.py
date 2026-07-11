"""****** authentication middleware for Starlette."""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from mcp_sgu.config import get_settings
from mcp_sgu.logging_config import get_logger

logger = get_logger(__name__)

_PROTECTED_PATHS = {"/mcp", "/api/exports"}


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Validate ``Authorization: ****** for protected paths.

    Uses constant-time comparison to prevent timing attacks.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        path = request.url.path

        # Only protect MCP endpoint
        if not any(path == p or path.startswith(p + "/") for p in _PROTECTED_PATHS):
            return await call_next(request)  # type: ignore[call-arg]

        settings = get_settings()
        expected_token = settings.mcp_bearer_token

        if not expected_token:
            logger.warning("MCP_BEARER_TOKEN is not configured; rejecting all requests")
            return _unauthorized("MCP_BEARER_TOKEN is not configured on the server")

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return _unauthorized("Missing or malformed Authorization header")

        provided_token = auth_header[len("bearer "):]

        # Constant-time comparison
        if not hmac.compare_digest(provided_token.encode(), expected_token.encode()):
            logger.warning("Invalid bearer token presented", extra={"path": path})
            return _unauthorized("Invalid bearer token")

        return await call_next(request)  # type: ignore[call-arg]


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        {"error": "unauthorized", "detail": detail},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )
