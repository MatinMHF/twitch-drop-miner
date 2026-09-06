"""Tests for Twitch constants and persisted query builder."""

import pytest
from app.core.twitch_constants import (
    PERSISTED_QUERY_HASHES,
    get_query_hash,
    build_gql_persisted_query,
)


def test_persisted_query_hashes_registered():
    required_queries = [
        "DropCampaignDetails",
        "DropsHighlightService_AvailableDrops",
        "DirectoryPage_Game",
        "PlaybackAccessToken_Template",
        "ClaimDropMutation",
    ]
    for q in required_queries:
        assert q in PERSISTED_QUERY_HASHES
        h = get_query_hash(q)
        assert len(h) == 64  # SHA-256 hex length


def test_unknown_query_raises_error():
    with pytest.raises(KeyError):
        get_query_hash("NonExistentTwitchQuery_XYZ")


def test_build_gql_persisted_query_structure():
    payload = build_gql_persisted_query("DropCampaignDetails", {"dropID": "123"})
    assert payload["operationName"] == "DropCampaignDetails"
    assert payload["variables"] == {"dropID": "123"}
    assert "persistedQuery" in payload["extensions"]
    assert payload["extensions"]["persistedQuery"]["version"] == 1
    assert len(payload["extensions"]["persistedQuery"]["sha256Hash"]) == 64
