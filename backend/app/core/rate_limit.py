"""Rate limiting configuration for authentication and sensitive API endpoints."""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_real_client_ip(request: Request) -> str:
    """Extract true client IP taking reverse proxy headers (X-Forwarded-For) into account."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in comma-separated list is the original client
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request) or "127.0.0.1"


limiter = Limiter(key_func=get_real_client_ip, default_limits=["120/minute"])
