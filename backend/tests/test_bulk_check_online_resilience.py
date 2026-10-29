"""Tests for bulk_check_online resilience against GQL and network errors."""

import sys
from pathlib import Path

# Import devilxd_bridge first to register sys.modules["gui"] stub
from app.engine.devilxd_bridge import Twitch, Channel
from app.engine.devilxd.exceptions import GQLException

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockSettings:
    def __init__(self, available_drops_check: bool = True):
        self.available_drops_check = available_drops_check
        self.connection_quality = 1
        self.dump = False
        self.priority = []


@pytest.fixture
def dummy_twitch():
    twitch = MagicMock(spec=Twitch)
    twitch.settings = MockSettings(available_drops_check=True)
    twitch.gui = MagicMock()
    twitch.gui.channels = MagicMock()
    twitch.channels = {}
    twitch._campaigns = {}
    twitch.wanted_games = []
    # Bind the actual bulk_check_online method to the mock instance
    twitch.bulk_check_online = Twitch.bulk_check_online.__get__(twitch, Twitch)
    return twitch


@pytest.mark.asyncio
async def test_bulk_check_online_handles_gql_exception_in_available_drops(dummy_twitch):
    """Verify bulk_check_online does not crash/raise when AvailableDrops throws GQLException."""
    channel = Channel(dummy_twitch, id=1001, login="streamer1", display_name="Streamer One")

    stream_info_response = [
        {
            "data": {
                "user": {
                    "id": "1001",
                    "login": "streamer1",
                    "displayName": "Streamer One",
                    "broadcastSettings": {"id": "1001", "title": "Stream title", "game": {"id": "123", "name": "Rust"}},
                    "stream": {
                        "id": "111111",
                        "createdAt": "2026-10-29T00:00:00Z",
                        "title": "Stream title",
                        "viewersCount": 42,
                        "game": {"id": "123", "name": "Rust"},
                    },
                }
            }
        }
    ]

    async def mock_gql_request(ops):
        # If it's AvailableDrops query, raise the exact GQLException seen in production crash
        if isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "DropsHighlightService_AvailableDrops":
            raise GQLException([{"message": "service error", "path": ["channel", "viewerDropCampaigns"]}])
        return stream_info_response

    dummy_twitch.gql_request = AsyncMock(side_effect=mock_gql_request)

    # In current code, this raises GQLException!
    # With safe-guarding, it should succeed without raising.
    await dummy_twitch.bulk_check_online([channel])

    # The channel should still be recognized as online
    assert channel.online is True
    assert channel._stream is not None


@pytest.mark.asyncio
async def test_bulk_check_online_handles_partial_gql_failures(dummy_twitch):
    """Verify bulk_check_online updates channels even if one chunk fails and one succeeds."""
    ch1 = Channel(dummy_twitch, id=1001, login="streamer1")
    ch2 = Channel(dummy_twitch, id=1002, login="streamer2")

    async def mock_gql_request(ops):
        if isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "VideoPlayerStreamInfoOverlayChannel":
            return [
                {
                    "data": {
                        "user": {
                            "id": "1001",
                            "login": "streamer1",
                            "displayName": "Streamer 1",
                            "broadcastSettings": {"id": "1001", "title": "Title 1", "game": {"id": "123", "name": "Rust"}},
                            "stream": {
                                "id": "111111",
                                "createdAt": "2026-10-29T00:00:00Z",
                                "title": "Title 1",
                                "viewersCount": 10,
                                "game": {"id": "123", "name": "Rust"},
                            },
                        }
                    }
                },
                {
                    "data": {
                        "user": {
                            "id": "1002",
                            "login": "streamer2",
                            "displayName": "Streamer 2",
                            "broadcastSettings": {"id": "1002", "title": "Title 2", "game": {"id": "123", "name": "Rust"}},
                            "stream": {
                                "id": "222222",
                                "createdAt": "2026-10-29T00:00:00Z",
                                "title": "Title 2",
                                "viewersCount": 20,
                                "game": {"id": "123", "name": "Rust"},
                            },
                        }
                    }
                },
            ]
        elif isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "DropsHighlightService_AvailableDrops":
            # Throw GQLException
            raise GQLException("GQL Service Timeout")
        return []

    dummy_twitch.gql_request = AsyncMock(side_effect=mock_gql_request)

    await dummy_twitch.bulk_check_online([ch1, ch2])

    assert ch1.online is True
    assert ch2.online is True


@pytest.mark.asyncio
async def test_bulk_check_online_handles_null_channel_data_in_available_drops(dummy_twitch):
    """Verify bulk_check_online gracefully handles response with None channel data."""
    channel = Channel(dummy_twitch, id=1001, login="streamer1")

    async def mock_gql_request(ops):
        if isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "VideoPlayerStreamInfoOverlayChannel":
            return [
                {
                    "data": {
                        "user": {
                            "id": "1001",
                            "login": "streamer1",
                            "broadcastSettings": {"id": "1001", "title": "Title 1", "game": {"id": "123", "name": "Rust"}},
                            "stream": {
                                "id": "111111",
                                "createdAt": "2026-10-29T00:00:00Z",
                                "title": "Title 1",
                                "viewersCount": 10,
                                "game": {"id": "123", "name": "Rust"},
                            },
                        }
                    }
                }
            ]
        elif isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "DropsHighlightService_AvailableDrops":
            # Response where channel is None (or data is None)
            return [{"data": {"channel": None}}]
        return []

    dummy_twitch.gql_request = AsyncMock(side_effect=mock_gql_request)

    await dummy_twitch.bulk_check_online([channel])

    assert channel.online is True


@pytest.mark.asyncio
async def test_bulk_check_online_processes_available_drops_when_successful(dummy_twitch):
    """Verify bulk_check_online populates available drops when GQL AvailableDrops succeeds."""
    channel = Channel(dummy_twitch, id=1001, login="streamer1")

    async def mock_gql_request(ops):
        if isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "VideoPlayerStreamInfoOverlayChannel":
            return [
                {
                    "data": {
                        "user": {
                            "id": "1001",
                            "login": "streamer1",
                            "broadcastSettings": {"id": "1001", "title": "Title 1", "game": {"id": "123", "name": "Rust"}},
                            "stream": {
                                "id": "111111",
                                "createdAt": "2026-10-29T00:00:00Z",
                                "title": "Title 1",
                                "viewersCount": 10,
                                "game": {"id": "123", "name": "Rust"},
                            },
                        }
                    }
                }
            ]
        elif isinstance(ops, list) and len(ops) > 0 and ops[0].get("operationName") == "DropsHighlightService_AvailableDrops":
            return [
                {
                    "data": {
                        "channel": {
                            "id": "1001",
                            "viewerDropCampaigns": [{"id": "camp1", "name": "Campaign 1"}],
                        }
                    }
                }
            ]
        return []

    dummy_twitch.gql_request = AsyncMock(side_effect=mock_gql_request)

    # Mock external_update on Channel class to inspect what was passed
    orig_external_update = Channel.external_update
    update_calls = []

    def wrapped_update(self_ch, channel_data, available_drops):
        update_calls.append((self_ch, channel_data, available_drops))
        return orig_external_update(self_ch, channel_data, available_drops)

    with patch.object(Channel, "external_update", side_effect=wrapped_update, autospec=True):
        await dummy_twitch.bulk_check_online([channel])

    assert len(update_calls) == 1
    assert update_calls[0][2] == [{"id": "camp1", "name": "Campaign 1"}]
    assert channel.online is True


