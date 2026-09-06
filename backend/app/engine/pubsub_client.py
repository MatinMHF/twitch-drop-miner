"""Twitch PubSub WebSocket client for real-time drop progress and claim notifications."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional, Callable, Awaitable, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed

from app.core.logging import logger

TWITCH_PUBSUB_URL = "wss://pubsub-edge.twitch.tv/v1"


class TwitchPubSubClient:
    """Persistent PubSub WebSocket client listening to user-drop-events."""

    def __init__(
        self,
        oauth_token: str,
        twitch_user_id: str,
        on_drop_progress: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_drop_claim: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        self.oauth_token = oauth_token if not oauth_token.startswith("OAuth ") else oauth_token[6:]
        self.twitch_user_id = str(twitch_user_id)
        self.on_drop_progress = on_drop_progress
        self.on_drop_claim = on_drop_claim

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_running = False
        self._main_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start persistent PubSub connection loop."""
        if self._is_running:
            return
        self._is_running = True
        logger.info(f"Starting Twitch PubSub client for user {self.twitch_user_id}...")
        self._main_task = asyncio.create_task(self._connection_loop())

    async def stop(self) -> None:
        """Stop PubSub connection and close socket."""
        self._is_running = False
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        logger.info("Twitch PubSub client stopped.")

    async def _connection_loop(self) -> None:
        """Master connection loop with automatic reconnect and exponential backoff."""
        backoff = 1
        while self._is_running:
            try:
                async with websockets.connect(
                    TWITCH_PUBSUB_URL,
                    ssl=True,
                    ping_interval=None,  # We manage manual PINGs
                    timeout=20,
                ) as ws:
                    self._ws = ws
                    backoff = 1
                    logger.info("Connected to Twitch PubSub WebSocket.")

                    # Send LISTEN packet for user drop events
                    topic = f"user-drop-events.{self.twitch_user_id}"
                    nonce = uuid.uuid4().hex
                    listen_msg = {
                        "type": "LISTEN",
                        "nonce": nonce,
                        "data": {
                            "topics": [topic],
                            "auth_token": self.oauth_token,
                        },
                    }
                    await ws.send(json.dumps(listen_msg))

                    # Start PING task (Twitch requires PING every 4-5 mins)
                    self._ping_task = asyncio.create_task(self._ping_loop(ws))

                    # Message listening loop
                    async for raw_message in ws:
                        try:
                            msg = json.loads(raw_message)
                            await self._handle_pubsub_message(msg)
                        except Exception as exc:
                            logger.error(f"Error handling PubSub message: {exc}")

            except (ConnectionClosed, asyncio.TimeoutError, Exception) as exc:
                if not self._is_running:
                    break
                logger.warning(f"PubSub connection lost ({exc}). Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _ping_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Send periodic PING messages to keep connection active."""
        while self._is_running and ws.open:
            try:
                await asyncio.sleep(120)  # PING every 2 minutes
                if ws.open:
                    await ws.send(json.dumps({"type": "PING"}))
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def _handle_pubsub_message(self, msg: Dict[str, Any]) -> None:
        """Process received PubSub messages."""
        msg_type = msg.get("type")

        if msg_type == "PONG":
            logger.debug("Received PubSub PONG")
            return

        if msg_type == "RECONNECT":
            logger.info("PubSub requested RECONNECT. Closing current socket to reconnect...")
            if self._ws:
                await self._ws.close()
            return

        if msg_type == "RESPONSE":
            err = msg.get("error")
            if err:
                logger.error(f"PubSub subscription error: {err}")
            else:
                logger.info("PubSub subscription confirmed for drop events.")
            return

        if msg_type == "MESSAGE":
            data = msg.get("data", {})
            topic = data.get("topic", "")
            raw_payload = data.get("message", "{}")

            if f"user-drop-events.{self.twitch_user_id}" in topic:
                try:
                    event_data = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                    event_type = event_data.get("type", "")

                    if event_type == "drop-progress" or "current_progress_min" in event_data:
                        logger.info(f"⚡ PubSub real-time drop progress event received: {event_data.get('drop_name', 'Drop')} ({event_data.get('current_progress_min', 0)}/{event_data.get('required_progress_min', 0)}m)")
                        if self.on_drop_progress:
                            await self.on_drop_progress(event_data)

                    elif event_type in ["drop-claim", "claim"]:
                        logger.info(f"🎁 PubSub real-time drop CLAIM event received for {event_data.get('drop_name', 'Drop')} (ID: {event_data.get('drop_id')})")
                        if self.on_drop_claim:
                            await self.on_drop_claim(event_data)
                    else:
                        logger.debug(f"PubSub drop event: {event_type} - {event_data}")

                except Exception as exc:
                    logger.error(f"Error parsing PubSub message payload: {exc}")
