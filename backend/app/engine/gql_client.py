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
    TWITCH_USER_AGENT,
    build_gql_persisted_query,
)


class TwitchGQLClient:
    """High-performance async Twitch GraphQL Client."""

    def __init__(
        self,
        oauth_token: Optional[str] = None,
        client_id: Optional[str] = None,
        twitch_user_id: Optional[str] = None,
    ):
        self.client_id = client_id or TWITCH_WEB_CLIENT_ID
        self.oauth_token = oauth_token
        self.twitch_user_id = twitch_user_id
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            headers = {
                "Client-Id": self.client_id,
                "User-Agent": TWITCH_USER_AGENT,
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

    async def execute_raw_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a raw GraphQL query string directly against Twitch GQL endpoint."""
        client = await self._get_client()
        payload = {
            "query": query,
            "variables": variables,
        }
        try:
            response = await client.post(TWITCH_GQL_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except Exception as exc:
            logger.warning(f"Raw Twitch GQL query execution failed: {exc}")
            return {}

    # --- Query Implementations ---

    async def search_games(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search Twitch games directory by querying Twitch searchFor API and filtering real games only."""
        items: List[Dict[str, Any]] = []
        seen_ids = set()

        q_clean = query.strip()
        q_lower = q_clean.lower()
        if not q_lower:
            return []

        # 1. Primary: Search Twitch games using official searchFor GraphQL query
        search_query_doc = """
        query SearchForGames($query: String!) {
          searchFor(userQuery: $query, platform: "web") {
            games {
              items {
                id
                name
                boxArtURL
                viewersCount
              }
            }
          }
        }
        """
        try:
            data = await self.execute_raw_query(search_query_doc, {"query": q_clean})
            games_data = data.get("searchFor", {}).get("games", {}).get("items", [])
            for g in games_data:
                gid = str(g.get("id") or "").strip()
                gname = g.get("name")
                if not gid or not gname or gid in seen_ids:
                    continue
                seen_ids.add(gid)

                box_art = g.get("boxArtURL")
                if box_art:
                    box_art_url = box_art.replace("{width}", "285").replace("{height}", "380")
                else:
                    box_art_url = f"https://static-cdn.jtvnw.net/ttv-boxart/{gid}-285x380.jpg"

                viewers = g.get("viewersCount") or 0
                items.append({
                    "id": gid,
                    "name": gname,
                    "box_art_url": box_art_url,
                    "viewers_count": viewers,
                })
        except Exception as exc:
            logger.debug(f"Twitch searchFor query error: {exc}")

        # 2. Secondary: Search against active drop campaigns
        try:
            campaigns = await self.get_available_drop_campaigns()
            for c in campaigns:
                g = c.get("game") or {}
                gid = str(g.get("id") or "").strip()
                gname = g.get("name", "")
                if gid and gname and q_lower in gname.lower() and gid not in seen_ids:
                    seen_ids.add(gid)
                    box_art = g.get("boxArtURL")
                    if box_art:
                        box_art_url = box_art.replace("{width}", "285").replace("{height}", "380")
                    else:
                        box_art_url = f"https://static-cdn.jtvnw.net/ttv-boxart/{gid}-285x380.jpg"
                    items.append({
                        "id": gid,
                        "name": gname,
                        "box_art_url": box_art_url,
                        "viewers_count": 0,
                    })
        except Exception as exc:
            logger.debug(f"Campaign search filter error: {exc}")

        # 3. Fallback: Query DirectoryGameRedirect for exact or slug game lookup on Twitch API
        if not items:
            try:
                data = await self.execute_query("DirectoryGameRedirect", {"name": q_clean})
                game_node = data.get("game")
                if game_node and game_node.get("id"):
                    gid = str(game_node.get("id"))
                    slug = game_node.get("slug") or q_clean
                    display_name = game_node.get("displayName") or slug.replace("-", " ").title()
                    box_art = game_node.get("boxArtURL")
                    if box_art:
                        box_art_url = box_art.replace("{width}", "285").replace("{height}", "380")
                    else:
                        box_art_url = f"https://static-cdn.jtvnw.net/ttv-boxart/{gid}-285x380.jpg"
                    if gid not in seen_ids:
                        seen_ids.add(gid)
                        items.append({
                            "id": gid,
                            "name": display_name,
                            "box_art_url": box_art_url,
                            "viewers_count": 0,
                        })
            except Exception as exc:
                logger.debug(f"DirectoryGameRedirect query error: {exc}")

        # Smart ranking:
        # Priority 1: Exact match name (case-insensitive)
        # Priority 2: Starts with query
        # Priority 3: Contains all query words
        # Then sub-sort by viewers_count descending
        query_words = q_lower.split()

        def rank_score(item: Dict[str, Any]) -> tuple:
            name_l = item["name"].lower()
            viewers = item.get("viewers_count", 0)
            if name_l == q_lower:
                match_tier = 0
            elif name_l.startswith(q_lower):
                match_tier = 1
            elif all(w in name_l for w in query_words):
                match_tier = 2
            elif any(w in name_l for w in query_words):
                match_tier = 3
            else:
                match_tier = 4
            return (match_tier, -viewers)

        items.sort(key=rank_score)
        return items[:limit]

    async def get_available_drop_campaigns(self, extra_games: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch all active and upcoming Drop campaigns across Twitch and merge with user Inventory."""
        campaigns_by_id: Dict[str, Dict[str, Any]] = {}
        variables = {"fetchRewardCampaigns": False}

        # 1. Primary: Fetch all campaigns from ViewerDropsDashboard (returns all active/upcoming campaigns)
        try:
            dash_data = await self.execute_query("ViewerDropsDashboard", variables)
            dash_user = dash_data.get("currentUser", {}) or {}
            dash_camps = dash_user.get("dropCampaigns", []) or []
            for c in dash_camps:
                if c and isinstance(c, dict) and "id" in c:
                    cid = c["id"]
                    status = c.get("status")
                    if status in ("ACTIVE", "UPCOMING"):
                        campaigns_by_id[cid] = c
        except Exception as exc:
            logger.debug(f"ViewerDropsDashboard query error: {exc}")

        # 2. Secondary: Merge from user Inventory (in-progress campaigns with progress)
        try:
            inv_data = await self.execute_query("Inventory", variables)
            user_inv = inv_data.get("currentUser", {}) or {}
            inv_node = user_inv.get("inventory", {}) if isinstance(user_inv, dict) else {}
            in_prog = inv_node.get("dropCampaignsInProgress", []) or []
            for c in in_prog:
                if c and isinstance(c, dict) and "id" in c:
                    cid = c["id"]
                    if cid in campaigns_by_id:
                        campaigns_by_id[cid].update(c)
                    else:
                        campaigns_by_id[cid] = c
        except Exception as exc:
            logger.debug(f"Inventory query error: {exc}")

        return list(campaigns_by_id.values())

    async def get_channel_drop_campaigns(self, channel_id: str) -> List[Dict[str, Any]]:
        """Fetch active drop campaigns from a channel's DropsHighlightService."""
        variables = {"channelID": str(channel_id)}
        try:
            data = await self.execute_query("DropsHighlightService_AvailableDrops", variables)
            channel_node = data.get("channel") or {}
            return channel_node.get("viewerDropCampaigns") or []
        except Exception as exc:
            logger.debug(f"Failed to query DropsHighlightService for channel {channel_id}: {exc}")
            return []

    async def get_campaign_details(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed drop rules and progress for a specific campaign."""
        variables = {
            "dropID": campaign_id,
            "channelLogin": str(self.twitch_user_id or ""),
        }
        try:
            data = await self.execute_query("DropCampaignDetails", variables)
            user_node = data.get("user", {}) or data.get("currentUser", {}) or {}
            if user_node and user_node.get("dropCampaign"):
                return user_node.get("dropCampaign")
        except Exception as exc:
            logger.debug(f"Failed to fetch campaign details for {campaign_id}: {exc}")
        return None

    async def get_stream_info(self, channel_login: str) -> Optional[Dict[str, Any]]:
        """Fetch live stream metadata (stream ID, channel ID, game ID/name) via VideoPlayerStreamInfoOverlayChannel."""
        try:
            data = await self.execute_query(
                "VideoPlayerStreamInfoOverlayChannel",
                {"channel": channel_login.lower().strip()}
            )
            user = data.get("user") or {}
            stream = user.get("stream")
            broadcast = user.get("broadcastSettings") or {}
            if stream and stream.get("id"):
                game = broadcast.get("game") or {}
                return {
                    "is_live": True,
                    "stream_id": str(stream["id"]),
                    "channel_id": str(broadcast.get("id") or user.get("id") or ""),
                    "channel_login": channel_login,
                    "viewers_count": stream.get("viewersCount", 0),
                    "game_id": str(game.get("id") or ""),
                    "game_name": game.get("name") or game.get("displayName") or "",
                    "title": broadcast.get("title", ""),
                }
        except Exception as exc:
            logger.debug(f"Failed to fetch stream info for {channel_login}: {exc}")
        return None

    async def send_spade_minute_watched(
        self,
        channel_id: str,
        channel_login: str,
        broadcast_id: str,
        game_name: str,
        game_id: str = "",
        user_id: Optional[str] = None,
    ) -> bool:
        """Send standard minute-watched telemetry heartbeat via Twitch GraphQL sendSpadeEvents mutation."""
        from datetime import datetime, timezone
        import gzip
        import base64
        payload = [
            {
                "event": "minute-watched",
                "properties": {
                    "broadcast_id": str(broadcast_id),
                    "channel_id": str(channel_id),
                    "channel": channel_login.lower(),
                    "client_time": datetime.now(timezone.utc).isoformat(),
                    "game": game_name or "",
                    "game_id": str(game_id or ""),
                    "hidden": False,
                    "is_live": True,
                    "live": True,
                    "logged_in": True,
                    "minutes_logged": 1,
                    "muted": False,
                    "user_id": int(user_id) if user_id and str(user_id).isdigit() else 0,
                }
            }
        ]
        compressed = gzip.compress(json.dumps(payload, separators=(',', ':')).encode("utf-8"))
        g64data = base64.b64encode(compressed).decode("utf-8")
        gql_doc = (
            "\n mutation SendEvents($input: SendSpadeEventsInput!) {\n"
            " sendSpadeEvents(input: $input) {\n"
            " statusCode\n"
            "}\n}\n"
        )
        try:
            data = await self.execute_raw_query(
                gql_doc,
                {
                    "input": {
                        "data": g64data,
                        "repository": "twilight",
                        "encoding": "GZIP_B64",
                    }
                }
            )
            return data.get("sendSpadeEvents", {}).get("statusCode") == 204
        except Exception as exc:
            logger.debug(f"send_spade_minute_watched error: {exc}")
            return False

    async def get_inventory_drops(self) -> Dict[str, Any]:
        """Fetch current user's drop inventory progress and claimable drops."""
        variables = {"fetchRewardCampaigns": False}
        try:
            data = await self.execute_query("Inventory", variables)
            user = data.get("currentUser", {}) or data.get("user", {}) or {}
            inv_node = user.get("inventory", {}) if isinstance(user, dict) else {}
            in_prog = inv_node.get("dropCampaignsInProgress", []) if isinstance(inv_node, dict) else []
            game_events = inv_node.get("gameEventDrops", []) if isinstance(inv_node, dict) else []
            return {
                "dropCampaignsInProgress": in_prog,
                "gameEventDrops": game_events,
                "user": user,
            }
        except Exception as exc:
            logger.warning(f"Failed to fetch user inventory drops: {exc}")
            return {"dropCampaignsInProgress": [], "gameEventDrops": []}

    async def get_live_streams_for_game(self, game_name: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch top live channels broadcasting a specific game."""
        game_slug = game_name.lower().strip().replace(" ", "-").replace(":", "").replace("'", "")
        try:
            redir = await self.execute_query("DirectoryGameRedirect", {"name": game_name.strip()})
            if redir.get("game") and redir["game"].get("slug"):
                game_slug = redir["game"]["slug"]
        except Exception:
            pass

        # 1. Try with DropsEnabled tag
        streams = await self._fetch_directory_streams(game_name, game_slug, limit, ["c2542d6d-cd10-4532-919b-3d19f30a768b"])
        # 2. Fallback to general live streams in game category if no tagged streams found
        if not streams:
            streams = await self._fetch_directory_streams(game_name, game_slug, limit, [])
        return streams

    async def _fetch_directory_streams(self, game_name: str, game_slug: str, limit: int, tags: List[str]) -> List[Dict[str, Any]]:
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
                "tags": tags,
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
                        "channel_id": str(broadcaster.get("id")),
                        "channel_login": broadcaster.get("login"),
                        "channel_display_name": broadcaster.get("displayName"),
                        "title": node.get("title", ""),
                        "viewers_count": node.get("viewersCount", 0),
                        "game_name": game_name,
                        "is_live": True,
                        "stream_id": str(node.get("id")),
                    })
            return streams
        except Exception as exc:
            logger.debug(f"DirectoryPage_Game query notice for '{game_name}' with tags {tags}: {exc}")
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
