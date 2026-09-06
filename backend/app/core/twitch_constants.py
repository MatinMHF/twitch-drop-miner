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
DEFAULT_TWITCH_SPADE_URL: str = "https://spade.twitch.tv/"
TWITCH_SPADE_URL: str = os.getenv("TWITCH_SPADE_URL", DEFAULT_TWITCH_SPADE_URL)


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
    "DropsPage_ClaimDropRewards": os.getenv(
        "TWITCH_HASH_CLAIM_DROP",
        "a455deea71bdc9015b78eb49f4acfbce8baa7ccbedd28e549bb025bd0f751930",
    ),
    "ClaimDropMutation": os.getenv(
        "TWITCH_HASH_CLAIM_DROP",
        "a455deea71bdc9015b78eb49f4acfbce8baa7ccbedd28e549bb025bd0f751930",
    ),
    "DropCampaignClaimDrop": os.getenv(
        "TWITCH_HASH_DROP_CAMPAIGN_CLAIM_DROP",
        "a455deea71bdc9015b78eb49f4acfbce8baa7ccbedd28e549bb025bd0f751930",
    ),
    "Inventory": os.getenv(
        "TWITCH_HASH_INVENTORY",
        "8337eb8541b314040b0edde0c09c5c7a2783ba1960aa9edfbf3bac16d0fec404",
    ),
    # Directory & Channels
    "DirectoryPage_Game": os.getenv(
        "TWITCH_HASH_DIRECTORY_GAME",
        "86bcceb4e8b1a51256ff8eed8bd8aae4acacf80d737efe904f84f3aeadf8cafd",
    ),
    "DirectoryGameRedirect": os.getenv(
        "TWITCH_HASH_DIRECTORY_GAME_REDIRECT",
        "1f0300090caceec51f33c5e20647aceff9017f740f223c3c532ba6fa59f6b6cc",
    ),
    "SearchFor": os.getenv(
        "TWITCH_HASH_SEARCH_FOR",
        "1f0300090caceec51f33c5e20647aceff9017f740f223c3c532ba6fa59f6b6cc",
    ),
    "VideoPlayerStreamInfoOverlayChannel": os.getenv(
        "TWITCH_HASH_STREAM_INFO",
        "198492e0857f6aedead9665c81c5a06d67b25b58034649687124083ff288597d",
    ),
    "PlaybackAccessToken": os.getenv(
        "TWITCH_HASH_PLAYBACK_ACCESS_TOKEN",
        "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9",
    ),
    "PlaybackAccessToken_Template": os.getenv(
        "TWITCH_HASH_PLAYBACK_ACCESS_TOKEN",
        "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9",
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
