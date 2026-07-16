"""Bearer token authentication for MCP HTTP transport."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Validate Bearer token for HTTP MCP requests."""
    
    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token
    
    async def dispatch(self, request: Request, call_next):
        # Allow health check without auth
        if request.url.path == "/health":
            return await call_next(request)
        
        # Check Authorization header
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
            )
        
        provided = auth[7:]  # Remove "Bearer "
        if provided != self.token:
            return JSONResponse(
                {"error": "Invalid token"},
                status_code=403,
            )
        
        return await call_next(request)