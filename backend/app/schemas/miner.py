"""Pydantic schemas for miner status, drops, campaigns, and live telemetry."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class DropBenefitSchema(BaseModel):
    id: str
    name: str
    image_asset_url: Optional[str] = None


class TimeBasedDropSchema(BaseModel):
    id: str
    name: str
    required_minutes_watched: int
    current_minutes_watched: int = 0
    is_claimed: bool = False
    benefit_edges: List[Dict[str, Any]] = []
    precondition_drops: List[str] = []


class CampaignSchema(BaseModel):
    id: str
    name: str
    game_id: str
    game_name: str
    game_box_art_url: Optional[str] = None
    status: str  # "ACTIVE", "UPCOMING", "EXPIRED"
    start_at: datetime
    end_at: datetime
    time_based_drops: List[TimeBasedDropSchema] = []
    allow_channels: List[Dict[str, Any]] = []


class ChannelStreamInfo(BaseModel):
    channel_id: str
    channel_login: str
    channel_display_name: str
    title: str
    viewers_count: int
    game_name: str
    is_live: bool
    stream_id: Optional[str] = None


class ActiveMiningTarget(BaseModel):
    game_id: str
    game_name: str
    campaign_id: str
    campaign_name: str
    drop_id: str
    drop_instance_id: Optional[str] = None
    drop_name: str
    required_minutes: int
    current_minutes: int
    progress_percent: float = 0.0
    channel: Optional[ChannelStreamInfo] = None


class MinerAccountStatus(BaseModel):
    account_id: str
    twitch_user_id: str
    twitch_username: str
    is_running: bool
    is_paused: bool
    error_message: Optional[str] = None
    status_text: str = "Idle"
    active_channel: Optional[Dict[str, Any]] = None
    active_drop: Optional[Dict[str, Any]] = None
    next_poll_at: Optional[str] = None


class MinerStatusResponse(BaseModel):
    state: str = "IDLE"  # "IDLE", "MINING", "PAUSED", "ERROR", "NO_ACCOUNT"
    is_running: bool = False
    is_paused: bool = False
    status_text: str = "Idle"
    error_message: Optional[str] = None
    active_channel: Optional[Dict[str, Any]] = None
    active_drop: Optional[Dict[str, Any]] = None
    next_poll_at: Optional[str] = None
    accounts_count: int = 0
    accounts: List[MinerAccountStatus] = []


class ClaimedDropResponse(BaseModel):
    id: str
    drop_id: str
    drop_name: str
    campaign_id: str
    campaign_name: str
    game_id: str
    game_name: str
    channel_name: Optional[str] = None
    claimed_at: datetime
    benefit_id: Optional[str] = None


class MinerControlRequest(BaseModel):
    action: str  # "start", "stop", "pause", "resume", "force_check"
