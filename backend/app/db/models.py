"""SQLAlchemy database models for persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
)
from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Local admin / operator user for web dashboard authentication."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class TwitchAccount(Base):
    """Twitch account OAuth credentials stored with AES-256-GCM encryption."""
    __tablename__ = "twitch_accounts"

    id = Column(String(36), primary_key=True, index=True)
    twitch_user_id = Column(String(64), unique=True, nullable=False, index=True)
    twitch_username = Column(String(128), nullable=False)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class GameWatchlist(Base):
    """Games configured for automated drop campaign monitoring & priority mining."""
    __tablename__ = "game_watchlist"

    id = Column(String(36), primary_key=True, index=True)
    game_id = Column(String(64), unique=True, nullable=False, index=True)
    game_name = Column(String(255), nullable=False)
    box_art_url = Column(String(512), nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_mine = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ClaimedDrop(Base):
    """Log of successfully claimed drop rewards."""
    __tablename__ = "claimed_drops"

    id = Column(String(36), primary_key=True, index=True)
    drop_id = Column(String(128), nullable=False, index=True)
    drop_name = Column(String(255), nullable=False)
    campaign_id = Column(String(128), nullable=False, index=True)
    campaign_name = Column(String(255), nullable=False)
    game_id = Column(String(64), nullable=False)
    game_name = Column(String(255), nullable=False)
    channel_name = Column(String(128), nullable=True)
    claimed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    benefit_id = Column(String(128), nullable=True)


class SettingEntry(Base):
    """Dynamic key-value settings storage."""
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
