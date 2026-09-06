"""Twitch OAuth Device Code Flow implementation for headless browser-free authentication."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.twitch_constants import (
    TWITCH_DEVICE_CLIENT_ID,
    TWITCH_OAUTH_DEVICE_URL,
    TWITCH_OAUTH_TOKEN_URL,
    TWITCH_OAUTH_VALIDATE_URL,
)
from app.db.database import AsyncSessionLocal
from app.db.repositories import save_or_update_twitch_account


class DeviceAuthFlow:
    """Handles OAuth 2.0 Device Authorization Grant (RFC 8628) for Twitch."""

    DEFAULT_SCOPES = [
        "user:read:email",
        "user:read:broadcast",
        "chat:read",
        "user:read:subscriptions",
    ]

    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or TWITCH_DEVICE_CLIENT_ID
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    async def initiate_device_flow(self) -> Dict[str, Any]:
        """Initiate device code flow and return verification URI + user code."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "client_id": self.client_id,
                "scopes": " ".join(self.DEFAULT_SCOPES),
            }
            response = await client.post(
                TWITCH_OAUTH_DEVICE_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

            device_code = data["device_code"]
            self._active_sessions[device_code] = {
                "device_code": device_code,
                "user_code": data["user_code"],
                "verification_uri": data.get("verification_uri", "https://www.twitch.tv/activate"),
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 1800)),
                "interval": max(data.get("interval", 5), 3),
                "status": "pending",
                "twitch_username": None,
            }
            return data

    async def validate_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate OAuth token and fetch associated Twitch user details."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                headers = {"Authorization": f"OAuth {access_token}"}
                response = await client.get(TWITCH_OAUTH_VALIDATE_URL, headers=headers)
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as exc:
                logger.error(f"Error validating Twitch token: {exc}")
                return None

    async def poll_device_token(self, device_code: str) -> Dict[str, Any]:
        """Check status of device code grant and store credentials upon user approval."""
        session_info = self._active_sessions.get(device_code)
        if not session_info:
            return {"status": "expired", "message": "Device flow session not found or expired"}

        if datetime.now(timezone.utc) > session_info["expires_at"]:
            self._active_sessions.pop(device_code, None)
            return {"status": "expired", "message": "Device code has expired"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "client_id": self.client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }
            try:
                response = await client.post(
                    TWITCH_OAUTH_TOKEN_URL,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                data = response.json()

                if response.status_code == 200:
                    access_token = data.get("access_token")
                    refresh_token = data.get("refresh_token")
                    expires_in = data.get("expires_in", 3600)
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    # Validate token to get user ID and username
                    user_info = await self.validate_token(access_token)
                    if not user_info:
                        return {"status": "failed", "message": "Failed to validate retrieved OAuth token"}

                    twitch_user_id = str(user_info.get("user_id"))
                    twitch_username = str(user_info.get("login", ""))

                    # Save encrypted tokens into database
                    async with AsyncSessionLocal() as db:
                        await save_or_update_twitch_account(
                            db=db,
                            twitch_user_id=twitch_user_id,
                            twitch_username=twitch_username,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at,
                        )

                    session_info["status"] = "success"
                    session_info["twitch_username"] = twitch_username
                    logger.info(f"Successfully authenticated Twitch user: {twitch_username}")
                    return {
                        "status": "success",
                        "message": f"Successfully connected Twitch account @{twitch_username}",
                        "twitch_username": twitch_username,
                    }

                error_code = data.get("message") or data.get("error", "")
                if "authorization_pending" in error_code.lower() or response.status_code == 400:
                    return {"status": "pending", "message": "Waiting for user authorization on Twitch..."}

                return {"status": "failed", "message": f"Twitch authorization error: {error_code}"}

            except Exception as exc:
                logger.error(f"Device code polling error: {exc}")
                return {"status": "failed", "message": str(exc)}


device_auth_service = DeviceAuthFlow()
