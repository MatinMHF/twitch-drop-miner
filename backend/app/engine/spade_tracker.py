"""Headless minute-watched tracking and Spade analytics dispatcher."""

from __future__ import annotations

import base64
import json
import time
from typing import Optional, Dict, Any
import httpx

from app.core.logging import logger
from app.core.twitch_constants import TWITCH_SPADE_URL, TWITCH_WEB_CLIENT_ID


class SpadeTracker:
    """Dispatches minute-watched heartbeats to Twitch telemetry endpoints.
    
    Operates without loading any video or audio fragments, consuming only
    minimal HTTP bandwidth (~1KB per minute).
    """

    def __init__(self, oauth_token: Optional[str] = None):
        self.oauth_token = oauth_token
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Client-Id": TWITCH_WEB_CLIENT_ID,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Content-Type": "text/plain;charset=UTF-8",
                "Origin": "https://www.twitch.tv",
                "Referer": "https://www.twitch.tv/",
            }
            if self.oauth_token:
                token_val = self.oauth_token if not self.oauth_token.startswith("OAuth ") else self.oauth_token[6:]
                headers["Authorization"] = f"OAuth {token_val}"

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(15.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def build_minute_payload(
        self,
        channel_id: str,
        channel_login: str,
        broadcast_id: Optional[str] = None,
        user_id: Optional[str] = None,
        game_name: Optional[str] = None,
    ) -> str:
        """Create standard base64-encoded Twitch minute-watched payload."""
        timestamp = int(time.time())
        event = {
            "event": "minute-watched",
            "properties": {
                "channel_id": str(channel_id),
                "broadcast_id": str(broadcast_id or timestamp),
                "player": "site",
                "user_id": str(user_id) if user_id else "",
                "live": True,
                "time": timestamp,
                "channel": channel_login,
                "game": game_name or "",
                "hidden": False,
                "muted": False,
                "client_time": timestamp,
            },
        }
        encoded_data = base64.b64encode(json.dumps([event]).encode("utf-8")).decode("utf-8")
        return f"data={encoded_data}"

    async def send_heartbeat(
        self,
        channel_id: str,
        channel_login: str,
        broadcast_id: Optional[str] = None,
        user_id: Optional[str] = None,
        game_name: Optional[str] = None,
    ) -> bool:
        """Send a single minute-watched heartbeat to Twitch telemetry."""
        try:
            client = await self._get_client()
            payload = self.build_minute_payload(
                channel_id=channel_id,
                channel_login=channel_login,
                broadcast_id=broadcast_id,
                user_id=user_id,
                game_name=game_name,
            )
            response = await client.post(
                TWITCH_SPADE_URL,
                content=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code in (200, 204):
                logger.debug(f"Spade heartbeat sent successfully for channel {channel_login} ({game_name})")
                return True
            logger.warning(f"Spade response code: {response.status_code}")
            return True
        except Exception as exc:
            logger.warning(f"Failed to send Spade heartbeat for {channel_login}: {exc}")
            return False
