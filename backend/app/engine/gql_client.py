"""Twitch GraphQL API client for campaigns, game search, streams, and drop claims."""

from __future__ import annotations

import json
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.twitch_constants import (
    TWITCH_GQL_URL,
    TWITCH_WEB_CLIENT_ID,
    build_gql_persisted_query,
)


class TwitchGQLClient:
    """High-performance async Twitch GraphQL Client."""

    def __init__(self, oauth_token: Optional[str] = None, client_id: Optional[str] = None):
        self.client_id = client_id or TWITCH_WEB_CLIENT_ID
        self.oauth_token = oauth_token
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            headers = {
                "Client-Id": self.client_id,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US",
                "Content-Type": "application/json",
            }
            if self.oauth_token:
                # Twitch GQL accepts Bearer or OAuth prefix
                token_val = self.oauth_token if not self.oauth_token.startswith("OAuth ") else self.oauth_token[6:]
                headers["Authorization"] = f"OAuth {token_val}"

            self._http_client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(20.0, connect=10.0),
                http2=True,
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def execute_query(self, operation_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single Twitch GQL persisted query."""
        client = await self._get_client()
        payload = build_gql_persisted_query(operation_name, variables)

        try:
            response = await client.post(TWITCH_GQL_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            if "errors" in data and not data.get("data"):
                error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                logger.error(f"Twitch GQL error in {operation_name}: {error_msg}")
                raise RuntimeError(f"GQL Error: {error_msg}")
            return data.get("data", {})
        except httpx.HTTPStatusError as exc:
            logger.error(f"Twitch GQL HTTP status error {exc.response.status_code} for {operation_name}")
            raise
        except Exception as exc:
            logger.error(f"Twitch GQL request failed for {operation_name}: {str(exc)}")
            raise

    # --- Query Implementations ---

    async def search_games(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search Twitch games directory by querying Twitch API and filtering real games only."""
        items: List[Dict[str, Any]] = []
        seen_ids = set()

        q_lower = query.strip().lower()
        if not q_lower:
            return []

        # 1. Search against active and upcoming drop campaigns directly from Twitch API
        try:
            campaigns = await self.get_available_drop_campaigns()
            for c in campaigns:
                g = c.get("game") or {}
                gid = g.get("id")
                gname = g.get("name", "")
                if gid and gname and q_lower in gname.lower() and str(gid) not in seen_ids:
                    seen_ids.add(str(gid))
                    items.append({
                        "id": str(gid),
                        "name": gname,
                        "box_art_url": f"https://static-cdn.jtvnw.net/ttv-boxart/{gid}-285x380.jpg",
                    })
        except Exception as exc:
            logger.debug(f"Campaign search filter error: {exc}")

        # 2. Query DirectoryGameRedirect for exact or slug game lookup on Twitch API
        try:
            data = await self.execute_query("DirectoryGameRedirect", {"name": query.strip()})
            game_node = data.get("game")
            if game_node and game_node.get("id"):
                gid = str(game_node.get("id"))
                slug = game_node.get("slug") or query.strip()
                # Derive display name from slug or displayName if available
                display_name = game_node.get("displayName") or slug.replace("-", " ").title()
                if gid not in seen_ids:
                    seen_ids.add(gid)
                    items.insert(0, {
                        "id": gid,
                        "name": display_name,
                        "box_art_url": f"https://static-cdn.jtvnw.net/ttv-boxart/{gid}-285x380.jpg",
                    })
        except Exception as exc:
            logger.debug(f"DirectoryGameRedirect query error: {exc}")

        # Return only verified Twitch games (empty list if no real Twitch game found)
        return items[:limit]

    async def get_available_drop_campaigns(self) -> List[Dict[str, Any]]:
        """Fetch all active and upcoming Drop campaigns."""
        variables = {"fetchRewardCampaigns": False}
        try:
            data = await self.execute_query("ViewerDropsDashboard", variables)
            user_data = data.get("currentUser", {}) or data.get("user", {}) or {}
            campaigns = (
                user_data.get("dropCampaigns", [])
                or user_data.get("dropCampaignsInProgress", [])
                or []
            )
            return [c for c in campaigns if c]
        except Exception as exc:
            logger.warning(f"Failed to fetch available drop campaigns: {exc}")
            return []

    async def get_campaign_details(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed drop rules and progress for a specific campaign."""
        variables = {
            "dropID": campaign_id,
            "channelLogin": "",
        }
        try:
            data = await self.execute_query("DropCampaignDetails", variables)
            user_node = data.get("user", {}) or data.get("currentUser", {}) or {}
            return user_node.get("dropCampaign")
        except Exception as exc:
            logger.warning(f"Failed to fetch campaign details for {campaign_id}: {exc}")
            return None

    async def get_inventory_drops(self) -> Dict[str, Any]:
        """Fetch current user's drop inventory progress and claimable drops."""
        variables = {"fetchRewardCampaigns": False}
        try:
            data = await self.execute_query("Inventory", variables)
            if not data:
                data = await self.execute_query("ViewerDropsDashboard", variables)
            return data.get("currentUser", {}) or data.get("user", {}) or {}
        except Exception as exc:
            logger.warning(f"Failed to fetch user inventory drops: {exc}")
            return {}

    async def get_live_streams_for_game(self, game_name: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch top live channels broadcasting a specific game with drops enabled."""
        # Convert game name to slug
        game_slug = game_name.lower().strip().replace(" ", "-").replace(":", "").replace("'", "")
        # First verify slug with DirectoryGameRedirect if available
        try:
            redir = await self.execute_query("DirectoryGameRedirect", {"name": game_name.strip()})
            if redir.get("game") and redir["game"].get("slug"):
                game_slug = redir["game"]["slug"]
        except Exception:
            pass

        variables = {
            "limit": limit,
            "slug": game_slug,
            "imageWidth": 50,
            "includeCostreaming": False,
            "options": {
                "broadcasterLanguages": [],
                "freeformTags": None,
                "includeRestricted": ["SUB_ONLY_LIVE"],
                "recommendationsContext": {"platform": "web"},
                "sort": "RELEVANCE",
                "systemFilters": [],
                "tags": ["c2542d6d-cd10-4532-919b-3d19f30a768b"],  # Standard 'DropsEnabled' tag ID
                "requestID": "JIRA-VXP-2397",
            },
            "sortTypeIsRecency": False,
        }
        try:
            data = await self.execute_query("DirectoryPage_Game", variables)
            streams = []
            game_node = data.get("game") or {}
            edges = game_node.get("streams", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                broadcaster = node.get("broadcaster", {})
                if node and broadcaster:
                    streams.append({
                        "channel_id": broadcaster.get("id"),
                        "channel_login": broadcaster.get("login"),
                        "channel_display_name": broadcaster.get("displayName"),
                        "title": node.get("title", ""),
                        "viewers_count": node.get("viewersCount", 0),
                        "game_name": game_name,
                        "is_live": True,
                        "stream_id": node.get("id"),
                    })
            return streams
        except Exception as exc:
            logger.warning(f"Failed to fetch live streams for game '{game_name}': {exc}")
            return []

    async def get_stream_playback_token(self, channel_login: str) -> Optional[Dict[str, Any]]:
        """Fetch stream playback access token required for telemetry tracking."""
        variables = {
            "isLive": True,
            "login": channel_login,
            "isVod": False,
            "vodID": "",
            "playerType": "site",
            "platform": "web",
        }
        try:
            data = await self.execute_query("PlaybackAccessToken", variables)
            stream_token = data.get("streamPlaybackAccessToken")
            if stream_token:
                return {
                    "value": stream_token.get("value"),
                    "signature": stream_token.get("signature"),
                }
            return None
        except Exception as exc:
            logger.warning(f"Failed to get stream playback token for '{channel_login}': {exc}")
            return None

    async def claim_drop(self, drop_id: str) -> bool:
        """Claim a completed drop reward via GraphQL mutation."""
        variables = {
            "input": {
                "dropInstanceID": drop_id,
            }
        }
        try:
            data = await self.execute_query("DropsPage_ClaimDropRewards", variables)
            claim_data = data.get("claimDropRewards") or data.get("claimDropReward") or {}
            status_val = claim_data.get("status")
            if status_val in ["ELIGIBLE_FOR_BADGE", "SUCCESS"] or "status" in claim_data or claim_data:
                logger.info(f"Successfully claimed drop instance: {drop_id}")
                return True
            logger.warning(f"Claim drop mutation result for {drop_id}: {claim_data}")
            return True
        except Exception as exc:
            logger.error(f"Error claiming drop {drop_id}: {exc}")
            return False
