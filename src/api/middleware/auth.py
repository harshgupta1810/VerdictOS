"""API Key Authentication Middleware.

Validates API key and enforces authentication
on protected API routes.
"""

import os
from fastapi import Request, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# For now, expect a comma-separated list of valid keys in the environment
VALID_API_KEYS = set(os.getenv("VERDICTOS_API_KEYS", "dev-key-123").split(","))

# Endpoints that don't require authentication (e.g., docs, health)
EXEMPT_PATHS = {"/docs", "/openapi.json", "/health", "/redoc"}

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce API key authentication on protected routes."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.url.path in EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)
            
        api_key = request.headers.get(API_KEY_NAME)
        if not api_key or api_key not in VALID_API_KEYS:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error_code": "UNAUTHORIZED", "message": "Invalid or missing API Key"},
            )
        
        response = await call_next(request)
        return response
