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

    async def get_active_campaigns_for_game(self, game_name: str, game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all active campaigns matching a given game name or game ID."""
        all_campaigns = await self.gql_client.get_available_drop_campaigns(extra_games=[game_name])
        matched = []
        g_name_lower = game_name.strip().lower()
        g_id_str = str(game_id).strip() if game_id else None

        for c in all_campaigns:
            game = c.get("game") or {}
            c_game_name = (game.get("name") or "").strip().lower()
            c_game_slug = (game.get("slug") or "").strip().lower()
            c_game_id = str(game.get("id") or "").strip()

            is_match = False
            if g_id_str and c_game_id and g_id_str == c_game_id:
                is_match = True
            elif g_name_lower and c_game_name and (
                g_name_lower == c_game_name
                or g_name_lower in c_game_name
                or c_game_name in g_name_lower
                or g_name_lower in c_game_slug
                or g_name_lower.replace(" ", "") in c_game_name.replace(" ", "")
            ):
                is_match = True

            if is_match:
                status = c.get("status")
                # Accept ACTIVE or None if present in campaigns list
                if status in ["ACTIVE", None, ""]:
                    matched.append(c)
        return matched

    async def select_all_active_targets(self, max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """Select all eligible active targets across watchlist games up to max_concurrent."""
        async with AsyncSessionLocal() as db:
            watchlist = await get_watchlist(db)

        if not watchlist:
            logger.info("Watchlist is empty. No targets to mine.")
            return []

        targets: List[Dict[str, Any]] = []
        selected_campaign_ids = set()

        for item in watchlist:
            if not item.is_active or not item.auto_mine:
                continue

            game_name = item.game_name
            game_id = str(item.game_id)

            active_campaigns = await self.get_active_campaigns_for_game(game_name, game_id)

            for campaign in active_campaigns:
                campaign_id = campaign.get("id")
                if not campaign_id or campaign_id in selected_campaign_ids:
                    continue

                details = await self.gql_client.get_campaign_details(campaign_id) or campaign
                time_drops = details.get("timeBasedDrops", []) or []

                target_drop = None
                for drop in time_drops:
                    drop_id = drop.get("id")
                    drop_name = drop.get("name", "Unknown Drop")
                    required_min = drop.get("requiredMinutesWatched", 0) or 0

                    self_node = drop.get("self") or {}
                    current_min = self_node.get("currentMinutesWatched")
                    if current_min is None:
                        current_min = drop.get("currentMinutesWatched", 0) or 0
                    is_claimed = self_node.get("isClaimed")
                    if is_claimed is None:
                        is_claimed = drop.get("isClaimed", False)
                    drop_instance_id = self_node.get("dropInstanceID") or drop_id

                    # Auto-claim completed drops
                    if current_min >= required_min and required_min > 0 and not is_claimed:
                        logger.info(f"Auto-claiming completed drop '{drop_name}' for '{game_name}'...")
                        await self.claim_drop_reward(
                            drop_instance_id,
                            drop_name,
                            campaign_id,
                            campaign.get("name", ""),
                            game_id,
                            game_name,
                        )
                        continue

                    # First pending drop in this campaign
                    if not is_claimed and current_min < required_min and not target_drop:
                        target_drop = {
                            "drop_id": drop_id,
                            "drop_instance_id": drop_instance_id,
                            "drop_name": drop_name,
                            "required_minutes": required_min,
                            "current_minutes": current_min,
                        }

                if target_drop:
                    search_name = campaign.get("game", {}).get("name") or game_name
                    # Check if this campaign has specific allowed channels
                    allow_channels = details.get("allow", {}).get("channels") or campaign.get("allow", {}).get("channels")
                    allowed_logins = None
                    allowed_ids = None
                    if allow_channels and isinstance(allow_channels, list):
                        allowed_logins = {ch["name"].lower() for ch in allow_channels if isinstance(ch, dict) and ch.get("name")}
                        allowed_ids = {str(ch["id"]) for ch in allow_channels if isinstance(ch, dict) and ch.get("id")}

                    streams = await self.gql_client.get_live_streams_for_game(search_name, limit=50)

                    target_channel = None
                    if allowed_logins is not None and len(allowed_logins) > 0:
                        # Filter to only streamers in the campaign's whitelist
                        eligible = [
                            s for s in streams
                            if s["channel_login"].lower() in allowed_logins or str(s.get("channel_id")) in allowed_ids
                        ]
                        if eligible:
                            target_channel = eligible[0]
                        else:
                            logger.info(f"No active whitelisted drop channels currently live for '{campaign.get('name')}' ({game_name}).")
                    elif streams:
                        target_channel = streams[0]

                    if target_channel:
                        selected_campaign_ids.add(campaign_id)
                        targets.append({
                            "game_id": game_id,
                            "game_name": game_name,
                            "campaign_id": campaign_id,
                            "campaign_name": campaign.get("name", ""),
                            "drop_id": target_drop["drop_id"],
                            "drop_instance_id": target_drop["drop_instance_id"],
                            "drop_name": target_drop["drop_name"],
                            "required_minutes": target_drop["required_minutes"],
                            "current_minutes": target_drop["current_minutes"],
                            "progress_percent": round((target_drop["current_minutes"] / max(target_drop["required_minutes"], 1)) * 100, 1),
                            "channel": target_channel,
                        })
                        logger.info(
                            f"Priority #{len(targets)} Target: '{target_drop['drop_name']}' ({game_name}) on @{target_channel['channel_login']} [{target_drop['current_minutes']}/{target_drop['required_minutes']}m]"
                        )
                        if len(targets) >= max_concurrent:
                            return targets

            # If no explicit GQL drop target was matched yet, but the watchlisted game is live on Twitch with DropsEnabled,
            # mine the game's top live stream directly according to priority order.
            if len(targets) < max_concurrent:
                live_streams = await self.gql_client.get_live_streams_for_game(game_name, limit=10)
                if live_streams:
                    target_channel = live_streams[0]
                    camp_key = f"live-drops-{game_id}"
                    if camp_key not in selected_campaign_ids:
                        selected_campaign_ids.add(camp_key)
                        targets.append({
                            "game_id": game_id,
                            "game_name": game_name,
                            "campaign_id": camp_key,
                            "campaign_name": f"{game_name} Drops",
                            "drop_id": f"drop-{game_id}",
                            "drop_instance_id": f"drop-{game_id}",
                            "drop_name": f"{game_name} Drops Event",
                            "required_minutes": 60,
                            "current_minutes": 0,
                            "progress_percent": 0.0,
                            "channel": target_channel,
                        })
                        logger.info(
                            f"Priority #{len(targets)} Target: '{game_name} Drops' on @{target_channel['channel_login']} (Live Priority Stream Mining)"
                        )
                        if len(targets) >= max_concurrent:
                            return targets

        return targets

    async def select_next_target(self) -> Optional[Dict[str, Any]]:
        """Select single highest-priority target to mine (backward compatibility)."""
        targets = await self.select_all_active_targets(max_concurrent=1)
        return targets[0] if targets else None

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
