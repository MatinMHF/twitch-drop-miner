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


class MinerStatusResponse(BaseModel):
    state: str  # "IDLE", "MINING", "PAUSED", "ERROR", "NO_ACCOUNT"
    active_targets: List[ActiveMiningTarget] = []
    active_game_id: Optional[str] = None
    active_game_name: Optional[str] = None
    active_campaign_id: Optional[str] = None
    active_campaign_name: Optional[str] = None
    active_channel: Optional[ChannelStreamInfo] = None
    current_drop_id: Optional[str] = None
    current_drop_name: Optional[str] = None
    current_drop_progress_percent: float = 0.0
    current_drop_minutes_watched: int = 0
    current_drop_required_minutes: int = 0
    total_drops_claimed_session: int = 0
    last_heartbeat_at: Optional[datetime] = None
    next_poll_at: Optional[datetime] = None
    error_message: Optional[str] = None
    is_paused: bool = False


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
