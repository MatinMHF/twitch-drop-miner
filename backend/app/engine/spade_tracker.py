"""Headless minute-watched tracking and Spade analytics dispatcher."""

from __future__ import annotations

import base64
import gzip
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from app.core.logging import logger
from app.core.twitch_constants import TWITCH_GQL_URL, TWITCH_WEB_CLIENT_ID, TWITCH_USER_AGENT


def isonow() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_minify(data: Any) -> str:
    return json.dumps(data, separators=(',', ':'))


class SpadeTracker:
    """Dispatches minute-watched heartbeats to Twitch GraphQL telemetry.
    
    Operates without downloading video/audio streams, advancing drop progress
    with minimal bandwidth overhead (~1KB/minute).
    """

    def __init__(self, oauth_token: Optional[str] = None):
        self.oauth_token = oauth_token
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Client-Id": TWITCH_WEB_CLIENT_ID,
                "User-Agent": TWITCH_USER_AGENT,
                "Accept-Language": "en-US",
                "Content-Type": "application/json",
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

    async def send_heartbeat(
        self,
        channel_id: str,
        channel_login: str,
        broadcast_id: Optional[str] = None,
        user_id: Optional[str] = None,
        game_name: Optional[str] = None,
        game_id: Optional[str] = None,
    ) -> bool:
        """Send a standard minute-watched heartbeat via GraphQL sendSpadeEvents."""
        try:
            client = await self._get_client()
            b_id = str(broadcast_id or "")
            uid = int(user_id) if user_id and str(user_id).isdigit() else 0

            payload = [
                {
                    "event": "minute-watched",
                    "properties": {
                        "broadcast_id": b_id,
                        "channel_id": str(channel_id),
                        "channel": channel_login.lower(),
                        "client_time": isonow(),
                        "game": game_name or "",
                        "game_id": str(game_id or ""),
                        "hidden": False,
                        "is_live": True,
                        "live": True,
                        "logged_in": True,
                        "minutes_logged": 1,
                        "muted": False,
                        "user_id": uid,
                    }
                }
            ]

            compressed = gzip.compress(json_minify(payload).encode("utf-8"))
            g64data = base64.b64encode(compressed).decode("utf-8")

            gql_payload = {
                "query": "\n mutation SendEvents($input: SendSpadeEventsInput!) {\n sendSpadeEvents(input: $input) {\n statusCode\n}\n}\n",
                "variables": {
                    "input": {
                        "data": g64data,
                        "repository": "twilight",
                        "encoding": "GZIP_B64",
                    }
                }
            }

            response = await client.post(TWITCH_GQL_URL, json=gql_payload)
            if response.status_code == 200:
                data = response.json()
                code = data.get("data", {}).get("sendSpadeEvents", {}).get("statusCode")
                if code == 204:
                    logger.info(f"✅ Minute heartbeat credited on Twitch for @{channel_login} ({game_name or 'Game'})")
                    return True
                else:
                    logger.warning(f"Unexpected Spade response code for @{channel_login}: {code}")
                    return True
            else:
                logger.warning(f"Spade GQL HTTP {response.status_code} for @{channel_login}")
                return False
        except Exception as exc:
            logger.warning(f"Failed to send Spade heartbeat for {channel_login}: {exc}")
            return False
