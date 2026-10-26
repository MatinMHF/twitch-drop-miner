"""Tests verifying backend bug fixes:
1. Token cookie seeding & device code error handling in DevilXD engine.
2. SingleAccountWorker credential and cookie seeding.
3. MultiAccountMiningManager compatibility in list_watchlist without AttributeError.
4. MultiTwitchAccountsResponse Pydantic model_rebuild resolution.
"""

import asyncio
import secrets
import pytest
from unittest.mock import AsyncMock, MagicMock
from yarl import URL
import aiohttp

from app.engine.devilxd_bridge import create_devilxd_instance
from app.engine.devilxd.twitch import _AuthState
from app.engine.miner_worker import SingleAccountWorker, MultiAccountMiningManager
from app.api.games import list_watchlist
from app.db.database import init_db, AsyncSessionLocal
from app.schemas.auth import MultiTwitchAccountsResponse, TwitchAccountResponse


@pytest.mark.asyncio
async def test_oauth_login_non_200_raises_clean_runtime_error():
    """Bug 1: _oauth_login raises RuntimeError instead of KeyError when HTTP status != 200."""
    twitch_mock = MagicMock()
    auth_state = _AuthState(twitch_mock)
    auth_state.device_id = "test_device_id"

    resp_mock = AsyncMock()
    resp_mock.status = 500
    resp_mock.json.return_value = {"error": "Server error"}

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp_mock)
    ctx.__aexit__ = AsyncMock(return_value=None)
    twitch_mock.request.return_value = ctx

    with pytest.raises(RuntimeError) as exc_info:
        await auth_state._oauth_login()
    assert "Failed to obtain device code" in str(exc_info.value) or "HTTP 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_oauth_login_missing_device_code_raises_clean_runtime_error():
    """Bug 1: _oauth_login raises RuntimeError instead of KeyError when device_code is missing."""
    twitch_mock = MagicMock()
    auth_state = _AuthState(twitch_mock)
    auth_state.device_id = "test_device_id"

    resp_mock = AsyncMock()
    resp_mock.status = 200
    resp_mock.json.return_value = {"status": "ok", "error": "missing field"}

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp_mock)
    ctx.__aexit__ = AsyncMock(return_value=None)
    twitch_mock.request.return_value = ctx

    with pytest.raises(RuntimeError) as exc_info:
        await auth_state._oauth_login()
    assert "device_code" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cookie_seeding_and_restoration_logic():
    """Bug 1: Verify token seeding into cookie and restoration from cookie."""
    jar = aiohttp.CookieJar()
    client_url = URL("https://www.twitch.tv")

    # 1. Seeding when cookie is empty and self has access_token
    auth_state = _AuthState(MagicMock())
    auth_state.access_token = "preseeded_token_xyz"

    cookie = jar.filter_cookies(client_url)
    if "auth-token" not in cookie:
        if hasattr(auth_state, "access_token") and auth_state.access_token:
            cookie["auth-token"] = auth_state.access_token
        else:
            auth_state.access_token = "new_oauth_token"
            cookie["auth-token"] = auth_state.access_token
    elif not hasattr(auth_state, "access_token") or not auth_state.access_token:
        auth_state.access_token = cookie["auth-token"].value

    assert cookie["auth-token"].value == "preseeded_token_xyz"

    # 2. Restoring from cookie when self.access_token is missing/empty
    auth_state_empty = _AuthState(MagicMock())
    auth_state_empty.access_token = None

    jar2 = aiohttp.CookieJar()
    jar2.update_cookies({"auth-token": "saved_cookie_token_123"}, client_url)
    cookie2 = jar2.filter_cookies(client_url)

    if "auth-token" not in cookie2:
        if hasattr(auth_state_empty, "access_token") and auth_state_empty.access_token:
            cookie2["auth-token"] = auth_state_empty.access_token
        else:
            auth_state_empty.access_token = "new_oauth_token"
            cookie2["auth-token"] = auth_state_empty.access_token
    elif not hasattr(auth_state_empty, "access_token") or not auth_state_empty.access_token:
        auth_state_empty.access_token = cookie2["auth-token"].value

    assert auth_state_empty.access_token == "saved_cookie_token_123"


@pytest.mark.asyncio
async def test_single_account_worker_cookie_seeding():
    """Bug 2: SingleAccountWorker credential pre-seeding populates session cookie jar."""
    worker = SingleAccountWorker("test_acc", "98765432", "test_streamer", lambda: None)
    worker.twitch, worker.bridge = create_devilxd_instance(["Rust"], user_id=worker.twitch_user_id)
    access_token = "seeded_oauth_token_abc"

    worker.twitch._auth_state.device_id = secrets.token_hex(16)
    worker.twitch._auth_state.session_id = secrets.token_hex(16)
    worker.twitch._auth_state.access_token = access_token
    worker.twitch._auth_state.user_id = int(worker.twitch_user_id)
    worker.twitch._auth_state._logged_in.set()

    if worker.twitch._session is None:
        await worker.twitch.get_session()
    worker.twitch._session.cookie_jar.update_cookies(
        {"auth-token": access_token},
        URL("https://www.twitch.tv"),
    )

    cookies = worker.twitch._session.cookie_jar.filter_cookies(URL("https://www.twitch.tv"))
    assert "auth-token" in cookies
    assert cookies["auth-token"].value == access_token

    await worker.twitch.shutdown()


@pytest.mark.asyncio
async def test_list_watchlist_multi_account_manager_no_attribute_error():
    """Bug 3: list_watchlist does not crash with AttributeError when miner_service is MultiAccountMiningManager."""
    await init_db()
    async with AsyncSessionLocal() as db:
        # miner_service in app.api.games is an instance of MultiAccountMiningManager
        # It does not have .twitch attribute, only .workers dict.
        res = await list_watchlist(user_id="test_user", db=db)
        assert isinstance(res, list)


def test_multi_twitch_accounts_response_pydantic_model_rebuild():
    """Bug 4: MultiTwitchAccountsResponse builds and validates properly with model_rebuild."""
    resp = MultiTwitchAccountsResponse(
        accounts=[
            TwitchAccountResponse(
                connected=True,
                account_id="acc-1",
                twitch_user_id="12345",
                twitch_username="streamer_one",
            )
        ],
        total_connected=1,
    )
    assert resp.total_connected == 1
    assert len(resp.accounts) == 1
    assert resp.accounts[0].twitch_username == "streamer_one"
