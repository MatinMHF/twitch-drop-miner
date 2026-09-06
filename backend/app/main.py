"""Main FastAPI application entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api.auth import router as auth_router
from app.api.games import router as games_router
from app.api.campaigns import router as campaigns_router
from app.api.miner import router as miner_router
from app.api.settings import router as settings_router
from app.api.websocket import router as ws_router
from app.api.health import router as health_router

from app.core.config import settings
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.db.database import init_db, AsyncSessionLocal
from app.db.repositories import seed_admin_user
from app.engine.miner_worker import miner_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: sets up DB tables and background worker."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    # Initialize SQLite tables
    await init_db()
    # Ensure default admin user is seeded
    async with AsyncSessionLocal() as session:
        await seed_admin_user(session, username="matin", plain_password="$D&@75cQ2DLh&jmLWr#U@")
    # Start background miner worker
    await miner_service.start()
    yield
    # Shutdown background worker gracefully
    logger.info("Gracefully shutting down Twitch Miner background services...")
    await miner_service.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Clean-room self-hosted automatic Twitch Drop mining web service.",
    lifespan=lifespan,
)

# Attach rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Enforce HTTPS and attach standard security headers."""
    if settings.REQUIRE_HTTPS and request.headers.get("x-forwarded-proto", "").lower() == "http":
        url = request.url.replace(scheme="https")
        return Response(status_code=301, headers={"Location": str(url)})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.REQUIRE_HTTPS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# Register Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(campaigns_router)
app.include_router(miner_router)
app.include_router(settings_router)
app.include_router(ws_router)

# Mount static frontend build if present
static_dist = Path(__file__).resolve().parent.parent / "static"
if static_dist.exists() and (static_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(static_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
