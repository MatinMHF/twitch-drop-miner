"""Twitch Drop priority evaluation, campaign discovery, and auto-claiming logic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.database import AsyncSessionLocal
from app.db.repositories import (
    get_watchlist,
    log_claimed_drop,
)
from app.engine.gql_client import TwitchGQLClient


class DropManager:
    """Evaluates active campaigns against watchlist and orchestrates drop claims."""

    def __init__(self, oauth_token: str, twitch_user_id: str):
        self.oauth_token = oauth_token
        self.twitch_user_id = twitch_user_id
        self.gql_client = TwitchGQLClient(oauth_token=oauth_token)

    async def close(self) -> None:
        await self.gql_client.close()

    async def get_active_campaigns_for_game(self, game_name: str) -> List[Dict[str, Any]]:
        """Fetch all active campaigns for a given game name."""
        all_campaigns = await self.gql_client.get_available_drop_campaigns()
        matched = []
        for c in all_campaigns:
            game = c.get("game") or {}
            c_game_name = game.get("name", "")
            if c_game_name.lower() == game_name.lower():
                status = c.get("status")
                if status == "ACTIVE":
                    matched.append(c)
        return matched

    async def select_next_target(self) -> Optional[Dict[str, Any]]:
        """Select highest-priority game and active drop to mine."""
        async with AsyncSessionLocal() as db:
            watchlist = await get_watchlist(db)

        if not watchlist:
            logger.info("Watchlist is empty. No targets to mine.")
            return None

        # Fetch current user's drop dashboard / inventory
        inventory = await self.gql_client.get_inventory_drops()
        in_progress_campaigns = inventory.get("dropCampaignsInProgress", []) or []

        # Map campaigns by ID
        campaign_progress_map: Dict[str, Dict[str, Any]] = {}
        for c in in_progress_campaigns:
            if c and "id" in c:
                campaign_progress_map[c["id"]] = c

        # Iterate through prioritized watchlist
        for item in watchlist:
            if not item.is_active or not item.auto_mine:
                continue

            game_name = item.game_name
            # Check available campaigns for this game
            active_campaigns = await self.get_active_campaigns_for_game(game_name)

            for campaign in active_campaigns:
                campaign_id = campaign.get("id")
                # Get detailed campaign structure
                details = await self.gql_client.get_campaign_details(campaign_id)
                if not details:
                    continue

                time_drops = details.get("timeBasedDrops", []) or []
                for drop in time_drops:
                    drop_id = drop.get("id")
                    name = drop.get("name", "Unknown Drop")
                    required_min = drop.get("requiredMinutesWatched", 0)
                    current_min = drop.get("currentMinutesWatched", 0)
                    is_claimed = drop.get("isClaimed", False)

                    # Check if already completed and needs claiming
                    if current_min >= required_min and not is_claimed:
                        # Attempt immediate claim
                        await self.claim_drop_reward(drop_id, name, campaign_id, campaign.get("name", ""), item.game_id, game_name)
                        continue

                    # If drop is still pending and eligible to watch
                    if not is_claimed and current_min < required_min:
                        # Find an active channel streaming this game with drops enabled
                        streams = await self.gql_client.get_live_streams_for_game(game_name, limit=10)
                        if streams:
                            target_channel = streams[0]  # Pick top viewer channel
                            return {
                                "game_id": item.game_id,
                                "game_name": game_name,
                                "campaign_id": campaign_id,
                                "campaign_name": campaign.get("name", ""),
                                "drop_id": drop_id,
                                "drop_name": name,
                                "required_minutes": required_min,
                                "current_minutes": current_min,
                                "channel": target_channel,
                            }
                        else:
                            logger.info(f"No live streams found for game '{game_name}' with drops enabled.")

        return None

    async def claim_drop_reward(
        self,
        drop_id: str,
        drop_name: str,
        campaign_id: str,
        campaign_name: str,
        game_id: str,
        game_name: str,
        channel_name: Optional[str] = None,
    ) -> bool:
        """Claim drop mutation and save record to database."""
        success = await self.gql_client.claim_drop(drop_id)
        if success:
            async with AsyncSessionLocal() as db:
                await log_claimed_drop(
                    db=db,
                    drop_id=drop_id,
                    drop_name=drop_name,
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    game_id=game_id,
                    game_name=game_name,
                    channel_name=channel_name,
                )
            logger.info(f"🎉 Successfully claimed and recorded Drop: '{drop_name}' ({game_name})")
            return True
        return False
