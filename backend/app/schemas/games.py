"""Pydantic schemas for game search and watchlist management."""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class GameSearchResult(BaseModel):
    id: str
    name: str
    box_art_url: Optional[str] = None
    has_active_drops: bool = False
    active_campaign_count: int = 0


class AddWatchlistRequest(BaseModel):
    game_id: str
    game_name: str
    box_art_url: Optional[str] = None
    priority: int = 0
    auto_mine: bool = True


class UpdateWatchlistRequest(BaseModel):
    priority: int
    auto_mine: Optional[bool] = None


class WatchlistItemResponse(BaseModel):
    id: str
    game_id: str
    game_name: str
    box_art_url: Optional[str] = None
    priority: int
    is_active: bool
    auto_mine: bool
    created_at: datetime
    active_campaigns_count: int = 0
    is_currently_mining: bool = False


class ReorderWatchlistRequest(BaseModel):
    game_ids: List[str]
