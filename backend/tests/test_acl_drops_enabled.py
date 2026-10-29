"""Tests verifying ACL channels retain drops_enabled=True regardless of AvailableDrops GQL response."""

from datetime import datetime, timezone, timedelta
import pytest

# Ensure gui stub is registered before importing devilxd modules
import app.engine.devilxd_bridge
from app.engine.devilxd.channel import Channel, Stream
from app.engine.devilxd.inventory import DropsCampaign
from app.engine.devilxd.twitch import Twitch
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
        self.inventory: list[DropsCampaign] = []
        self.wanted_games: list[Game] = []

    def print(self, *args, **kwargs):
        pass

    # Bind the genuine Twitch can_watch method
    can_watch = Twitch.can_watch


def create_r6_acl_campaign(twitch: DummyTwitch, acl_channel_data: list[dict]) -> DropsCampaign:
    now = datetime.now(timezone.utc)
    campaign_data = {
        "id": "r6_doktors_curse_26",
        "name": "Doktor's Curse 26",
        "game": {
            "id": "460630",
            "displayName": "Tom Clancy's Rainbow Six Siege",
            "name": "Tom Clancy's Rainbow Six Siege",
            "boxArtURL": "https://example.com/r6.jpg",
        },
        "self": {"isAccountConnected": True},
        "accountLinkURL": "https://example.com",
        "startAt": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endAt": (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ACTIVE",
        "allow": {
            "channels": acl_channel_data,
            "isEnabled": True,
        },
        "timeBasedDrops": [
            {
                "id": "r6_pack_1",
                "name": "Doktor's Curse Pack",
                "requiredMinutesWatched": 120,
                "benefitEdges": [
                    {
                        "benefit": {
                            "id": "ben_r6_1",
                            "name": "Doktor's Curse Pack",
                            "distributionType": "DIRECT_ENTITLEMENT",
                            "imageAssetURL": "https://example.com/pack.png",
                        }
                    }
                ],
                "startAt": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endAt": (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "preconditionDrops": [],
                "self": {"currentMinutesWatched": 0, "dropInstanceID": None, "isClaimed": False},
            }
        ],
    }
    return DropsCampaign(twitch, campaign_data, {})


def create_apple_tv_campaign(twitch: DummyTwitch) -> DropsCampaign:
    now = datetime.now(timezone.utc)
    campaign_data = {
        "id": "apple_tv_promo",
        "name": "1 Month of Apple TV",
        "game": {
            "id": "509663",
            "displayName": "Special Events",
            "name": "Special Events",
            "boxArtURL": "https://example.com/apple.jpg",
        },
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
    return DropsCampaign(twitch, campaign_data, {})


def test_acl_channel_retains_drops_enabled_when_available_drops_only_has_apple_tv():
    """An ACL channel whose AvailableDrops GQL only returns Apple TV must retain drops_enabled=True."""
    twitch = DummyTwitch(available_drops_check=True)
    apple_tv = create_apple_tv_campaign(twitch)
    r6_camp = create_r6_acl_campaign(
        twitch,
        [
            {"id": "1001", "name": "itsspoit", "displayName": "itsspoit"},
            {"id": "1002", "name": "varsitygaming", "displayName": "VarsityGaming"},
        ],
    )
    twitch._campaigns["apple_tv_promo"] = apple_tv
    twitch._campaigns["r6_doktors_curse_26"] = r6_camp
    twitch.inventory = [apple_tv, r6_camp]
    r6_game = Game({"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"})
    twitch.wanted_games = [r6_game]

    # Pick itsspoit from the ACL campaign's allowed channels
    spoit_channel = r6_camp.allowed_channels[0]
    assert spoit_channel.acl_based is True
    assert spoit_channel.id == 1001

    # Simulate external_update with stream playing Rainbow Six Siege
    channel_data = {
        "id": "1001",
        "displayName": "itsspoit",
        "stream": {
            "id": "900100",
            "viewersCount": 3500,
        },
        "broadcastSettings": {
            "game": {"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"},
            "title": "Doktor's Curse drops active | !drops",
        },
    }

    # AvailableDrops GQL response only returns Apple TV
    apple_tv_only_drops = [{"id": "apple_tv_promo", "name": "1 Month of Apple TV"}]

    spoit_channel.external_update(channel_data, apple_tv_only_drops)

    # The stream drops_enabled and channel.drops_enabled MUST remain True
    assert spoit_channel.drops_enabled is True
    assert spoit_channel._stream.drops_enabled is True


def test_can_watch_returns_true_for_acl_channel_with_apple_tv_available_drops():
    """can_watch must return True for an ACL channel even if AvailableDrops only returned Apple TV."""
    twitch = DummyTwitch(available_drops_check=True)
    apple_tv = create_apple_tv_campaign(twitch)
    r6_camp = create_r6_acl_campaign(
        twitch,
        [{"id": "1002", "name": "varsitygaming", "displayName": "VarsityGaming"}],
    )
    twitch._campaigns["apple_tv_promo"] = apple_tv
    twitch._campaigns["r6_doktors_curse_26"] = r6_camp
    twitch.inventory = [apple_tv, r6_camp]
    r6_game = Game({"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"})
    twitch.wanted_games = [r6_game]

    varsity_channel = r6_camp.allowed_channels[0]
    channel_data = {
        "id": "1002",
        "displayName": "VarsityGaming",
        "stream": {
            "id": "900200",
            "viewersCount": 2800,
        },
        "broadcastSettings": {
            "game": {"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"},
            "title": "Doktor's Curse 26 grinding | DROPS ON",
        },
    }
    apple_tv_only_drops = [{"id": "apple_tv_promo", "name": "1 Month of Apple TV"}]

    varsity_channel.external_update(channel_data, apple_tv_only_drops)

    assert varsity_channel.online is True
    assert varsity_channel.drops_enabled is True
    assert twitch.can_watch(varsity_channel) is True


def test_non_acl_channel_with_apple_tv_only_evaluates_drops_enabled_false():
    """A non-ACL channel with only Apple TV in AvailableDrops must evaluate drops_enabled=False."""
    twitch = DummyTwitch(available_drops_check=True)
    apple_tv = create_apple_tv_campaign(twitch)
    r6_camp = create_r6_acl_campaign(
        twitch,
        [{"id": "1001", "name": "itsspoit", "displayName": "itsspoit"}],
    )
    twitch._campaigns["apple_tv_promo"] = apple_tv
    twitch._campaigns["r6_doktors_curse_26"] = r6_camp
    twitch.inventory = [apple_tv, r6_camp]
    r6_game = Game({"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"})
    twitch.wanted_games = [r6_game]

    # Non-ACL streamer from directory
    random_streamer = Channel(twitch, id=9999, login="random_streamer", acl_based=False)
    channel_data = {
        "id": "9999",
        "displayName": "random_streamer",
        "stream": {
            "id": "900999",
            "viewersCount": 50,
        },
        "broadcastSettings": {
            "game": {"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"},
            "title": "Playing R6 casually",
        },
    }
    apple_tv_only_drops = [{"id": "apple_tv_promo", "name": "1 Month of Apple TV"}]

    random_streamer.external_update(channel_data, apple_tv_only_drops)

    # For non-ACL channel, drops_enabled must be False
    assert random_streamer.drops_enabled is False
    assert twitch.can_watch(random_streamer) is False


def test_check_drops_enabled_direct_call_for_acl_channel():
    """Direct Channel._check_drops_enabled call returns True for ACL channel."""
    twitch = DummyTwitch(available_drops_check=True)
    apple_tv = create_apple_tv_campaign(twitch)
    r6_camp = create_r6_acl_campaign(
        twitch,
        [{"id": "1001", "name": "itsspoit", "displayName": "itsspoit"}],
    )
    twitch._campaigns["apple_tv_promo"] = apple_tv
    twitch._campaigns["r6_doktors_curse_26"] = r6_camp
    twitch.inventory = [apple_tv, r6_camp]

    spoit_channel = r6_camp.allowed_channels[0]
    stream = Stream(
        spoit_channel,
        id=900100,
        game={"id": "460630", "name": "Tom Clancy's Rainbow Six Siege"},
        viewers=3000,
        title="R6 drops",
    )

    # Only Apple TV in available_drops
    available_drops = [{"id": "apple_tv_promo", "name": "1 Month of Apple TV"}]
    assert spoit_channel._check_drops_enabled(available_drops, stream=stream) is True
