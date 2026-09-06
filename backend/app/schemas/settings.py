"""Pydantic schemas for application settings and configuration."""

from __future__ import annotations

from typing import Optional, Dict
from pydantic import BaseModel, Field


class AppSettingsSchema(BaseModel):
    poll_interval_minutes: int = Field(30, ge=5, le=1440)
    watch_heartbeat_seconds: int = Field(60, ge=30, le=120)
    auto_claim_drops: bool = True
    auto_failover_streamers: bool = True
    timezone: str = "UTC"
    custom_spade_url: Optional[str] = None
    custom_query_hashes: Optional[Dict[str, str]] = None


class UpdateSettingsRequest(BaseModel):
    poll_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    watch_heartbeat_seconds: Optional[int] = Field(None, ge=30, le=120)
    auto_claim_drops: Optional[bool] = None
    auto_failover_streamers: Optional[bool] = None
    timezone: Optional[str] = None
    custom_spade_url: Optional[str] = None
    custom_query_hashes: Optional[Dict[str, str]] = None
