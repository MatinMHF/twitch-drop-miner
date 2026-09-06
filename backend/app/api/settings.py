"""Settings and Configuration API routes."""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user_id
from app.core.twitch_constants import PERSISTED_QUERY_HASHES, TWITCH_SPADE_URL
from app.db.database import get_db
from app.db.repositories import get_setting, set_setting
from app.schemas.settings import AppSettingsSchema, UpdateSettingsRequest

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=AppSettingsSchema)
async def get_app_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve current system configuration and Twitch constants."""
    poll_int = await get_setting(db, "POLL_INTERVAL_MINUTES", str(settings.POLL_INTERVAL_MINUTES))
    heartbeat_sec = await get_setting(db, "WATCH_HEARTBEAT_SECONDS", str(settings.WATCH_HEARTBEAT_SECONDS))
    auto_claim = await get_setting(db, "AUTO_CLAIM_DROPS", str(settings.AUTO_CLAIM_DROPS))
    auto_failover = await get_setting(db, "AUTO_FAILOVER_STREAMERS", str(settings.AUTO_FAILOVER_STREAMERS))
    tz = await get_setting(db, "TIMEZONE", settings.TIMEZONE)
    spade_url = await get_setting(db, "TWITCH_SPADE_URL", TWITCH_SPADE_URL)

    return AppSettingsSchema(
        poll_interval_minutes=int(poll_int or 30),
        watch_heartbeat_seconds=int(heartbeat_sec or 60),
        auto_claim_drops=str(auto_claim).lower() in ("true", "1"),
        auto_failover_streamers=str(auto_failover).lower() in ("true", "1"),
        timezone=tz or "UTC",
        custom_spade_url=spade_url,
        custom_query_hashes=dict(PERSISTED_QUERY_HASHES),
    )


@router.put("", response_model=AppSettingsSchema)
async def update_app_settings(
    body: UpdateSettingsRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update system settings and persisted Twitch query hashes."""
    if body.poll_interval_minutes is not None:
        await set_setting(db, "POLL_INTERVAL_MINUTES", str(body.poll_interval_minutes))
        settings.POLL_INTERVAL_MINUTES = body.poll_interval_minutes

    if body.watch_heartbeat_seconds is not None:
        await set_setting(db, "WATCH_HEARTBEAT_SECONDS", str(body.watch_heartbeat_seconds))
        settings.WATCH_HEARTBEAT_SECONDS = body.watch_heartbeat_seconds

    if body.auto_claim_drops is not None:
        await set_setting(db, "AUTO_CLAIM_DROPS", str(body.auto_claim_drops))
        settings.AUTO_CLAIM_DROPS = body.auto_claim_drops

    if body.auto_failover_streamers is not None:
        await set_setting(db, "AUTO_FAILOVER_STREAMERS", str(body.auto_failover_streamers))
        settings.AUTO_FAILOVER_STREAMERS = body.auto_failover_streamers

    if body.timezone is not None:
        await set_setting(db, "TIMEZONE", body.timezone)
        settings.TIMEZONE = body.timezone

    if body.custom_spade_url:
        await set_setting(db, "TWITCH_SPADE_URL", body.custom_spade_url)

    if body.custom_query_hashes:
        for k, v in body.custom_query_hashes.items():
            if k in PERSISTED_QUERY_HASHES and v:
                PERSISTED_QUERY_HASHES[k] = v
        await set_setting(db, "TWITCH_QUERY_HASHES", json.dumps(PERSISTED_QUERY_HASHES))

    return await get_app_settings(user_id=user_id, db=db)
