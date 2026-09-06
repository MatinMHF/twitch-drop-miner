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
        "039277bf98f3130929262cc7c6efd9c141ca3749cb6dca442fc8ead9a53f77c1",
    ),
    "DropsHighlightService_AvailableDrops": os.getenv(
        "TWITCH_HASH_AVAILABLE_DROPS",
        "782dad0f032942260171d2d80a654f88bdd0c5a9dddc392e9bc92218a0f42d20",
    ),
    "ViewerDropsDashboard": os.getenv(
        "TWITCH_HASH_VIEWER_DROPS_DASHBOARD",
        "d9cae7761dafab85908c85e6683cb4201b449e66ac3bb5e894f15ff12aeafaa7",
    ),
    "ClaimDropMutation": os.getenv(
        "TWITCH_HASH_CLAIM_DROP",
        "a455deea71bdc9015b78eb49f4acfbce8baa7ccbedd28e549bb025bd0f751930",
    ),
    "DropCampaignClaimDrop": os.getenv(
        "TWITCH_HASH_DROP_CAMPAIGN_CLAIM_DROP",
        "a455deea71bdc9015b78eb49f4acfbce8baa7ccbedd28e549bb025bd0f751930",
    ),
    # Directory & Channels
    "DirectoryPage_Game": os.getenv(
        "TWITCH_HASH_DIRECTORY_GAME",
        "86bcceb4e8b1a51256ff8eed8bd8aae4acacf80d737efe904f84f3aeadf8cafd",
    ),
    "DirectoryRoot_Directory": os.getenv(
        "TWITCH_HASH_DIRECTORY_ROOT",
        "76192cfba9e1bf0fb4440078b17c5b61b24d7cb0efb32e14bc2bc3b6cbbe1d72",
    ),
    "DirectoryGameRedirect": os.getenv(
        "TWITCH_HASH_DIRECTORY_GAME_REDIRECT",
        "1f0300090caceec51f33c5e20647aceff9017f740f223c3c532ba6fa59f6b6cc",
    ),
    "SearchFor": os.getenv(
        "TWITCH_HASH_SEARCH_FOR",
        "1f0300090caceec51f33c5e20647aceff9017f740f223c3c532ba6fa59f6b6cc",
    ),
    "ChannelShell": os.getenv(
        "TWITCH_HASH_CHANNEL_SHELL",
        "c3ea5a50b73c242e22c07b69c6cf260840c83a1523dd0fb8a9fb462f4fb89e3f",
    ),
    "VideoPlayerStreamInfoOverlayChannel": os.getenv(
        "TWITCH_HASH_STREAM_INFO",
        "198492e0857f6aedead9665c81c5a06d67b25b58034649687124083ff288597d",
    ),
    "PlaybackAccessToken_Template": os.getenv(
        "TWITCH_HASH_PLAYBACK_ACCESS_TOKEN",
        "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9",
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
