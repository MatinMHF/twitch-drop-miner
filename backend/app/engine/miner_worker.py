"""Multi-Account Background Mining Service powered by DevilXD Twitch Drops engine."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.logging import logger
from app.db.database import AsyncSessionLocal
from app.db.repositories import (
    get_all_active_twitch_accounts,
    get_twitch_account_by_id,
    get_decrypted_tokens,
    get_watchlist,
    log_claimed_drop,
)
from app.engine.devilxd_bridge import create_devilxd_instance, FastAPIBridgeGUIManager, Twitch, State


class SingleAccountWorker:
    """Worker managing DevilXD engine lifecycle for a single Twitch account."""

    def __init__(self, account_id: str, twitch_user_id: str, twitch_username: str, on_change_cb: Any):
        self.account_id = account_id
        self.twitch_user_id = twitch_user_id
        self.twitch_username = twitch_username
        self.on_change_cb = on_change_cb

        self.twitch: Optional[Twitch] = None
        self.bridge: Optional[FastAPIBridgeGUIManager] = None
        self.is_running: bool = False
        self.is_paused: bool = False
        self.error_message: Optional[str] = None
        self.next_poll_at: Optional[datetime] = None

        self._main_task: Optional[asyncio.Task] = None
        self._orchestrator_task: Optional[asyncio.Task] = None

    def get_status(self) -> Dict[str, Any]:
        """Return serialized state for this account."""
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
                "drop_name": getattr(cur_drop, "name", ""),
                "required_minutes": req_min,
                "current_minutes": cur_min,
                "progress_percentage": progress_pct,
                "is_claimed": getattr(cur_drop, "is_claimed", False),
            }

        return {
            "account_id": self.account_id,
            "twitch_user_id": self.twitch_user_id,
            "twitch_username": self.twitch_username,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "error_message": self.error_message,
            "status_text": status_text,
            "active_channel": stream_info,
            "active_drop": target_obj,
            "next_poll_at": self.next_poll_at.isoformat() if self.next_poll_at else None,
        }

    async def notify_change(self) -> None:
        if self.on_change_cb:
            try:
                await self.on_change_cb()
            except Exception as exc:
                logger.error(f"Worker state change callback error: {exc}")

    async def _handle_drop_claimed(self, drop: Any) -> None:
        """Invoked when DevilXD successfully claims a drop reward."""
        try:
            camp = getattr(drop, "campaign", None)
            camp_game = getattr(camp, "game", None) if camp else None
            game_id = str(getattr(camp_game, "id", "")) if camp_game else "0"
            game_name = getattr(camp_game, "name", "Unknown Game") if camp_game else "Unknown Game"

            async with AsyncSessionLocal() as db:
                await log_claimed_drop(
                    db=db,
                    drop_id=str(getattr(drop, "id", "")),
                    drop_name=getattr(drop, "name", "Twitch Reward"),
                    campaign_id=str(getattr(camp, "id", "")),
                    campaign_name=getattr(camp, "name", "Drops Campaign"),
                    game_id=game_id,
                    game_name=game_name,
                    channel_name=getattr(self.bridge.current_channel, "name", None) if self.bridge else None,
                )
            logger.info(f"Successfully recorded claimed drop reward: {getattr(drop, 'name', 'Reward')} for @{self.twitch_username}")
        except Exception as exc:
            logger.error(f"Error logging claimed drop to DB: {exc}")

        await self.notify_change()

    async def start(self) -> None:
        """Start DevilXD instance for this account."""
        if self.is_running:
            return

        async with AsyncSessionLocal() as db:
            account = await get_twitch_account_by_id(db, self.account_id)
            watchlist = await get_watchlist(db)

        if not account or not account.is_active:
            self.error_message = f"Account @{self.twitch_username} inactive or missing."
            logger.warning(self.error_message)
            await self.notify_change()
            return

        tokens = get_decrypted_tokens(account)
        access_token = tokens.get("access_token")
        if not access_token:
            self.error_message = f"No access token for @{self.twitch_username}"
            logger.warning(self.error_message)
            await self.notify_change()
            return

        priority_games = [item.game_name for item in watchlist if item.auto_mine and item.is_active]
        logger.info(f"Starting DevilXD engine for @{self.twitch_username} with priority games: {priority_games}")

        # Initialize DevilXD instance with per-account cookie jar
        self.twitch, self.bridge = create_devilxd_instance(priority_games, user_id=self.twitch_user_id)

        # Wire bridge callbacks
        self.bridge.on_status_callback = lambda text: asyncio.create_task(self.notify_change())
        self.bridge.on_channel_callback = lambda ch: asyncio.create_task(self.notify_change())
        self.bridge.on_drop_callback = lambda d: asyncio.create_task(self.notify_change())
        self.bridge.on_claim_callback = self._handle_drop_claimed

        # Pre-seed credentials
        self.twitch._auth_state.device_id = secrets.token_hex(16)
        self.twitch._auth_state.session_id = secrets.token_hex(16)
        self.twitch._auth_state.access_token = access_token
        self.twitch._auth_state.user_id = int(self.twitch_user_id)
        self.twitch._auth_state._logged_in.set()

        self.is_running = True
        self.is_paused = False
        self.error_message = None

        self._main_task = asyncio.create_task(self._run_wrapper())
        self._orchestrator_task = asyncio.create_task(self._orchestrator_loop())

        await self.notify_change()

    async def _run_wrapper(self) -> None:
        try:
            if self.twitch:
                await self.twitch.run()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"DevilXD engine run loop for @{self.twitch_username} error: {exc}", exc_info=True)
            self.error_message = str(exc)
            await self.notify_change()

    async def stop(self) -> None:
        self.is_running = False
        self.is_paused = False

        if self.twitch:
            try:
                self.twitch.close()
                await self.twitch.shutdown()
            except Exception as exc:
                logger.debug(f"Twitch shutdown notice for @{self.twitch_username}: {exc}")
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

        logger.info(f"DevilXD engine for @{self.twitch_username} stopped.")
        await self.notify_change()

    async def pause(self) -> None:
        self.is_paused = True
        if self.twitch:
            self.twitch.stop_watching()
            self.twitch.change_state(State.IDLE)
        await self.notify_change()

    async def resume(self) -> None:
        self.is_paused = False
        if self.twitch:
            self.twitch.change_state(State.INVENTORY_FETCH)
        else:
            await self.start()
        await self.notify_change()

    async def sync_watchlist(self, priority_games: List[str]) -> None:
        if self.twitch and self.is_running:
            self.twitch.settings.priority = priority_games
            self.twitch.change_state(State.INVENTORY_FETCH)
            await self.notify_change()

    async def _orchestrator_loop(self) -> None:
        while self.is_running:
            try:
                poll_interval = settings.POLL_INTERVAL_MINUTES
                self.next_poll_at = datetime.now(timezone.utc) + timedelta(minutes=poll_interval)
                await asyncio.sleep(poll_interval * 60)
                if self.is_running and not self.is_paused and self.twitch:
                    async with AsyncSessionLocal() as db:
                        watchlist = await get_watchlist(db)
                    priority_games = [item.game_name for item in watchlist if item.auto_mine and item.is_active]
                    await self.sync_watchlist(priority_games)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in orchestrator loop for @{self.twitch_username}: {exc}")
                await asyncio.sleep(60)


class MultiAccountMiningManager:
    """Master Coordinator running concurrent mining workers for all active Twitch accounts."""

    def __init__(self):
        self.workers: Dict[str, SingleAccountWorker] = {}
        self._ws_broadcast_callback: Optional[Any] = None

    @property
    def twitch(self) -> Optional[Twitch]:
        """Backwards compatibility for single-instance endpoints (e.g. inventory inspector)."""
        if not self.workers:
            return None
        # Return first available worker's Twitch instance
        for w in self.workers.values():
            if w.twitch:
                return w.twitch
        return None

    def register_ws_broadcaster(self, callback: Any) -> None:
        self._ws_broadcast_callback = callback

    async def broadcast_status(self) -> None:
        if self._ws_broadcast_callback:
            try:
                await self._ws_broadcast_callback(self.get_status())
            except Exception as exc:
                logger.error(f"Failed to broadcast multi-account status: {exc}")

    def get_status(self) -> Dict[str, Any]:
        """Aggregate status across all active accounts with backwards compatibility."""
        accounts_status = [w.get_status() for w in self.workers.values()]

        # Primary account (first active worker) for legacy single-account consumers
        primary = accounts_status[0] if accounts_status else {}

        any_running = any(w.is_running for w in self.workers.values())
        all_paused = all(w.is_paused for w in self.workers.values()) if self.workers else False

        return {
            "is_running": any_running,
            "is_paused": all_paused,
            "error_message": primary.get("error_message"),
            "status_text": primary.get("status_text", "Idle"),
            "active_channel": primary.get("active_channel"),
            "active_drop": primary.get("active_drop"),
            "next_poll_at": primary.get("next_poll_at"),
            "accounts_count": len(accounts_status),
            "accounts": accounts_status,
        }

    async def start(self) -> None:
        """Load all active Twitch accounts and start mining workers in parallel."""
        async with AsyncSessionLocal() as db:
            accounts = await get_all_active_twitch_accounts(db)

        if not accounts:
            logger.warning("MultiAccountMiningManager: No active Twitch accounts configured.")
            await self.broadcast_status()
            return

        for acc in accounts:
            if acc.id not in self.workers:
                worker = SingleAccountWorker(
                    account_id=acc.id,
                    twitch_user_id=acc.twitch_user_id,
                    twitch_username=acc.twitch_username,
                    on_change_cb=self.broadcast_status,
                )
                self.workers[acc.id] = worker
                asyncio.create_task(worker.start())

        await self.broadcast_status()

    async def stop(self, account_id: Optional[str] = None) -> None:
        """Stop one or all mining workers."""
        if account_id:
            worker = self.workers.pop(account_id, None)
            if worker:
                await worker.stop()
        else:
            tasks = [w.stop() for w in self.workers.values()]
            self.workers.clear()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        await self.broadcast_status()

    async def pause(self, account_id: Optional[str] = None) -> None:
        if account_id and account_id in self.workers:
            await self.workers[account_id].pause()
        else:
            for w in self.workers.values():
                await w.pause()
        await self.broadcast_status()

    async def resume(self, account_id: Optional[str] = None) -> None:
        if account_id and account_id in self.workers:
            await self.workers[account_id].resume()
        else:
            if not self.workers:
                await self.start()
            else:
                for w in self.workers.values():
                    await w.resume()
        await self.broadcast_status()

    async def check_and_mine(self) -> None:
        """Sync active accounts and watchlists across all running workers."""
        async with AsyncSessionLocal() as db:
            active_accounts = await get_all_active_twitch_accounts(db)
            watchlist = await get_watchlist(db)

        priority_games = [item.game_name for item in watchlist if item.auto_mine and item.is_active]
        active_ids = {a.id for a in active_accounts}

        # Stop workers for removed accounts
        removed_ids = set(self.workers.keys()) - active_ids
        for rid in removed_ids:
            w = self.workers.pop(rid, None)
            if w:
                await w.stop()

        # Start workers for newly added accounts
        for acc in active_accounts:
            if acc.id not in self.workers:
                worker = SingleAccountWorker(
                    account_id=acc.id,
                    twitch_user_id=acc.twitch_user_id,
                    twitch_username=acc.twitch_username,
                    on_change_cb=self.broadcast_status,
                )
                self.workers[acc.id] = worker
                asyncio.create_task(worker.start())
            else:
                asyncio.create_task(self.workers[acc.id].sync_watchlist(priority_games))

        await self.broadcast_status()


miner_service = MultiAccountMiningManager()
