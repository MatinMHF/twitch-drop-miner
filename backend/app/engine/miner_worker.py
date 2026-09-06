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
from app.engine.pubsub_client import TwitchPubSubClient
from app.engine.stream_watcher import StreamWatcher


class MiningWorker:
    """Master Background Miner Engine with Multi-Stream concurrent drop support."""

    def __init__(self):
        self.state: str = "IDLE"  # "IDLE", "MINING", "PAUSED", "ERROR", "NO_ACCOUNT"
        self.active_targets: Dict[str, Dict[str, Any]] = {}  # campaign_id -> target dict
        self.stream_watchers: Dict[str, StreamWatcher] = {}  # campaign_id -> StreamWatcher
        self.drop_manager: Optional[DropManager] = None
        self.pubsub_client: Optional[TwitchPubSubClient] = None
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
        active_targets_list: List[Dict[str, Any]] = []

        for cid, target in self.active_targets.items():
            cur_min = target.get("current_minutes", 0)
            req_min = target.get("required_minutes", 0)
            progress_pct = min(round((cur_min / req_min) * 100, 2), 100.0) if req_min > 0 else 0.0

            ch = target.get("channel") or {}
            active_targets_list.append({
                "game_id": target.get("game_id"),
                "game_name": target.get("game_name"),
                "campaign_id": cid,
                "campaign_name": target.get("campaign_name"),
                "drop_id": target.get("drop_id"),
                "drop_instance_id": target.get("drop_instance_id"),
                "drop_name": target.get("drop_name"),
                "required_minutes": req_min,
                "current_minutes": cur_min,
                "progress_percent": progress_pct,
                "channel": {
                    "channel_id": ch.get("channel_id"),
                    "channel_login": ch.get("channel_login"),
                    "channel_display_name": ch.get("channel_display_name"),
                    "title": ch.get("title"),
                    "viewers_count": ch.get("viewers_count", 0),
                    "game_name": ch.get("game_name"),
                    "is_live": ch.get("is_live", True),
                    "stream_id": ch.get("stream_id"),
                } if ch else None,
            })

        # Primary target for backward compatibility
        primary = active_targets_list[0] if active_targets_list else None

        return {
            "state": self.state,
            "active_targets": active_targets_list,
            "active_game_id": primary["game_id"] if primary else None,
            "active_game_name": primary["game_name"] if primary else None,
            "active_campaign_id": primary["campaign_id"] if primary else None,
            "active_campaign_name": primary["campaign_name"] if primary else None,
            "active_channel": primary["channel"] if primary else None,
            "current_drop_id": primary["drop_id"] if primary else None,
            "current_drop_name": primary["drop_name"] if primary else None,
            "current_drop_progress_percent": primary["progress_percent"] if primary else 0.0,
            "current_drop_minutes_watched": primary["current_minutes"] if primary else 0,
            "current_drop_required_minutes": primary["required_minutes"] if primary else 0,
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
        logger.info("Initializing Twitch Multi-Stream Drop Mining Engine...")
        self._main_task = asyncio.create_task(self._orchestrator_loop())

    async def stop(self) -> None:
        """Stop miner engine and close all active watchers and PubSub."""
        self._is_running = False
        for watcher in list(self.stream_watchers.values()):
            await watcher.stop()
        self.stream_watchers.clear()
        self.active_targets.clear()

        if self.pubsub_client:
            await self.pubsub_client.stop()
            self.pubsub_client = None
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
        logger.info("Twitch Drop Mining Engine stopped.")
        await self.broadcast_status()

    async def pause(self) -> None:
        """Pause mining activity."""
        self.is_paused = True
        self.state = "PAUSED"
        for watcher in list(self.stream_watchers.values()):
            await watcher.stop()
        self.stream_watchers.clear()
        logger.info("Mining paused by user.")
        await self.broadcast_status()

    async def resume(self) -> None:
        """Resume mining activity."""
        self.is_paused = False
        self.state = "IDLE"
        logger.info("Mining resumed by user.")
        await self.broadcast_status()
        await self.check_and_mine()

    async def _handle_pubsub_drop_progress(self, data: Dict[str, Any]) -> None:
        """Real-time drop progress callback from Twitch PubSub."""
        drop_id = data.get("drop_id")
        cur = data.get("current_progress_min")
        req = data.get("required_progress_min")

        for cid, target in self.active_targets.items():
            if not drop_id or target.get("drop_id") == drop_id or target.get("drop_instance_id") == drop_id:
                if cur is not None:
                    target["current_minutes"] = cur
                if req is not None and req > 0:
                    target["required_minutes"] = req
                watcher = self.stream_watchers.get(cid)
                if watcher:
                    watcher.minutes_watched_in_session = 0
                logger.info(f"PubSub progress update for '{target.get('drop_name')}': {cur}/{req}m")
                await self.broadcast_status()
                break

    async def _handle_pubsub_drop_claim(self, data: Dict[str, Any]) -> None:
        """Real-time drop claim callback from Twitch PubSub."""
        logger.info(f"⚡ Instant PubSub claim event triggered for {data.get('drop_name', 'Drop')}")
        drop_instance_id = data.get("drop_instance_id") or data.get("drop_id")

        if self.drop_manager and drop_instance_id:
            # Find matching target or claim with available data
            matching_target = None
            for target in self.active_targets.values():
                if target.get("drop_id") == drop_instance_id or target.get("drop_instance_id") == drop_instance_id:
                    matching_target = target
                    break

            claimed = await self.drop_manager.claim_drop_reward(
                drop_id=drop_instance_id,
                drop_name=data.get("drop_name", matching_target.get("drop_name", "Drop") if matching_target else "Drop"),
                campaign_id=matching_target.get("campaign_id", "") if matching_target else "",
                campaign_name=matching_target.get("campaign_name", "") if matching_target else "",
                game_id=matching_target.get("game_id", "") if matching_target else "",
                game_name=matching_target.get("game_name", "") if matching_target else "",
                channel_name=matching_target.get("channel", {}).get("channel_display_name") if matching_target else None,
            )
            if claimed:
                self.total_drops_claimed_session += 1
                await self.check_and_mine()

    async def check_and_mine(self) -> None:
        """Evaluate targets across watchlist and maintain concurrent stream watchers."""
        if self.is_paused:
            return

        async with AsyncSessionLocal() as db:
            account = await get_active_twitch_account(db)

        if not account:
            self.state = "NO_ACCOUNT"
            for watcher in list(self.stream_watchers.values()):
                await watcher.stop()
            self.stream_watchers.clear()
            self.active_targets.clear()
            if self.pubsub_client:
                await self.pubsub_client.stop()
                self.pubsub_client = None
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

        # Setup PubSub real-time event listener
        if not self.pubsub_client:
            self.pubsub_client = TwitchPubSubClient(
                oauth_token=access_token,
                twitch_user_id=account.twitch_user_id,
                on_drop_progress=self._handle_pubsub_drop_progress,
                on_drop_claim=self._handle_pubsub_drop_claim,
            )
            await self.pubsub_client.start()

        try:
            # Query active targets (single stream focus matching Twitch drop credit rules)
            targets = await self.drop_manager.select_all_active_targets(max_concurrent=1)
            new_target_map = {t["campaign_id"]: t for t in targets}

            # 1. Stop watchers for campaigns no longer present in active targets
            for old_cid in list(self.stream_watchers.keys()):
                if old_cid not in new_target_map:
                    logger.info(f"Stopping watcher for finished/inactive campaign '{old_cid}'")
                    await self.stream_watchers[old_cid].stop()
                    del self.stream_watchers[old_cid]
                    self.active_targets.pop(old_cid, None)

            # 2. Launch or update watchers for new/current active targets
            for cid, target in new_target_map.items():
                ch_info = target["channel"]
                new_login = ch_info.get("channel_login", "")

                if cid in self.stream_watchers:
                    existing_watcher = self.stream_watchers[cid]
                    if existing_watcher.channel_login.lower() != new_login.lower():
                        logger.info(f"Switching streamer for campaign '{cid}' to @{new_login}")
                        await existing_watcher.stop()
                        watcher = StreamWatcher(
                            oauth_token=access_token,
                            twitch_user_id=account.twitch_user_id,
                            channel_id=ch_info["channel_id"],
                            channel_login=ch_info["channel_login"],
                            channel_display_name=ch_info["channel_display_name"],
                            game_name=target["game_name"],
                            game_id=target.get("game_id"),
                            stream_id=ch_info.get("stream_id"),
                            on_channel_offline=lambda cid=cid: self._handle_channel_offline(cid),
                            on_minute_heartbeat=lambda mins, cid=cid: self._handle_minute_heartbeat(cid, mins),
                        )
                        await watcher.start()
                        self.stream_watchers[cid] = watcher
                    if cid in self.active_targets:
                        old_target = self.active_targets[cid]
                        old_mins = old_target.get("current_minutes", 0)
                        if old_mins > target.get("current_minutes", 0):
                            target["current_minutes"] = old_mins
                            target["baseline_minutes"] = old_target.get("baseline_minutes", target["current_minutes"])
                            target["extra_minutes"] = old_target.get("extra_minutes", 0)
                            req = target.get("required_minutes", 1)
                            target["progress_percent"] = round((old_mins / max(req, 1)) * 100, 1)
                    self.active_targets[cid] = target
                else:
                    logger.info(
                        f"🚀 Launching concurrent StreamWatcher for '{target['drop_name']}' ({target['game_name']}) on @{new_login}"
                    )
                    watcher = StreamWatcher(
                        oauth_token=access_token,
                        twitch_user_id=account.twitch_user_id,
                        channel_id=ch_info["channel_id"],
                        channel_login=ch_info["channel_login"],
                        channel_display_name=ch_info["channel_display_name"],
                        game_name=target["game_name"],
                        game_id=target.get("game_id"),
                        stream_id=ch_info.get("stream_id"),
                        on_channel_offline=lambda cid=cid: self._handle_channel_offline(cid),
                        on_minute_heartbeat=lambda mins, cid=cid: self._handle_minute_heartbeat(cid, mins),
                    )
                    await watcher.start()
                    self.stream_watchers[cid] = watcher
                    self.active_targets[cid] = target

            self.state = "MINING" if len(self.stream_watchers) > 0 else "IDLE"
            self.error_message = None
            await self.broadcast_status()

        except Exception as exc:
            logger.error(f"Error during check_and_mine: {exc}")
            self.state = "ERROR"
            self.error_message = str(exc)
            await self.broadcast_status()

    async def _handle_minute_heartbeat(self, campaign_id: str, minutes_in_session: int) -> None:
        """Callback invoked when a minute watched heartbeat completes for a campaign."""
        self.last_heartbeat_at = datetime.now(timezone.utc)
        target = self.active_targets.get(campaign_id)

        if target:
            if "baseline_minutes" not in target:
                target["baseline_minutes"] = target.get("current_minutes", 0)
                target["extra_minutes"] = 0

            # Progressively advance local session minute
            target["extra_minutes"] = target.get("extra_minutes", 0) + 1

            # Query verified drop progress from Twitch
            if self.drop_manager:
                try:
                    ch_id = target.get("channel", {}).get("channel_id")
                    ch_login = target.get("channel", {}).get("channel_login", "")

                    if ch_id and ch_login:
                        ctx = await self.drop_manager.gql_client.execute_query(
                            "DropCurrentSessionContext",
                            {"channelID": str(ch_id), "channelLogin": ch_login}
                        )
                        drop_data = (ctx.get("currentUser") or {}).get("dropCurrentSession")
                        if drop_data and drop_data.get("dropID") == target.get("drop_id"):
                            twitch_mins = drop_data.get("currentMinutesWatched")
                            if twitch_mins is not None and twitch_mins > target.get("baseline_minutes", 0):
                                target["baseline_minutes"] = twitch_mins
                                target["extra_minutes"] = 0
                                req_t = drop_data.get("requiredMinutesWatched")
                                if req_t:
                                    target["required_minutes"] = req_t
                except Exception as exc:
                    logger.debug(f"Progress sync notice: {exc}")

            # Reconcile total current minutes (cap optimistic advance to +3m ahead of Twitch confirmed baseline)
            req = target.get("required_minutes", 1)
            bounded_extra = min(target.get("extra_minutes", 0), 3)
            tot_mins = min(target.get("baseline_minutes", 0) + bounded_extra, req)
            target["current_minutes"] = tot_mins
            target["progress_percent"] = round((tot_mins / max(req, 1)) * 100, 1)

            # Check if Twitch-confirmed baseline reached 100% or total reached 100%
            if tot_mins >= req and req > 0:
                logger.info(f"Drop '{target['drop_name']}' watch requirement reached ({tot_mins}/{req}m). Attempting claim...")
                if self.drop_manager:
                    claimed = await self.drop_manager.claim_drop_reward(
                        drop_id=target["drop_id"],
                        drop_name=target["drop_name"],
                        campaign_id=target["campaign_id"],
                        campaign_name=target["campaign_name"],
                        game_id=target["game_id"],
                        game_name=target["game_name"],
                        channel_name=target.get("channel", {}).get("channel_display_name"),
                    )
                    if claimed:
                        self.total_drops_claimed_session += 1
                        logger.info(f"Drop '{target['drop_name']}' successfully claimed. Re-evaluating next target...")
                        await self.check_and_mine()
                        return
                    else:
                        logger.debug(f"Drop '{target['drop_name']}' not yet confirmed claimable by Twitch edge; continuing watch.")

        await self.broadcast_status()

    async def _handle_channel_offline(self, campaign_id: str) -> None:
        """Failover triggered when a streamer goes offline for a campaign."""
        logger.info(f"Streamer offline on campaign '{campaign_id}'. Initiating failover...")
        if campaign_id in self.stream_watchers:
            await self.stream_watchers[campaign_id].stop()
            del self.stream_watchers[campaign_id]
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
