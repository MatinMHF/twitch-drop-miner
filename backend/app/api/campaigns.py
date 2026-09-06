"""Twitch Drop Campaigns and Claim History API routes."""

from __future__ import annotations

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories import (
    get_active_twitch_account,
    get_claimed_drops,
    get_decrypted_tokens,
    get_watchlist,
)
from app.engine.gql_client import TwitchGQLClient
from app.schemas.miner import ClaimedDropResponse

router = APIRouter(prefix="/api/campaigns", tags=["Drop Campaigns"])


@router.get("/active")
async def list_active_campaigns(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all currently active drop campaigns on Twitch."""
    account = await get_active_twitch_account(db)
    watchlist = await get_watchlist(db)
    extra_games = [item.game_name for item in watchlist if item.is_active]

    token = None
    if account:
        token = get_decrypted_tokens(account)["access_token"]

    gql = TwitchGQLClient(oauth_token=token)
    try:
        raw_campaigns = await gql.get_available_drop_campaigns(extra_games=extra_games)
        results = []
        for c in raw_campaigns:
            game = c.get("game") or {}
            gid = str(game.get("id") or "")
            box_art = game.get("boxArtURL")
            if box_art:
                box_art_url = box_art.replace("{width}", "285").replace("{height}", "380")
            elif gid:
                box_art_url = f"https://static-cdn.jtvnw.net/ttv-boxart/{gid}-285x380.jpg"
            else:
                box_art_url = None

            results.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "status": c.get("status") or "ACTIVE",
                "start_at": c.get("startAt"),
                "end_at": c.get("endAt"),
                "game": {
                    "id": gid,
                    "name": game.get("name") or "Twitch Game",
                    "box_art_url": box_art_url,
                },
            })
        return results
    finally:
        await gql.close()


@router.get("/details/{campaign_id}")
async def get_campaign_details(
    campaign_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch detailed drops and rules for a specific campaign."""
    account = await get_active_twitch_account(db)
    token = None
    if account:
        token = get_decrypted_tokens(account)["access_token"]

    gql = TwitchGQLClient(oauth_token=token)
    try:
        details = await gql.get_campaign_details(campaign_id)
        if not details:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return details
    finally:
        await gql.close()


@router.get("/history", response_model=List[ClaimedDropResponse])
async def list_claimed_drops(
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List drops claimed by the miner."""
    records = await get_claimed_drops(db, limit=limit)
    return [
        ClaimedDropResponse(
            id=r.id,
            drop_id=r.drop_id,
            drop_name=r.drop_name,
            campaign_id=r.campaign_id,
            campaign_name=r.campaign_name,
            game_id=r.game_id,
            game_name=r.game_name,
            channel_name=r.channel_name,
            claimed_at=r.claimed_at,
            benefit_id=r.benefit_id,
        )
        for r in records
    ]


@router.get("/channels")
async def list_eligible_channels(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List live channels/streamers streaming watchlisted games with drops."""
    watchlist = await get_watchlist(db)
    active_games = [item.game_name for item in watchlist if item.is_active]
    if not active_games:
        return []

    account = await get_active_twitch_account(db)
    token = None
    if account:
        token = get_decrypted_tokens(account)["access_token"]

    gql = TwitchGQLClient(oauth_token=token)
    all_streams = []
    seen_logins = set()
    try:
        for game_name in active_games[:8]:
            streams = await gql.get_live_streams_for_game(game_name, limit=6)
            for s in streams:
                login_val = s.get("channel_login")
                if login_val and login_val not in seen_logins:
                    seen_logins.add(login_val)
                    all_streams.append(s)
        return all_streams
    finally:
        await gql.close()

