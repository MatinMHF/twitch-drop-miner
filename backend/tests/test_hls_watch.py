"""Tests for HLS playlist chunks HEAD requests and 20s watch interval (DevilXD f693b0c)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import timedelta
from yarl import URL

from app.engine.devilxd.constants import WATCH_INTERVAL, URLType
from app.engine.devilxd.channel import Channel, Stream


def test_watch_interval_is_twenty_seconds():
    """Verify WATCH_INTERVAL is set to 20 seconds (DevilXD f693b0c)."""
    assert WATCH_INTERVAL == timedelta(seconds=20)
    assert WATCH_INTERVAL.total_seconds() == 20


@pytest.mark.asyncio
async def test_send_watch_playlist_iterates_all_chunks_success():
    """Verify _send_watch_playlist iterates through all chunks starting with http."""
    twitch_mock = MagicMock()
    channel = Channel(twitch_mock, id=12345, login="test_user", display_name="TestUser")

    stream = Stream(
        channel=channel,
        id=99999,
        game={"id": "1", "displayName": "TestGame", "name": "TestGame"},
        viewers=100,
        title="Test Stream",
    )
    stream.get_stream_url = AsyncMock(return_value=URL("https://usher.ttvnw.net/stream.m3u8"))
    channel._stream = stream

    playlist_content = (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-TARGETDURATION:2\n"
        "#EXTINF:2.000,\n"
        "https://video-edge.twitch.tv/chunk-1.ts\n"
        "#EXTINF:2.000,\n"
        "https://video-edge.twitch.tv/chunk-2.ts\n"
        "#EXTINF:2.000,\n"
        "https://video-edge.twitch.tv/chunk-3.ts\n"
        "#EXT-X-ENDLIST\n"
    )

    requested_head_urls = []

    def mock_request(method, url, **kwargs):
        ctx = MagicMock()
        resp = AsyncMock()
        if method == "GET":
            resp.status = 200
            resp.text = AsyncMock(return_value=playlist_content)
        elif method == "HEAD":
            resp.status = 200
            requested_head_urls.append(str(url))
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    twitch_mock.request.side_effect = mock_request

    result = await channel._send_watch_playlist()

    assert result is True
    assert len(requested_head_urls) == 3
    assert requested_head_urls == [
        "https://video-edge.twitch.tv/chunk-1.ts",
        "https://video-edge.twitch.tv/chunk-2.ts",
        "https://video-edge.twitch.tv/chunk-3.ts",
    ]


@pytest.mark.asyncio
async def test_send_watch_playlist_returns_false_on_chunk_failure():
    """Verify _send_watch_playlist returns False if any chunk HEAD returns non-200."""
    twitch_mock = MagicMock()
    channel = Channel(twitch_mock, id=12345, login="test_user", display_name="TestUser")

    stream = Stream(
        channel=channel,
        id=99999,
        game={"id": "1", "displayName": "TestGame", "name": "TestGame"},
        viewers=100,
        title="Test Stream",
    )
    stream.get_stream_url = AsyncMock(return_value=URL("https://usher.ttvnw.net/stream.m3u8"))
    channel._stream = stream

    playlist_content = (
        "https://video-edge.twitch.tv/chunk-1.ts\n"
        "https://video-edge.twitch.tv/chunk-2.ts\n"
    )

    call_count = 0

    def mock_request(method, url, **kwargs):
        nonlocal call_count
        ctx = MagicMock()
        resp = AsyncMock()
        if method == "GET":
            resp.status = 200
            resp.text = AsyncMock(return_value=playlist_content)
        elif method == "HEAD":
            call_count += 1
            resp.status = 200 if call_count == 1 else 404
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    twitch_mock.request.side_effect = mock_request

    result = await channel._send_watch_playlist()
    assert result is False
