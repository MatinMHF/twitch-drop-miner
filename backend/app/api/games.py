import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.repositories import (
    add_game_to_watchlist,
    get_active_twitch_account,
    get_decrypted_tokens,
    get_watchlist,
    remove_game_from_watchlist,
    restore_watchlist,
    update_game_priority,
)
from app.engine.gql_client import TwitchGQLClient
from app.engine.miner_worker import miner_service
from app.schemas.games import (
    AddWatchlistRequest,
    GameSearchResult,
    ReorderWatchlistRequest,
    RestoreWatchlistRequest,
    UpdateWatchlistRequest,
    WatchlistBackupData,
    WatchlistBackupItem,
    WatchlistItemResponse,
)

router = APIRouter(prefix="/api/games", tags=["Games & Watchlist"])


@router.get("/search", response_model=List[GameSearchResult])
async def search_twitch_games(
    query: str = Query(..., min_length=1),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Search Twitch games directly via Twitch GraphQL API."""
    account = await get_active_twitch_account(db)
    token = None
    if account:
        token = get_decrypted_tokens(account)["access_token"]

    gql = TwitchGQLClient(oauth_token=token)
    try:
        games = await gql.search_games(query, limit=15)
        # Check active campaigns to tag active drops
        all_campaigns = await gql.get_available_drop_campaigns()
        campaign_game_ids = {
            c.get("game", {}).get("id")
            for c in all_campaigns
            if c.get("status") == "ACTIVE" and c.get("game")
        }

        results = []
        for g in games:
            has_drops = g["id"] in campaign_game_ids
            results.append(
                GameSearchResult(
                    id=g["id"],
                    name=g["name"],
                    box_art_url=g["box_art_url"],
                    has_active_drops=has_drops,
                    active_campaign_count=1 if has_drops else 0,
                )
            )
        return results
    finally:
        await gql.close()


@router.get("/watchlist", response_model=List[WatchlistItemResponse])
async def list_watchlist(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all games in the user's priority watchlist."""
    items = await get_watchlist(db)
    status = miner_service.get_status()
    current_game_id = status.get("active_game_id")

    res = []
    for item in items:
        res.append(
            WatchlistItemResponse(
                id=item.id,
                game_id=item.game_id,
                game_name=item.game_name,
                box_art_url=item.box_art_url,
                priority=item.priority,
                is_active=item.is_active,
                auto_mine=item.auto_mine,
                created_at=item.created_at,
                active_campaigns_count=0,
                is_currently_mining=(item.game_id == current_game_id),
            )
        )
    return res


@router.post("/watchlist", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    body: AddWatchlistRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a game to the watchlist."""
    item = await add_game_to_watchlist(
        db=db,
        game_id=body.game_id,
        game_name=body.game_name,
        box_art_url=body.box_art_url,
        priority=body.priority,
        auto_mine=body.auto_mine,
    )
    # Trigger miner in background to check if new campaign should be picked up immediately
    asyncio.create_task(miner_service.check_and_mine())

    return WatchlistItemResponse(
        id=item.id,
        game_id=item.game_id,
        game_name=item.game_name,
        box_art_url=item.box_art_url,
        priority=item.priority,
        is_active=item.is_active,
        auto_mine=item.auto_mine,
        created_at=item.created_at,
        is_currently_mining=False,
    )


@router.put("/watchlist/{game_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    game_id: str,
    body: UpdateWatchlistRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update priority or auto_mine toggle for a game."""
    item = await update_game_priority(db, game_id, body.priority, body.auto_mine)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found in watchlist",
        )
    asyncio.create_task(miner_service.check_and_mine())
    return WatchlistItemResponse(
        id=item.id,
        game_id=item.game_id,
        game_name=item.game_name,
        box_art_url=item.box_art_url,
        priority=item.priority,
        is_active=item.is_active,
        auto_mine=item.auto_mine,
        created_at=item.created_at,
    )


@router.delete("/watchlist/{game_id}")
async def delete_from_watchlist(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Remove a game from the watchlist."""
    success = await remove_game_from_watchlist(db, game_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found in watchlist",
        )
    # Check if we need to switch miner target
    if miner_service.active_target and miner_service.active_target.get("game_id") == game_id:
        asyncio.create_task(miner_service.check_and_mine())
    return {"message": "Game removed from watchlist"}


@router.post("/watchlist/reorder")
async def reorder_watchlist(
    body: ReorderWatchlistRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Batch update game priorities according to ordered list of game IDs."""
    for idx, gid in enumerate(body.game_ids):
        await update_game_priority(db, gid, priority=idx)
    asyncio.create_task(miner_service.check_and_mine())
    return {"message": "Watchlist reordered successfully"}


@router.get("/watchlist/backup", response_model=WatchlistBackupData)
async def backup_watchlist(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Export the current watchlist games and their exact priority order as a backup payload."""
    from datetime import timezone
    items = await get_watchlist(db)
    backup_items = [
        WatchlistBackupItem(
            game_id=item.game_id,
            game_name=item.game_name,
            box_art_url=item.box_art_url,
            priority=item.priority,
            auto_mine=item.auto_mine,
            is_active=item.is_active,
        )
        for item in items
    ]
    return WatchlistBackupData(
        app="Twitch Drop Miner",
        version="1.0.0",
        exported_at=datetime.now(timezone.utc),
        total_games=len(backup_items),
        games=backup_items,
    )


@router.post("/watchlist/restore", response_model=List[WatchlistItemResponse])
async def restore_watchlist_endpoint(
    body: RestoreWatchlistRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Restore watchlist games and their exact priority order from a backup file."""
    if not body.games:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup payload contains no games to restore.",
        )

    dict_items = [g.model_dump() for g in body.games]
    restored = await restore_watchlist(db, dict_items, replace_existing=body.replace_existing)
    asyncio.create_task(miner_service.check_and_mine())

    status_data = miner_service.get_status()
    current_game_id = status_data.get("active_game_id")

    return [
        WatchlistItemResponse(
            id=item.id,
            game_id=item.game_id,
            game_name=item.game_name,
            box_art_url=item.box_art_url,
            priority=item.priority,
            is_active=item.is_active,
            auto_mine=item.auto_mine,
            created_at=item.created_at,
            is_currently_mining=(item.game_id == current_game_id),
        )
        for item in restored
    ]


