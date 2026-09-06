"""Pydantic schemas for authentication and Twitch device flow."""

from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SetupAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    csrf_token: str


class UserProfileResponse(BaseModel):
    id: str
    username: str
    is_active: bool
    is_setup_completed: bool


class DeviceCodeInitResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class DeviceCodeStatusResponse(BaseModel):
    status: str  # "pending", "success", "expired", "failed"
    message: str
    twitch_username: Optional[str] = None


class TwitchAccountResponse(BaseModel):
    connected: bool
    twitch_user_id: Optional[str] = None
    twitch_username: Optional[str] = None
    connected_at: Optional[datetime] = None
