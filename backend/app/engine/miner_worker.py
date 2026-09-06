"""Master Background Miner Worker orchestrating polling, stream watching, and live state."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.logging import logger
from app.db.database import AsyncSessionLocal
from app.db.repositories import (
    get_active_twitch_account,
    get_decrypted_tokens,
)
from app.engine.drop_manager import DropManager
from app.engine.stream_watcher import StreamWatcher


class MiningWorker:
    """Master Background Miner Engine."""

    def __init__(self):
        self.state: str = "IDLE"  # "IDLE", "MINING", "PAUSED", "ERROR", "NO_ACCOUNT"
        self.active_target: Optional[Dict[str, Any]] = None
        self.stream_watcher: Optional[StreamWatcher] = None
        self.drop_manager: Optional[DropManager] = None
        self.last_heartbeat_at: Optional[datetime] = None
        self.next_poll_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.total_drops_claimed_session: int = 0
        self.is_paused: bool = False

        self._main_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._ws_broadcast_callback: Optional[Any] = None

    def register_ws_broadcaster(self, callback: Any) -> None:
        self._ws_broadcast_callback = callback

    async def broadcast_status(self) -> None:
        """Broadcast current miner status over WebSocket if registered."""
        if self._ws_broadcast_callback:
            try:
                await self._ws_broadcast_callback(self.get_status())
            except Exception as exc:
                logger.error(f"Failed to broadcast WS status: {exc}")

    def get_status(self) -> Dict[str, Any]:
        """Return serialized state for REST / WebSocket consumers."""
        progress_pct = 0.0
        req_min = 0
        cur_min = 0

        if self.active_target:
            req_min = self.active_target.get("required_minutes", 0)
            cur_min = self.active_target.get("current_minutes", 0)
            if self.stream_watcher:
                cur_min += self.stream_watcher.minutes_watched_in_session
            if req_min > 0:
                progress_pct = min(round((cur_min / req_min) * 100, 2), 100.0)

        active_channel = None
        if self.active_target and self.active_target.get("channel"):
            ch = self.active_target["channel"]
            active_channel = {
                "channel_id": ch.get("channel_id"),
                "channel_login": ch.get("channel_login"),
                "channel_display_name": ch.get("channel_display_name"),
                "title": ch.get("title"),
                "viewers_count": ch.get("viewers_count"),
                "game_name": ch.get("game_name"),
                "is_live": ch.get("is_live", True),
                "stream_id": ch.get("stream_id"),
            }

        return {
            "state": self.state,
            "active_game_id": self.active_target.get("game_id") if self.active_target else None,
            "active_game_name": self.active_target.get("game_name") if self.active_target else None,
            "active_campaign_id": self.active_target.get("campaign_id") if self.active_target else None,
            "active_campaign_name": self.active_target.get("campaign_name") if self.active_target else None,
            "active_channel": active_channel,
            "current_drop_id": self.active_target.get("drop_id") if self.active_target else None,
            "current_drop_name": self.active_target.get("drop_name") if self.active_target else None,
            "current_drop_progress_percent": progress_pct,
            "current_drop_minutes_watched": cur_min,
            "current_drop_required_minutes": req_min,
            "total_drops_claimed_session": self.total_drops_claimed_session,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "next_poll_at": self.next_poll_at.isoformat() if self.next_poll_at else None,
            "error_message": self.error_message,
            "is_paused": self.is_paused,
        }

    async def start(self) -> None:
        """Start background miner orchestrator."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("Initializing Twitch Drop Mining Engine...")
        self._main_task = asyncio.create_task(self._orchestrator_loop())

    async def stop(self) -> None:
        """Stop miner engine and close active watchers."""
        self._is_running = False
        if self.stream_watcher:
            await self.stream_watcher.stop()
            self.stream_watcher = None
        if self.drop_manager:
            await self.drop_manager.close()
            self.drop_manager = None
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        self.state = "IDLE"
        self.active_target = None
        logger.info("Twitch Drop Mining Engine stopped.")
        await self.broadcast_status()

    async def pause(self) -> None:
        """Pause mining activity."""
        self.is_paused = True
        self.state = "PAUSED"
        if self.stream_watcher:
            await self.stream_watcher.stop()
            self.stream_watcher = None
        logger.info("Mining paused by user.")
        await self.broadcast_status()

    async def resume(self) -> None:
        """Resume mining activity."""
        self.is_paused = False
        self.state = "IDLE"
        logger.info("Mining resumed by user.")
        await self.broadcast_status()
        await self.check_and_mine()

    async def check_and_mine(self) -> None:
        """Evaluate targets and start watching if suitable campaign is active."""
        if self.is_paused:
            return

        async with AsyncSessionLocal() as db:
            account = await get_active_twitch_account(db)

        if not account:
            self.state = "NO_ACCOUNT"
            self.active_target = None
            if self.stream_watcher:
                await self.stream_watcher.stop()
                self.stream_watcher = None
            await self.broadcast_status()
            return

        tokens = get_decrypted_tokens(account)
        access_token = tokens["access_token"]
        if not access_token:
            self.state = "NO_ACCOUNT"
            await self.broadcast_status()
            return

        # Setup drop manager
        if not self.drop_manager:
            self.drop_manager = DropManager(oauth_token=access_token, twitch_user_id=account.twitch_user_id)

        try:
            target = await self.drop_manager.select_next_target()
            if not target:
                logger.info("No active campaigns or live drop channels found for current watchlist.")
                self.state = "IDLE"
                self.active_target = None
                if self.stream_watcher:
                    await self.stream_watcher.stop()
                    self.stream_watcher = None
                await self.broadcast_status()
                return

            # Check if target channel changed
            current_ch = self.active_target.get("channel", {}).get("channel_login") if self.active_target else None
            new_ch = target.get("channel", {}).get("channel_login")

            if current_ch != new_ch or not self.stream_watcher:
                if self.stream_watcher:
                    await self.stream_watcher.stop()

                self.active_target = target
                ch_info = target["channel"]

                self.stream_watcher = StreamWatcher(
                    oauth_token=access_token,
                    twitch_user_id=account.twitch_user_id,
                    channel_id=ch_info["channel_id"],
                    channel_login=ch_info["channel_login"],
                    channel_display_name=ch_info["channel_display_name"],
                    game_name=target["game_name"],
                    stream_id=ch_info.get("stream_id"),
                    on_channel_offline=self._handle_channel_offline,
                    on_minute_heartbeat=self._handle_minute_heartbeat,
                )
                await self.stream_watcher.start()
                self.state = "MINING"
                logger.info(f"Mining active drop '{target['drop_name']}' on channel @{ch_info['channel_login']}")
            else:
                self.active_target = target

            await self.broadcast_status()

        except Exception as exc:
            logger.error(f"Error during check_and_mine: {exc}")
            self.state = "ERROR"
            self.error_message = str(exc)
            await self.broadcast_status()

    async def _handle_minute_heartbeat(self, minutes_in_session: int) -> None:
        """Callback invoked when a minute watched heartbeat completes."""
        self.last_heartbeat_at = datetime.now(timezone.utc)
        if self.active_target:
            cur = self.active_target.get("current_minutes", 0) + minutes_in_session
            req = self.active_target.get("required_minutes", 0)

            # Check if reached 100%
            if cur >= req and req > 0:
                logger.info(f"Drop '{self.active_target['drop_name']}' reached 100% watch requirement. Claiming reward...")
                if self.drop_manager:
                    claimed = await self.drop_manager.claim_drop_reward(
                        drop_id=self.active_target["drop_id"],
                        drop_name=self.active_target["drop_name"],
                        campaign_id=self.active_target["campaign_id"],
                        campaign_name=self.active_target["campaign_name"],
                        game_id=self.active_target["game_id"],
                        game_name=self.active_target["game_name"],
                        channel_name=self.active_target.get("channel", {}).get("channel_display_name"),
                    )
                    if claimed:
                        self.total_drops_claimed_session += 1
                        # Re-evaluate targets
                        await self.check_and_mine()
                        return

        await self.broadcast_status()

    async def _handle_channel_offline(self) -> None:
        """Automatic failover triggered when the current channel goes offline."""
        logger.info("Triggering automatic streamer failover...")
        if self.stream_watcher:
            await self.stream_watcher.stop()
            self.stream_watcher = None
        await self.check_and_mine()

    async def _orchestrator_loop(self) -> None:
        """Master background loop polling periodically (default 30m)."""
        while self._is_running:
            try:
                poll_interval = settings.POLL_INTERVAL_MINUTES
                self.next_poll_at = datetime.now(timezone.utc) + timedelta(minutes=poll_interval)
                await self.check_and_mine()
                await asyncio.sleep(poll_interval * 60)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in orchestrator loop: {exc}")
                await asyncio.sleep(60)


miner_service = MiningWorker()
