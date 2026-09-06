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
        """Periodic heartbeat loop maintaining active stream session every 60 seconds."""
        import urllib.parse
        import httpx

        http_client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Referer": "https://www.twitch.tv/",
                "Origin": "https://www.twitch.tv",
            },
            timeout=httpx.Timeout(15.0),
        )

        playback_token: Optional[Dict[str, Any]] = None
        consecutive_failures = 0

        try:
            while self._is_running:
                try:
                    # 1. Obtain/Refresh playback token if missing or periodically
                    if not playback_token or self.minutes_watched_in_session % 10 == 0:
                        playback_token = await self._gql_client.get_stream_playback_token(self.channel_login)

                    # 2. Ping Usher HLS stream endpoint and variant playlist to register active playback session
                    if playback_token and "value" in playback_token and "signature" in playback_token:
                        val = urllib.parse.quote_plus(playback_token["value"])
                        sig = playback_token["signature"]
                        usher_url = (
                            f"https://usher.ttvnw.net/api/channel/hls/{self.channel_login}.m3u8"
                            f"?client_id={self._gql_client.client_id}&token={val}&sig={sig}&allow_source=true&allow_audio_only=true&fast_bread=true"
                        )
                        try:
                            usher_res = await http_client.get(usher_url)
                            if usher_res.status_code == 200:
                                # Fetch variant media playlist (audio/low) to confirm playback session with Edge cluster
                                lines = usher_res.text.splitlines()
                                variant_urls = [line.strip() for line in lines if line.strip().startswith("http")]
                                if variant_urls:
                                    var_url = variant_urls[-1]  # audio_only or lowest segment list
                                    var_res = await http_client.get(var_url)
                                    if var_res.status_code == 200:
                                        var_lines = var_res.text.splitlines()
                                        # Ping trigger URL if present in manifest
                                        for vl in var_lines:
                                            if 'X-TV-TWITCH-TRIGGER-URL="' in vl:
                                                try:
                                                    trig_url = vl.split('X-TV-TWITCH-TRIGGER-URL="')[1].split('"')[0]
                                                    await http_client.get(trig_url)
                                                except Exception:
                                                    pass
                                        # Fetch tiny 2KB header of latest audio segment to register genuine active buffer
                                        seg_urls = [
                                            vl.strip() for vl in var_lines 
                                            if vl.strip().startswith("http") or (not vl.strip().startswith("#") and vl.strip().endswith(".ts"))
                                        ]
                                        if seg_urls:
                                            latest_seg = seg_urls[0]
                                            if not latest_seg.startswith("http"):
                                                base = var_url.rsplit("/", 1)[0]
                                                latest_seg = f"{base}/{latest_seg}"
                                            await http_client.get(latest_seg, headers={"Range": "bytes=0-2048"})
                        except Exception as exc:
                            logger.debug(f"Usher/Variant stream ping notice for @{self.channel_login}: {exc}")

                    # 3. Dispatch Spade minute-watched telemetry heartbeat with game metadata
                    try:
                        await self._spade_tracker.send_heartbeat(
                            channel_id=self.channel_id,
                            channel_login=self.channel_login,
                            broadcast_id=self.stream_id,
                            user_id=self.twitch_user_id,
                            game_name=self.game_name,
                        )
                    except Exception as exc:
                        logger.debug(f"Spade heartbeat notice: {exc}")

                    # 4. Increment minutes watched and record timestamp
                    consecutive_failures = 0
                    self.minutes_watched_in_session += 1
                    self.last_heartbeat_at = datetime.now(timezone.utc)
                    logger.debug(f"Stream watch minute heartbeat completed for @{self.channel_login} (session: {self.minutes_watched_in_session}m)")

                    if self.on_minute_heartbeat:
                        try:
                            await self.on_minute_heartbeat(self.minutes_watched_in_session)
                        except Exception as exc:
                            logger.error(f"Error in on_minute_heartbeat callback: {exc}")

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
                    logger.warning(f"Watch loop notice for @{self.channel_login}: {exc}")
                    if consecutive_failures >= 5:
                        logger.warning(f"Too many consecutive watch failures on @{self.channel_login}. Triggering failover.")
                        if self.on_channel_offline:
                            await self.on_channel_offline()
                        break
                    await asyncio.sleep(10)
        finally:
            await http_client.aclose()

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
