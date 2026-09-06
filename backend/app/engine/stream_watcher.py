"""Stream watching engine for tracking channel heartbeats and live status."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any, Awaitable

from app.core.config import settings
from app.core.logging import logger
from app.engine.gql_client import TwitchGQLClient
from app.engine.spade_tracker import SpadeTracker


class StreamWatcher:
    """Manages an active stream watching session without downloading video."""

    def __init__(
        self,
        oauth_token: str,
        twitch_user_id: str,
        channel_id: str,
        channel_login: str,
        channel_display_name: str,
        game_name: str,
        stream_id: Optional[str] = None,
        on_channel_offline: Optional[Callable[[], Awaitable[None]]] = None,
        on_minute_heartbeat: Optional[Callable[[int], Awaitable[None]]] = None,
    ):
        self.oauth_token = oauth_token
        self.twitch_user_id = twitch_user_id
        self.channel_id = channel_id
        self.channel_login = channel_login
        self.channel_display_name = channel_display_name
        self.game_name = game_name
        self.stream_id = stream_id
        self.on_channel_offline = on_channel_offline
        self.on_minute_heartbeat = on_minute_heartbeat

        self._gql_client = TwitchGQLClient(oauth_token=oauth_token)
        self._spade_tracker = SpadeTracker(oauth_token=oauth_token)
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self.minutes_watched_in_session = 0
        self.last_heartbeat_at: Optional[datetime] = None

    async def start(self) -> None:
        """Start the async heartbeat loop for this channel."""
        if self._is_running:
            return
        self._is_running = True
        logger.info(f"Starting headless stream watch on channel '{self.channel_login}' ({self.game_name})")
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop the heartbeat loop."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._gql_client.close()
        await self._spade_tracker.close()
        logger.info(f"Stopped stream watcher for channel '{self.channel_login}'")

    async def _watch_loop(self) -> None:
        """Periodic heartbeat loop dispatching events every 60 seconds."""
        # Initial playback token fetch
        await self._gql_client.get_stream_playback_token(self.channel_login)

        consecutive_failures = 0
        while self._is_running:
            try:
                # Dispatch Spade minute-watched telemetry
                success = await self._spade_tracker.send_heartbeat(
                    channel_id=self.channel_id,
                    channel_login=self.channel_login,
                    broadcast_id=self.stream_id,
                    user_id=self.twitch_user_id,
                )

                if success:
                    consecutive_failures = 0
                    self.minutes_watched_in_session += 1
                    self.last_heartbeat_at = datetime.now(timezone.utc)

                    if self.on_minute_heartbeat:
                        try:
                            await self.on_minute_heartbeat(self.minutes_watched_in_session)
                        except Exception as exc:
                            logger.error(f"Error in on_minute_heartbeat callback: {exc}")
                else:
                    consecutive_failures += 1

                # Every 5 minutes, verify channel is still broadcasting
                if self.minutes_watched_in_session % 5 == 0:
                    is_live = await self._verify_channel_live()
                    if not is_live:
                        logger.warning(f"Channel '{self.channel_login}' went offline! Triggering failover.")
                        if self.on_channel_offline:
                            await self.on_channel_offline()
                        break

                await asyncio.sleep(settings.WATCH_HEARTBEAT_SECONDS)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                consecutive_failures += 1
                logger.error(f"Error during stream watch heartbeat for {self.channel_login}: {exc}")
                if consecutive_failures >= 5:
                    logger.warning(f"Too many consecutive watch failures on {self.channel_login}. Triggering failover.")
                    if self.on_channel_offline:
                        await self.on_channel_offline()
                    break
                await asyncio.sleep(10)

    async def _verify_channel_live(self) -> bool:
        """Check if streamer is still live."""
        try:
            streams = await self._gql_client.get_live_streams_for_game(self.game_name, limit=50)
            for s in streams:
                if s["channel_login"].lower() == self.channel_login.lower():
                    return True
            return False
        except Exception:
            return True  # Avoid false failovers on network blips
