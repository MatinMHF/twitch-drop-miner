"""FastAPI Bridge GUIManager for DevilXD Twitch Drops Miner engine."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable, Set

# Ensure devilxd directory is in sys.path
_current_dir = Path(__file__).resolve().parent
_devilxd_dir = _current_dir / "devilxd"
if str(_devilxd_dir) not in sys.path:
    sys.path.insert(0, str(_devilxd_dir))

from app.core.logging import logger

# Ensure TwitchDrops logger outputs to stdout via the redacting handler
_td_logger = logging.getLogger("TwitchDrops")
_td_logger.setLevel(logging.INFO)
if logger.handlers:
    for h in logger.handlers:
        if h not in _td_logger.handlers:
            _td_logger.addHandler(h)


class DummyButton:
    def config(self, *args, **kwargs):
        pass


class BridgeHelp:
    def __init__(self):
        self._invalidate_button = DummyButton()


class BridgeLogin:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge

    def update(self, *args, **kwargs):
        pass

    def clear(self, *args, **kwargs):
        pass

    async def ask_enter_code(self, uri: Any, code: str):
        logger.info(f"[DEVILXD AUTH REQUIRED] Visit {uri} and enter code: {code}")
        self.bridge.pending_device_auth = {
            "verification_uri": str(uri),
            "user_code": code,
        }

    async def ask_login(self):
        raise RuntimeError("Interactive username/password login not supported in headless mode. Use Device Auth or stored cookie.")


class BridgeStatus:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge
        self.text: str = "Idle"

    def update(self, text: str):
        self.text = text
        self.bridge.status_text = text
        logger.info(f"[DEVILXD STATUS] {text}")
        if self.bridge.on_status_callback:
            try:
                asyncio.create_task(self.bridge.on_status_callback(text))
            except Exception as exc:
                logger.debug(f"Status callback dispatch note: {exc}")


class BridgeProgress:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge

    def minute_almost_done(self) -> bool:
        return False

    def stop_timer(self):
        pass


class BridgeChannels:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge
        self.channels: Dict[int, Any] = {}
        self.watching: Optional[Any] = None

    def display(self, channel: Any, add: bool = False):
        self.channels[channel.id] = channel

    def remove(self, channel: Any):
        self.channels.pop(channel.id, None)

    def set_watching(self, channel: Any):
        self.watching = channel
        self.bridge.current_channel = channel
        game_name = getattr(channel.game, "name", "Unknown") if hasattr(channel, "game") and channel.game else "Unknown"
        logger.info(f"[DEVILXD WATCHING] Streamer: @{channel._login} ({game_name}) | Viewers: {getattr(channel, 'viewers', 0)}")
        if self.bridge.on_channel_callback:
            try:
                asyncio.create_task(self.bridge.on_channel_callback(channel))
            except Exception as exc:
                logger.debug(f"Channel callback dispatch note: {exc}")

    def clear_watching(self):
        self.watching = None
        self.bridge.current_channel = None
        logger.info("[DEVILXD WATCHING] Streamer cleared")
        if self.bridge.on_channel_callback:
            try:
                asyncio.create_task(self.bridge.on_channel_callback(None))
            except Exception as exc:
                logger.debug(f"Channel callback dispatch note: {exc}")

    def clear(self):
        self.channels.clear()

    def get_selection(self) -> Optional[Any]:
        return None


class BridgeInventory:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge
        self.campaigns: Dict[str, Any] = {}
        self.drops: Dict[str, Any] = {}

    async def add_campaign(self, campaign: Any):
        self.campaigns[campaign.id] = campaign

    def update_drop(self, drop: Any):
        self.drops[drop.id] = drop
        if self.bridge.current_drop and self.bridge.current_drop.id == drop.id:
            self.bridge.current_drop = drop
            if self.bridge.on_drop_callback:
                try:
                    asyncio.create_task(self.bridge.on_drop_callback(drop))
                except Exception as exc:
                    logger.debug(f"Drop update callback note: {exc}")

    def clear(self):
        self.campaigns.clear()
        self.drops.clear()


class BridgeTray:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge

    def change_icon(self, *args, **kwargs):
        pass

    def notify(self, title: str, msg: str, *args, **kwargs):
        logger.info(f"🏆 [DEVILXD CLAIM] {title}: {msg}")
        self.bridge.total_claimed += 1
        if self.bridge.on_claim_callback:
            try:
                asyncio.create_task(self.bridge.on_claim_callback(title, msg))
            except Exception as exc:
                logger.debug(f"Claim callback note: {exc}")


class BridgeWebsockets:
    def __init__(self, bridge: "FastAPIBridgeGUIManager"):
        self.bridge = bridge

    def update(self, *args, **kwargs):
        pass

    def remove(self, *args, **kwargs):
        pass


class FastAPIBridgeGUIManager:
    """Headless GUIManager implementation for DevilXD's Twitch engine."""

    def __init__(self, twitch: Any):
        self._twitch = twitch
        self.status = BridgeStatus(self)
        self.progress = BridgeProgress(self)
        self.channels = BridgeChannels(self)
        self.inv = BridgeInventory(self)
        self.tray = BridgeTray(self)
        self.websockets = BridgeWebsockets(self)
        self.help = BridgeHelp()
        self.login = BridgeLogin(self)
        self.close_requested = asyncio.Event()

        # State cache for FastAPI / WebSockets
        self.status_text: str = "Idle"
        self.current_channel: Optional[Any] = None
        self.current_drop: Optional[Any] = None
        self.available_games: Set[Any] = set()
        self.total_claimed: int = 0
        self.last_heartbeat: Optional[datetime] = None
        self.pending_device_auth: Optional[Dict[str, str]] = None

        # Callbacks
        self.on_status_callback: Optional[Callable[[str], Any]] = None
        self.on_channel_callback: Optional[Callable[[Optional[Any]], Any]] = None
        self.on_drop_callback: Optional[Callable[[Any], Any]] = None
        self.on_claim_callback: Optional[Callable[[str, str], Any]] = None

    def print(self, *args, **kwargs):
        msg = " ".join(str(a) for a in args)
        logger.info(f"[DEVILXD] {msg}")

    def display_drop(self, drop: Any, *args, **kwargs):
        self.current_drop = drop
        self.last_heartbeat = datetime.now(timezone.utc)
        logger.info(
            f"[DEVILXD DROP] {drop.name} ({drop.current_minutes}/{drop.required_minutes}m - {drop.progress:.1%})"
        )
        if self.on_drop_callback:
            try:
                asyncio.create_task(self.on_drop_callback(drop))
            except Exception as exc:
                logger.debug(f"Drop callback note: {exc}")

    def clear_drop(self):
        self.current_drop = None
        logger.info("[DEVILXD DROP] Cleared")
        if self.on_drop_callback:
            try:
                asyncio.create_task(self.on_drop_callback(None))
            except Exception as exc:
                logger.debug(f"Drop clear note: {exc}")

    def set_games(self, games: Any):
        self.available_games = set(games)
        logger.info(f"[DEVILXD INVENTORY] Available drop games: {[getattr(g, 'name', str(g)) for g in games]}")

    async def coro_unless_closed(self, coro: Any):
        return await coro

    def start(self):
        pass

    def save(self, *args, **kwargs):
        pass

    def close(self):
        self.close_requested.set()

    def prevent_close(self):
        pass

    async def wait_until_closed(self):
        await self.close_requested.wait()


# Register stub in sys.modules["gui"]
gui_stub = types.ModuleType("gui")
gui_stub.GUIManager = FastAPIBridgeGUIManager
gui_stub.ChannelList = BridgeChannels
sys.modules["gui"] = gui_stub

# Import DevilXD components with stubbed GUI
from twitch import Twitch
from settings import Settings
from constants import PriorityMode, State, JsonType
from channel import Channel, Stream
from inventory import TimedDrop, DropsCampaign


class DummyArgs:
    log = True
    tray = False
    dump = False
    debug_ws = 0
    debug_gql = 0
    logging_level = 2


def create_devilxd_instance(priority_games: List[str]) -> tuple[Twitch, FastAPIBridgeGUIManager]:
    """Factory creating a headless DevilXD Twitch instance wired to FastAPIBridgeGUIManager."""
    settings = Settings(DummyArgs())
    settings.priority = priority_games
    settings.priority_mode = PriorityMode.PRIORITY_ONLY

    twitch = Twitch(settings)
    bridge: FastAPIBridgeGUIManager = twitch.gui
    return twitch, bridge
