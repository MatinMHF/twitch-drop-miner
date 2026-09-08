"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_auth_status_before_setup():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_setup_completed" in data


@pytest.mark.asyncio
async def test_watchlist_response_model():
    from app.schemas.games import WatchlistItemResponse
    from datetime import datetime, timezone

    item = WatchlistItemResponse(
        id="test-id",
        game_id="12345",
        game_name="Rainbow Six Siege",
        box_art_url="http://test.com/art.jpg",
        priority=0,
        is_active=True,
        auto_mine=True,
        created_at=datetime.now(timezone.utc),
        active_campaigns_count=0,
        active_drops_count=0,
        is_completed=True,
        is_currently_mining=False,
    )
    assert item.active_drops_count == 0
    assert item.active_campaigns_count == 0
    assert item.is_completed is True
