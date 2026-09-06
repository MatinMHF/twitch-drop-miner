"""Database repository functions for users, accounts, watchlist, drops, and settings."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, delete, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.core.security import hash_password
from app.db.models import User, TwitchAccount, GameWatchlist, ClaimedDrop, SettingEntry


# --- User Repository ---

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def count_users(db: AsyncSession) -> int:
    stmt = select(User)
    result = await db.execute(stmt)
    return len(result.scalars().all())


async def create_user(db: AsyncSession, username: str, plain_password: str) -> User:
    new_user = User(
        id=str(uuid.uuid4()),
        username=username.strip(),
        hashed_password=hash_password(plain_password),
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def seed_admin_user(db: AsyncSession, username: str = "matin", plain_password: str = "$D&@75cQ2DLh&jmLWr#U@") -> User:
    user = await get_user_by_username(db, username.strip())
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            username=username.strip(),
            hashed_password=hash_password(plain_password),
            is_active=True,
        )
        db.add(user)
    else:
        user.hashed_password = hash_password(plain_password)
        user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user


# --- Twitch Account Repository (AES-256-GCM Encrypted at Rest) ---

async def get_active_twitch_account(db: AsyncSession) -> Optional[TwitchAccount]:
    stmt = select(TwitchAccount).where(TwitchAccount.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    return result.scalars().first()


async def save_or_update_twitch_account(
    db: AsyncSession,
    twitch_user_id: str,
    twitch_username: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> TwitchAccount:
    encrypted_access = cipher.encrypt(access_token)
    encrypted_refresh = cipher.encrypt(refresh_token) if refresh_token else None

    stmt = select(TwitchAccount).where(TwitchAccount.twitch_user_id == twitch_user_id)
    result = await db.execute(stmt)
    account = result.scalars().first()

    if account:
        account.twitch_username = twitch_username
        account.encrypted_access_token = encrypted_access
        if encrypted_refresh:
            account.encrypted_refresh_token = encrypted_refresh
        account.token_expires_at = expires_at
        account.is_active = True
        account.updated_at = datetime.now(timezone.utc)
    else:
        account = TwitchAccount(
            id=str(uuid.uuid4()),
            twitch_user_id=twitch_user_id,
            twitch_username=twitch_username,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expires_at=expires_at,
            is_active=True,
        )
        db.add(account)

    await db.commit()
    await db.refresh(account)
    return account


async def delete_twitch_account(db: AsyncSession, account_id: str) -> bool:
    stmt = delete(TwitchAccount).where(TwitchAccount.id == account_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


def get_decrypted_tokens(account: TwitchAccount) -> Dict[str, Optional[str]]:
    """Helper to safely decrypt token strings in memory."""
    access_token = cipher.decrypt(account.encrypted_access_token)
    refresh_token = cipher.decrypt(account.encrypted_refresh_token) if account.encrypted_refresh_token else None
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


# --- Game Watchlist Repository ---

async def get_watchlist(db: AsyncSession) -> List[GameWatchlist]:
    stmt = select(GameWatchlist).order_by(asc(GameWatchlist.priority), asc(GameWatchlist.game_name))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_game_to_watchlist(
    db: AsyncSession,
    game_id: str,
    game_name: str,
    box_art_url: Optional[str] = None,
    priority: int = 0,
    auto_mine: bool = True,
) -> GameWatchlist:
    stmt = select(GameWatchlist).where(GameWatchlist.game_id == game_id)
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if existing:
        existing.game_name = game_name
        existing.box_art_url = box_art_url or existing.box_art_url
        existing.is_active = True
        existing.auto_mine = auto_mine
        await db.commit()
        await db.refresh(existing)
        return existing

    item = GameWatchlist(
        id=str(uuid.uuid4()),
        game_id=game_id,
        game_name=game_name,
        box_art_url=box_art_url,
        priority=priority,
        is_active=True,
        auto_mine=auto_mine,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def remove_game_from_watchlist(db: AsyncSession, game_id: str) -> bool:
    stmt = delete(GameWatchlist).where(GameWatchlist.game_id == game_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def update_game_priority(db: AsyncSession, game_id: str, priority: int, auto_mine: Optional[bool] = None) -> Optional[GameWatchlist]:
    stmt = select(GameWatchlist).where(GameWatchlist.game_id == game_id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    if item:
        item.priority = priority
        if auto_mine is not None:
            item.auto_mine = auto_mine
        await db.commit()
        await db.refresh(item)
    return item


async def restore_watchlist(
    db: AsyncSession,
    items: List[Dict[str, Any]],
    replace_existing: bool = True,
) -> List[GameWatchlist]:
    """Restore watchlist games and their exact priorities from backup."""
    if replace_existing:
        await db.execute(delete(GameWatchlist))
        await db.commit()

    saved_items: List[GameWatchlist] = []
    for idx, it in enumerate(items):
        gid = str(it.get("game_id", "")).strip()
        gname = str(it.get("game_name", "")).strip()
        if not gid or not gname:
            continue

        box_art = it.get("box_art_url")
        prio = it.get("priority", idx)
        auto_mine = bool(it.get("auto_mine", True))
        is_active = bool(it.get("is_active", True))

        stmt = select(GameWatchlist).where(GameWatchlist.game_id == gid)
        res = await db.execute(stmt)
        existing = res.scalars().first()

        if existing:
            existing.game_name = gname
            existing.box_art_url = box_art or existing.box_art_url
            existing.priority = prio
            existing.auto_mine = auto_mine
            existing.is_active = is_active
            saved_items.append(existing)
        else:
            entry = GameWatchlist(
                id=str(uuid.uuid4()),
                game_id=gid,
                game_name=gname,
                box_art_url=box_art,
                priority=prio,
                auto_mine=auto_mine,
                is_active=is_active,
            )
            db.add(entry)
            saved_items.append(entry)

    await db.commit()
    for entry in saved_items:
        await db.refresh(entry)

    # Re-fetch in clean priority order
    stmt_all = select(GameWatchlist).order_by(asc(GameWatchlist.priority))
    res_all = await db.execute(stmt_all)
    return list(res_all.scalars().all())



# --- Claimed Drops Repository ---

async def log_claimed_drop(
    db: AsyncSession,
    drop_id: str,
    drop_name: str,
    campaign_id: str,
    campaign_name: str,
    game_id: str,
    game_name: str,
    channel_name: Optional[str] = None,
    benefit_id: Optional[str] = None,
) -> ClaimedDrop:
    # Check if already logged
    stmt = select(ClaimedDrop).where(ClaimedDrop.drop_id == drop_id)
    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing:
        return existing

    record = ClaimedDrop(
        id=str(uuid.uuid4()),
        drop_id=drop_id,
        drop_name=drop_name,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        game_id=game_id,
        game_name=game_name,
        channel_name=channel_name,
        benefit_id=benefit_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_claimed_drops(db: AsyncSession, limit: int = 50) -> List[ClaimedDrop]:
    stmt = select(ClaimedDrop).order_by(desc(ClaimedDrop.claimed_at)).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# --- Settings Repository ---

async def get_setting(db: AsyncSession, key: str, default: Optional[str] = None) -> Optional[str]:
    stmt = select(SettingEntry).where(SettingEntry.key == key)
    result = await db.execute(stmt)
    entry = result.scalars().first()
    return entry.value if entry else default


async def set_setting(db: AsyncSession, key: str, value: str) -> SettingEntry:
    stmt = select(SettingEntry).where(SettingEntry.key == key)
    result = await db.execute(stmt)
    entry = result.scalars().first()
    if entry:
        entry.value = value
        entry.updated_at = datetime.now(timezone.utc)
    else:
        entry = SettingEntry(key=key, value=value)
        db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
