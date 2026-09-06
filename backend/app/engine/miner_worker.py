"""Master Background Miner Worker powered by DevilXD Twitch Drops engine."""

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
    get_watchlist,
    log_claimed_drop,
)
from app.engine.devilxd_bridge import create_devilxd_instance, FastAPIBridgeGUIManager, Twitch, State


class MiningWorker:
    """Master Background Miner Worker orchestrating DevilXD engine with FastAPI & WebSockets."""

    def __init__(self):
        self.twitch: Optional[Twitch] = None
        self.bridge: Optional[FastAPIBridgeGUIManager] = None
        self.is_running: bool = False
        self.is_paused: bool = False
        self.error_message: Optional[str] = None
        self.next_poll_at: Optional[datetime] = None

        self._main_task: Optional[asyncio.Task] = None
        self._orchestrator_task: Optional[asyncio.Task] = None
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
        cur_drop = self.bridge.current_drop if self.bridge else None
        cur_channel = self.bridge.current_channel if self.bridge else None
        status_text = self.bridge.status_text if self.bridge else "Idle"

        req_min = getattr(cur_drop, "required_minutes", 0) if cur_drop else 0
        cur_min = getattr(cur_drop, "current_minutes", 0) if cur_drop else 0
        progress_pct = round(getattr(cur_drop, "progress", 0.0) * 100, 2) if cur_drop else 0.0

        stream_info = None
        if cur_channel:
            stream = getattr(cur_channel, "_stream", None)
            game_name = getattr(cur_channel.game, "name", "") if hasattr(cur_channel, "game") and cur_channel.game else ""
            stream_info = {
                "channel_id": str(cur_channel.id),
                "channel_login": getattr(cur_channel, "_login", ""),
                "channel_display_name": getattr(cur_channel, "name", ""),
                "title": getattr(stream, "title", "") if stream else "",
                "viewers_count": getattr(stream, "viewers", 0) if stream else 0,
                "game_name": game_name,
                "is_live": getattr(cur_channel, "online", True),
                "stream_id": str(getattr(stream, "broadcast_id", "")) if stream else None,
            }

        target_obj = None
        if cur_drop:
            camp = getattr(cur_drop, "campaign", None)
            camp_game = getattr(camp, "game", None) if camp else None
            game_name = getattr(camp_game, "name", "") if camp_game else (stream_info["game_name"] if stream_info else "")
            target_obj = {
                "game_id": str(getattr(camp_game, "id", "")) if camp_game else "",
                "game_name": game_name,
                "campaign_id": getattr(camp, "id", "") if camp else "",
                "campaign_name": getattr(camp, "name", "") if camp else "",
                "drop_id": getattr(cur_drop, "id", ""),
                "drop_instance_id": getattr(cur_drop, "claim_id", getattr(cur_drop, "id", "")),
                "drop_name": getattr(cur_drop, "name", ""),
                "required_minutes": req_min,
                "current_minutes": cur_min,
                "progress_percent": progress_pct,
                "channel": stream_info,
            }

        active_targets_list = [target_obj] if target_obj else []
        primary = target_obj

        # Compute high-level state
        state = "IDLE"
        if not self.is_running:
            state = "IDLE"
        elif self.is_paused:
            state = "PAUSED"
        elif self.error_message:
            state = "ERROR"
        elif cur_channel is not None and cur_channel.online:
            state = "MINING"
        elif any(k in status_text.lower() for k in ("gathering", "fetching", "cleanup", "switching")):
            state = "POLLING"

        last_hb = self.bridge.last_heartbeat.isoformat() if self.bridge and self.bridge.last_heartbeat else None
        next_poll = self.next_poll_at.isoformat() if self.next_poll_at else None
        total_claimed = self.bridge.total_claimed if self.bridge else 0

        return {
            "state": state,
            "active_targets": active_targets_list,
            "active_game_id": primary["game_id"] if primary else None,
            "active_game_name": primary["game_name"] if primary else (stream_info["game_name"] if stream_info else None),
            "active_campaign_id": primary["campaign_id"] if primary else None,
            "active_campaign_name": primary["campaign_name"] if primary else None,
            "active_channel": stream_info,
            "current_drop_id": primary["drop_id"] if primary else None,
            "current_drop_name": primary["drop_name"] if primary else None,
            "current_drop_progress_percent": progress_pct,
            "current_drop_minutes_watched": cur_min,
            "current_drop_required_minutes": req_min,
            "total_drops_claimed_session": total_claimed,
            "last_heartbeat_at": last_hb,
            "next_poll_at": next_poll,
            "error_message": self.error_message,
            "is_paused": self.is_paused,
            "status_text": status_text,
        }

    async def _handle_drop_claimed(self, title: str, msg: str) -> None:
        """Record claimed drop to DB and broadcast update."""
        logger.info(f"⚡ Processing claimed drop: {title} - {msg}")
        try:
            cur_drop = self.bridge.current_drop if self.bridge else None
            cur_channel = self.bridge.current_channel if self.bridge else None

            drop_id = getattr(cur_drop, "id", f"drop_{int(datetime.now().timestamp())}") if cur_drop else f"drop_{int(datetime.now().timestamp())}"
            drop_name = getattr(cur_drop, "name", title) if cur_drop else title
            camp = getattr(cur_drop, "campaign", None) if cur_drop else None
            camp_id = getattr(camp, "id", "") if camp else ""
            camp_name = getattr(camp, "name", "") if camp else ""
            camp_game = getattr(camp, "game", None) if camp else None
            game_id = str(getattr(camp_game, "id", "")) if camp_game else ""
            game_name = getattr(camp_game, "name", "") if camp_game else ""
            channel_name = getattr(cur_channel, "name", None) if cur_channel else None

            async with AsyncSessionLocal() as db:
                await log_claimed_drop(
                    db=db,
                    drop_id=drop_id,
                    drop_name=drop_name,
                    campaign_id=camp_id,
                    campaign_name=camp_name,
                    game_id=game_id,
                    game_name=game_name,
                    channel_name=channel_name,
                )
        except Exception as exc:
            logger.error(f"Error logging claimed drop to DB: {exc}")

        await self.broadcast_status()

    async def start(self) -> None:
        """Start DevilXD background mining engine."""
        if self.is_running:
            return

        async with AsyncSessionLocal() as db:
            account = await get_active_twitch_account(db)
            watchlist = await get_watchlist(db)

        if not account:
            self.error_message = "No active Twitch account found. Please login first."
            logger.warning(self.error_message)
            await self.broadcast_status()
            return

        tokens = get_decrypted_tokens(account)
        access_token = tokens.get("access_token")
        if not access_token:
            self.error_message = "No access token found for active Twitch account."
            logger.warning(self.error_message)
            await self.broadcast_status()
            return

        priority_games = [item.game_name for item in watchlist if item.auto_mine and item.is_active]
        logger.info(f"Starting DevilXD engine for @{account.twitch_username} with priority games: {priority_games}")

        # Initialize DevilXD Twitch instance & bridge
        self.twitch, self.bridge = create_devilxd_instance(priority_games)

        # Wire bridge callbacks
        self.bridge.on_status_callback = lambda text: self.broadcast_status()
        self.bridge.on_channel_callback = lambda ch: self.broadcast_status()
        self.bridge.on_drop_callback = lambda d: self.broadcast_status()
        self.bridge.on_claim_callback = self._handle_drop_claimed

        # Pre-seed credentials directly into DevilXD auth state
        import secrets
        self.twitch._auth_state.device_id = secrets.token_hex(16)
        self.twitch._auth_state.session_id = secrets.token_hex(16)
        self.twitch._auth_state.access_token = access_token
        self.twitch._auth_state.user_id = int(account.twitch_user_id)
        self.twitch._auth_state._logged_in.set()

        self.is_running = True
        self.is_paused = False
        self.error_message = None

        # Launch main Twitch run loop
        self._main_task = asyncio.create_task(self._run_wrapper())
        # Launch periodic poll orchestrator
        self._orchestrator_task = asyncio.create_task(self._orchestrator_loop())

        await self.broadcast_status()

    async def _run_wrapper(self) -> None:
        """Wrapper around twitch.run() handling auto-recovery and logging."""
        try:
            if self.twitch:
                await self.twitch.run()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"DevilXD engine run loop encountered error: {exc}", exc_info=True)
            self.error_message = str(exc)
            await self.broadcast_status()

    async def stop(self) -> None:
        """Stop DevilXD mining engine cleanly."""
        self.is_running = False
        self.is_paused = False

        if self.twitch:
            try:
                self.twitch.close()
                await self.twitch.shutdown()
            except Exception as exc:
                logger.debug(f"Twitch shutdown notice: {exc}")
            self.twitch = None
            self.bridge = None

        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass

        if self._orchestrator_task and not self._orchestrator_task.done():
            self._orchestrator_task.cancel()
            try:
                await self._orchestrator_task
            except asyncio.CancelledError:
                pass

        logger.info("DevilXD mining engine stopped.")
        await self.broadcast_status()

    async def pause(self) -> None:
        """Pause mining activity."""
        self.is_paused = True
        if self.twitch:
            self.twitch.stop_watching()
            self.twitch.change_state(State.IDLE)
        logger.info("Mining paused by user.")
        await self.broadcast_status()

    async def resume(self) -> None:
        """Resume mining activity."""
        self.is_paused = False
        if self.twitch:
            self.twitch.change_state(State.INVENTORY_FETCH)
        else:
            await self.start()
        logger.info("Mining resumed by user.")
        await self.broadcast_status()

    async def check_and_mine(self) -> None:
        """Synchronize priority watchlist from DB and trigger inventory / campaign evaluation."""
        if not self.is_running or not self.twitch:
            await self.start()
            return

        async with AsyncSessionLocal() as db:
            watchlist = await get_watchlist(db)

        priority_games = [item.game_name for item in watchlist if item.auto_mine and item.is_active]
        logger.info(f"Syncing priority games with DevilXD engine: {priority_games}")

        self.twitch.settings.priority = priority_games
        self.twitch.change_state(State.INVENTORY_FETCH)
        await self.broadcast_status()

    async def _orchestrator_loop(self) -> None:
        """Periodic background loop triggering inventory refresh to pick up new drops."""
        while self.is_running:
            try:
                poll_interval = settings.POLL_INTERVAL_MINUTES
                self.next_poll_at = datetime.now(timezone.utc) + timedelta(minutes=poll_interval)
                await asyncio.sleep(poll_interval * 60)
                if self.is_running and not self.is_paused:
                    logger.info("Running periodic inventory refresh...")
                    await self.check_and_mine()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in orchestrator loop: {exc}")
                await asyncio.sleep(60)


miner_service = MiningWorker()
