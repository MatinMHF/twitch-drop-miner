"""Tests for DevilXD fake progress prevention and strict AvailableDrops verification."""

import sys
from pathlib import Path

# Ensure devilxd directory is in sys.path before importing devilxd modules
_devilxd_dir = Path(__file__).resolve().parent.parent / "app" / "engine" / "devilxd"
if _devilxd_dir.is_dir() and str(_devilxd_dir) not in sys.path:
    sys.path.insert(0, str(_devilxd_dir))

import pytest
from datetime import datetime, timezone, timedelta
from app.engine.devilxd.inventory import TimedDrop, DropsCampaign
from app.engine.devilxd.channel import Channel, Stream
from app.engine.devilxd.utils import Game


class DummySettings:
    def __init__(self, available_drops_check: bool = True):
        self.available_drops_check = available_drops_check
        self.enable_badges_emotes = False


class DummyTwitch:
    def __init__(self, available_drops_check: bool = True):
        self.settings = DummySettings(available_drops_check)
        self._auth_state = type("AuthState", (), {"user_id": 12345, "access_token": "token"})()
        self.gui = type("GUI", (), {
            "channels": type("ChGUI", (), {"display": lambda *a, **k: None, "remove": lambda *a, **k: None})(),
            "inv": type("InvGUI", (), {"update_drop": lambda *a, **k: None, "clear": lambda *a, **k: None})(),
            "tray": type("TrayGUI", (), {"notify": lambda *a, **k: None})(),
            "display_drop": lambda *a, **k: None,
        })()
        self._campaigns = {}
        self.wanted_games = []

    def print(self, *args, **kwargs):
        pass


def test_no_fake_progress_on_bump_minutes():
    """Verify _bump_minutes does NOT artificially inflate current_minutes or progress."""
    twitch = DummyTwitch()
    now = datetime.now(timezone.utc)
    game_data = {"id": "263497", "displayName": "Rust", "name": "Rust", "boxArtURL": "https://example.com/art-100x100.jpg"}
    campaign_data = {
        "id": "rust_camp_1",
        "name": "Rust Drops Campaign",
        "game": game_data,
        "self": {"isAccountConnected": True},
        "accountLinkURL": "https://example.com",
        "startAt": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endAt": (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ACTIVE",
        "allow": {"channels": [], "isEnabled": True},
        "timeBasedDrops": [
            {
                "id": "drop_1",
                "name": "Rust Hoodie",
                "requiredMinutesWatched": 60,
                "benefitEdges": [
                    {
                        "benefit": {
                            "id": "ben_1",
                            "name": "Rust Hoodie",
                            "distributionType": "DIRECT_ENTITLEMENT",
                            "imageAssetURL": "https://example.com/item.png",
                        }
                    }
                ],
                "startAt": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endAt": (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "preconditionDrops": [],
                "self": {"currentMinutesWatched": 0, "dropInstanceID": None, "isClaimed": False},
            }
        ],
    }

    campaign = DropsCampaign(twitch, campaign_data, {})
    drop = campaign.timed_drops["drop_1"]

    assert drop.real_current_minutes == 0
    assert drop.current_minutes == 0
    assert drop.progress == 0.0

    # Simulate 8 lagged minute ticks
    for _ in range(8):
        drop._bump_minutes(None)

    # Watchdog tracked the 8 uncredited minutes
    assert drop.extra_current_minutes == 8
    # BUT current_minutes and progress MUST remain strictly 0 (verified minutes only)
    assert drop.current_minutes == 0
    assert drop.progress == 0.0
    assert "0/60" in repr(drop) or "Drop(Rust Hoodie" in repr(drop)


def test_stream_drops_enabled_defaults_by_setting():
    """Verify Stream.drops_enabled defaults to False if available_drops_check is True."""
    twitch_strict = DummyTwitch(available_drops_check=True)
    ch_strict = Channel(twitch_strict, id=1001, login="streamer_strict")
    stream_strict = Stream(ch_strict, id=9001, game={"id": "263497", "name": "Rust"}, viewers=500, title="Rust Stream")
    assert stream_strict.drops_enabled is False

    twitch_lenient = DummyTwitch(available_drops_check=False)
    ch_lenient = Channel(twitch_lenient, id=1002, login="streamer_lenient")
    stream_lenient = Stream(ch_lenient, id=9002, game={"id": "263497", "name": "Rust"}, viewers=500, title="Rust Stream")
    assert stream_lenient.drops_enabled is True


def test_check_drops_enabled_rejects_sitewide_and_accepts_target_game():
    """Verify channels with only sitewide drops (Apple TV) are False, while target game drops are True."""
    twitch = DummyTwitch(available_drops_check=True)
    now = datetime.now(timezone.utc)

    # 1. Sitewide drop: Apple TV (special events game ID 509663)
    apple_tv_campaign_data = {
        "id": "apple_tv_promo",
        "name": "1 Month of Apple TV",
        "game": {"id": "509663", "displayName": "Special Events", "name": "Special Events", "boxArtURL": "https://example.com/apple-100x100.jpg"},
        "self": {"isAccountConnected": True},
        "accountLinkURL": "https://example.com",
        "startAt": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endAt": (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ACTIVE",
        "allow": {"channels": [], "isEnabled": True},
        "timeBasedDrops": [
            {
                "id": "apple_drop_1",
                "name": "Apple TV Sub",
                "requiredMinutesWatched": 15,
                "benefitEdges": [
                    {
                        "benefit": {
                            "id": "ben_apple",
                            "name": "Apple TV Sub",
                            "distributionType": "DIRECT_ENTITLEMENT",
                            "imageAssetURL": "https://example.com/apple.png",
                        }
                    }
                ],
                "startAt": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endAt": (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "preconditionDrops": [],
                "self": {"currentMinutesWatched": 0, "dropInstanceID": None, "isClaimed": False},
            }
        ],
    }
    apple_tv_campaign = DropsCampaign(twitch, apple_tv_campaign_data, {})

    # 2. Genuine game drop: Rust
    rust_campaign_data = {
        "id": "rust_round_30",
        "name": "Rust General Drops",
        "game": {"id": "263497", "displayName": "Rust", "name": "Rust", "boxArtURL": "https://example.com/rust-100x100.jpg"},
        "self": {"isAccountConnected": True},
        "accountLinkURL": "https://example.com",
        "startAt": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endAt": (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ACTIVE",
        "allow": {"channels": [], "isEnabled": True},
        "timeBasedDrops": [
            {
                "id": "rust_drop_1",
                "name": "Assault Rifle Skin",
                "requiredMinutesWatched": 120,
                "benefitEdges": [
                    {
                        "benefit": {
                            "id": "ben_rust_1",
                            "name": "Assault Rifle Skin",
                            "distributionType": "DIRECT_ENTITLEMENT",
                            "imageAssetURL": "https://example.com/rust_ar.png",
                        }
                    }
                ],
                "startAt": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endAt": (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "preconditionDrops": [],
                "self": {"currentMinutesWatched": 0, "dropInstanceID": None, "isClaimed": False},
            }
        ],
    }
    rust_campaign = DropsCampaign(twitch, rust_campaign_data, {})

    twitch._campaigns["apple_tv_promo"] = apple_tv_campaign
    twitch._campaigns["rust_round_30"] = rust_campaign
    twitch.wanted_games = [Game({"id": "263497", "name": "Rust"})]

    # Streamer @Krolay playing Rust, but ONLY has Apple TV promo in AvailableDrops
    krolay_ch = Channel(twitch, id=2001, login="krolay")
    krolay_stream = Stream(krolay_ch, id=5001, game={"id": "263497", "name": "Rust"}, viewers=10000, title="Rust chill")
    krolay_drops = [{"id": "apple_tv_promo", "name": "1 Month of Apple TV"}]

    assert krolay_ch._check_drops_enabled(krolay_drops, stream=krolay_stream) is False

    # Streamer @psihopattrd playing Rust, HAS genuine Rust drops campaign
    psihopattrd_ch = Channel(twitch, id=2002, login="psihopattrd")
    psihopattrd_stream = Stream(psihopattrd_ch, id=5002, game={"id": "263497", "name": "Rust"}, viewers=800, title="Rust drops on")
    psihopattrd_drops = [
        {"id": "apple_tv_promo", "name": "1 Month of Apple TV"},
        {"id": "rust_round_30", "name": "Rust General Drops"},
    ]

    assert psihopattrd_ch._check_drops_enabled(psihopattrd_drops, stream=psihopattrd_stream) is True


def test_from_directory_available_drops_evaluation():
    """Verify Stream.from_directory properly checks available_drops."""
    twitch = DummyTwitch(available_drops_check=True)
    now = datetime.now(timezone.utc)

    rust_campaign_data = {
        "id": "rust_active",
        "name": "Rust Drops",
        "game": {"id": "263497", "name": "Rust", "boxArtURL": "https://example.com/rust-100x100.jpg"},
        "self": {"isAccountConnected": True},
        "accountLinkURL": "https://example.com",
        "startAt": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endAt": (now + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ACTIVE",
        "allow": {"channels": [], "isEnabled": True},
        "timeBasedDrops": [
            {
                "id": "d1",
                "name": "Box Skin",
                "requiredMinutesWatched": 60,
                "benefitEdges": [
                    {
                        "benefit": {
                            "id": "ben_box",
                            "name": "Box Skin",
                            "distributionType": "DIRECT_ENTITLEMENT",
                            "imageAssetURL": "https://example.com/box.png",
                        }
                    }
                ],
                "startAt": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endAt": (now + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "preconditionDrops": [],
                "self": {"currentMinutesWatched": 0, "dropInstanceID": None, "isClaimed": False},
            }
        ],
    }
    twitch._campaigns["rust_active"] = DropsCampaign(twitch, rust_campaign_data, {})
    twitch.wanted_games = [Game({"id": "263497", "name": "Rust"})]

    channel_data_krolay = {
        "id": "6001",
        "game": {"id": "263497", "name": "Rust"},
        "viewersCount": 9999,
        "title": "Rust Big Stream",
        "broadcaster": {"id": "3001", "login": "krolay", "displayName": "Krolay"},
    }
    # No genuine drops passed
    ch1 = Channel.from_directory(
        twitch,
        channel_data_krolay,
        drops_enabled=True,
        available_drops=[{"id": "non_existent_or_sitewide"}],
    )
    assert ch1.drops_enabled is False

    # Genuine drops passed
    channel_data_psiho = {
        "id": "6002",
        "game": {"id": "263497", "name": "Rust"},
        "viewersCount": 1200,
        "title": "Rust drops here",
        "broadcaster": {"id": "3002", "login": "psihopattrd", "displayName": "PsihopatTRD"},
    }
    ch2 = Channel.from_directory(
        twitch,
        channel_data_psiho,
        drops_enabled=True,
        available_drops=[{"id": "rust_active"}],
    )
    assert ch2.drops_enabled is True
