"""Centralized registry for Twitch GraphQL Persisted Query Hashes and endpoints.

All hashes and endpoints are defined as constants here with environment variable
override support so they can be updated in one place whenever Twitch updates them.
"""

from __future__ import annotations

import os
from typing import Dict, Any

# --- Official & Standard Public Twitch Client IDs ---
# Twitch Web Client ID (standard for GQL queries)
DEFAULT_TWITCH_WEB_CLIENT_ID: str = "kimne78kx3ncx6brgo4mv6wki5h1ko"
# Twitch TV / Console Client ID (supports standard OAuth 2.0 Device Flow without secret)
DEFAULT_TWITCH_DEVICE_CLIENT_ID: str = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"

TWITCH_WEB_CLIENT_ID: str = os.getenv("TWITCH_WEB_CLIENT_ID", DEFAULT_TWITCH_WEB_CLIENT_ID)
TWITCH_DEVICE_CLIENT_ID: str = os.getenv("TWITCH_DEVICE_CLIENT_ID", DEFAULT_TWITCH_DEVICE_CLIENT_ID)

# --- Endpoints ---
TWITCH_GQL_URL: str = os.getenv("TWITCH_GQL_URL", "https://gql.twitch.tv/gql")
TWITCH_OAUTH_DEVICE_URL: str = os.getenv("TWITCH_OAUTH_DEVICE_URL", "https://id.twitch.tv/oauth2/device")
TWITCH_OAUTH_TOKEN_URL: str = os.getenv("TWITCH_OAUTH_TOKEN_URL", "https://id.twitch.tv/oauth2/token")
TWITCH_OAUTH_VALIDATE_URL: str = os.getenv("TWITCH_OAUTH_VALIDATE_URL", "https://id.twitch.tv/oauth2/validate")
TWITCH_OAUTH_REVOKE_URL: str = os.getenv("TWITCH_OAUTH_REVOKE_URL", "https://id.twitch.tv/oauth2/revoke")

# Spade Analytics / Minute-Watched Tracker Endpoints
DEFAULT_TWITCH_SPADE_URL: str = "https://video-edge-104.sjc01.hls.ttvnw.net/v1/segment/"
TWITCH_SPADE_URL: str = os.getenv("TWITCH_SPADE_URL", "https://spade.twitch.tv/batched")


# --- Persisted Query Hashes (SHA-256) ---
# Override any hash via environment variables (e.g. TWITCH_HASH_DROP_CAMPAIGN_DETAILS)
PERSISTED_QUERY_HASHES: Dict[str, str] = {
    # Drop Campaigns & Inventory
    "DropCampaignDetails": os.getenv(
        "TWITCH_HASH_DROP_CAMPAIGN_DETAILS",
        "14b5532296e8346065529f7cb2f436be3c5ca02636f3458ff62df18ae87f735c",
    ),
    "DropsHighlightService_AvailableDrops": os.getenv(
        "TWITCH_HASH_AVAILABLE_DROPS",
        "b1949711c266858064a7813a48e3de4214fe967c9b0e2f5b35889ff4c2810a9c",
    ),
    "ViewerDropsDashboard": os.getenv(
        "TWITCH_HASH_VIEWER_DROPS_DASHBOARD",
        "e8b9835237990c6b8409fbc62f55496939055416047214731885b54ae52077e6",
    ),
    "ClaimDropMutation": os.getenv(
        "TWITCH_HASH_CLAIM_DROP",
        "2f813d6288837bc2869818475bd840ef7482656a5e12fcc9a0d2481b041b1b11",
    ),
    "DropCampaignClaimDrop": os.getenv(
        "TWITCH_HASH_DROP_CAMPAIGN_CLAIM_DROP",
        "a455deea71bdc9015b78eb49f4acfbce800bc456d598281695713502842bf430",
    ),
    # Directory & Channels
    "DirectoryPage_Game": os.getenv(
        "TWITCH_HASH_DIRECTORY_GAME",
        "d5c5c0529d665a31a9c3d42de782fec9deca888aa38031d2ff287ffc9f7a77e5",
    ),
    "DirectoryRoot_Directory": os.getenv(
        "TWITCH_HASH_DIRECTORY_ROOT",
        "76192cfba9e1bf0fb4440078b17c5b61b24d7cb0efb32e14bc2bc3b6cbbe1d72",
    ),
    "SearchFor": os.getenv(
        "TWITCH_HASH_SEARCH_FOR",
        "d5db530d363e0f968529367c9ad50a7c64c7ef21ea6e54ee00e7ff2b3cb1c9ef",
    ),
    "ChannelShell": os.getenv(
        "TWITCH_HASH_CHANNEL_SHELL",
        "c3ea5a50b73c242e22c07b69c6cf260840c83a1523dd0fb8a9fb462f4fb89e3f",
    ),
    "VideoPlayerStreamInfoOverlayChannel": os.getenv(
        "TWITCH_HASH_STREAM_INFO",
        "198492c0a1de4392a40bc0eed5ee3a7cf52885917290928db641c88d55c7b398",
    ),
    "PlaybackAccessToken_Template": os.getenv(
        "TWITCH_HASH_PLAYBACK_ACCESS_TOKEN",
        "0828119ded1c13477966434e15800ff57ddace7ba03078779303243b6d381767",
    ),
    "CoreActionsMinuteWatched": os.getenv(
        "TWITCH_HASH_MINUTE_WATCHED",
        "0f223a272782e4e16dcf3ee43f2a8999818817c181775a74ff9ee1cc9ff740f9",
    ),
}


def get_query_hash(operation_name: str) -> str:
    """Retrieve the SHA-256 persisted query hash for a given Twitch GQL operation."""
    if operation_name not in PERSISTED_QUERY_HASHES:
        raise KeyError(
            f"Operation '{operation_name}' not found in PERSISTED_QUERY_HASHES registry. "
            f"Available operations: {list(PERSISTED_QUERY_HASHES.keys())}"
        )
    return PERSISTED_QUERY_HASHES[operation_name]


def build_gql_persisted_query(operation_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Construct a standard Twitch GraphQL persisted query payload."""
    query_hash = get_query_hash(operation_name)
    return {
        "operationName": operation_name,
        "variables": variables,
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": query_hash,
            }
        },
    }
