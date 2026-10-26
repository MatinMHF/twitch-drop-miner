"""Tests for stream heartbeat payload dynamic timestamping and progress fallback."""

import time
import base64
import json
import pytest
from app.engine.devilxd_bridge import FastAPIBridgeGUIManager, BridgeProgress


class DummyTwitch:
    def __init__(self):
        class Settings:
            available_drops_check = False
        class AuthState:
            user_id = 123456
        self.settings = Settings()
        self._auth_state = AuthState()


class DummyChannel:
    def __init__(self):
        self._twitch = DummyTwitch()
        self.id = 99999
        self._login = "test_streamer"


def test_stream_spade_payload_is_dynamic():
    """Verify Stream.spade_payload evaluates client_time dynamically and does not freeze."""
    from app.engine.devilxd.channel import Stream

    ch = DummyChannel()
    stream = Stream(
        channel=ch,
        id=88888,
        game={"id": "460630", "displayName": "Rainbow Six Siege", "name": "Rainbow Six Siege"},
        viewers=100,
        title="Test Stream",
    )

    payload1 = stream.spade_payload
    data1 = json.loads(base64.b64decode(payload1["data"]).decode("utf8"))
    time1 = data1[0]["properties"]["client_time"]

    time.sleep(0.01)

    payload2 = stream.spade_payload
    data2 = json.loads(base64.b64decode(payload2["data"]).decode("utf8"))
    time2 = data2[0]["properties"]["client_time"]

    # Timestamps MUST NOT be identical (proves @property is used, not frozen @cached_property)
    assert time1 != time2, "spade_payload client_time was frozen and cached!"
    assert data1[0]["properties"]["channel"] == "test_streamer"
    assert data1[0]["properties"]["game"] == "Rainbow Six Siege"


def test_bridge_progress_minute_almost_done():
    """Verify BridgeProgress triggers fallback after 60s."""
    bridge = FastAPIBridgeGUIManager(None)
    progress = bridge.progress

    # First call returns True (since last_check starts at 0.0)
    assert progress.minute_almost_done() is True
    # Immediate second call returns False
    assert progress.minute_almost_done() is False
