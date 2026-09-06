"""Authentication and Twitch Device Flow API routes."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    get_current_user_id,
    verify_password,
)
from app.db.database import get_db
from app.db.repositories import (
    count_users,
    create_user,
    delete_twitch_account,
    get_active_twitch_account,
    get_user_by_id,
    get_user_by_username,
)
from app.engine.device_auth import device_auth_service
from app.engine.miner_worker import miner_service
from app.schemas.auth import (
    DeviceCodeInitResponse,
    DeviceCodeStatusResponse,
    LoginRequest,
    SetupAdminRequest,
    TokenResponse,
    TwitchAccountResponse,
    UserProfileResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/status", response_model=UserProfileResponse)
async def check_auth_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Check whether initial setup is completed and if current session is authenticated."""
    num_users = await count_users(db)
    is_setup_completed = num_users > 0

    user_id = None
    username = "Anonymous"
    is_active = False

    # Check optional session token
    token = request.cookies.get("access_token")
    if not token and "authorization" in request.headers:
        auth_hdr = request.headers["authorization"]
        if auth_hdr.lower().startswith("bearer "):
            token = auth_hdr[7:]

    if token:
        try:
            payload = decode_token(token, expected_type="access")
            uid = payload.get("sub")
            if uid:
                user = await get_user_by_id(db, uid)
                if user and user.is_active:
                    user_id = user.id
                    username = user.username
                    is_active = True
        except Exception:
            pass

    return UserProfileResponse(
        id=user_id or "",
        username=username,
        is_active=is_active,
        is_setup_completed=is_setup_completed,
    )


@router.post("/setup", response_model=TokenResponse)
@limiter.limit("5/minute")
async def setup_initial_admin(
    request: Request,
    response: Response,
    body: SetupAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initial wizard setup to create the admin account."""
    num_users = await count_users(db)
    if num_users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account is already setup. Please log in.",
        )

    user = await create_user(db, body.username, body.password)
    access_token = create_access_token(user.id, {"username": user.username})
    refresh_token = create_refresh_token(user.id)
    csrf_token = generate_csrf_token(user.id)

    # Set secure HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Readable by frontend JS to attach to X-CSRF-Token header
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        username=user.username,
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate admin user and issue short-lived JWT + refresh token."""
    user = await get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    access_token = create_access_token(user.id, {"username": user.username})
    refresh_token = create_refresh_token(user.id)
    csrf_token = generate_csrf_token(user.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        username=user.username,
        csrf_token=csrf_token,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token and issue fresh access token."""
    refresh_val = request.cookies.get("refresh_token")
    if not refresh_val:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing",
        )

    payload = decode_token(refresh_val, expected_type="refresh")
    user_id = payload.get("sub")
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer valid",
        )

    new_access_token = create_access_token(user.id, {"username": user.username})
    new_refresh_token = create_refresh_token(user.id)
    csrf_token = generate_csrf_token(user.id)

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.REQUIRE_HTTPS,
        samesite="lax",
    )

    return TokenResponse(
        access_token=new_access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        username=user.username,
        csrf_token=csrf_token,
    )


@router.post("/logout")
async def logout(response: Response, user_id: str = Depends(get_current_user_id)):
    """Clear session cookies."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="csrf_token")
    return {"message": "Logged out successfully"}


# --- Twitch Device Code Flow Endpoints ---

@router.post("/twitch/device-code/init", response_model=DeviceCodeInitResponse)
@limiter.limit("20/minute")
async def init_twitch_device_code(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Initiate Twitch OAuth 2.0 Device Code Flow."""
    try:
        data = await device_auth_service.initiate_device_flow()
        return DeviceCodeInitResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data.get("verification_uri", "https://www.twitch.tv/activate"),
            expires_in=data.get("expires_in", 1800),
            interval=data.get("interval", 5),
        )
    except Exception as exc:
        logger.error(f"Failed to initiate Twitch device flow: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Twitch OAuth Device Flow initiation failed: {str(exc)}",
        )


@router.get("/twitch/device-code/status", response_model=DeviceCodeStatusResponse)
@limiter.limit("60/minute")
async def check_twitch_device_status(
    request: Request,
    device_code: str,
    user_id: str = Depends(get_current_user_id),
):
    """Poll Twitch OAuth device code authorization status."""
    res = await device_auth_service.poll_device_token(device_code)
    if res["status"] == "success":
        # Notify miner to immediately start check_and_mine
        await miner_service.check_and_mine()

    return DeviceCodeStatusResponse(
        status=res["status"],
        message=res["message"],
        twitch_username=res.get("twitch_username"),
    )


@router.get("/twitch/account", response_model=TwitchAccountResponse)
async def get_twitch_account_status(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get active connected Twitch account info."""
    account = await get_active_twitch_account(db)
    if account:
        return TwitchAccountResponse(
            connected=True,
            twitch_user_id=account.twitch_user_id,
            twitch_username=account.twitch_username,
            connected_at=account.created_at,
        )
    return TwitchAccountResponse(connected=False)


@router.delete("/twitch/account")
async def disconnect_twitch_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect and revoke stored Twitch account."""
    account = await get_active_twitch_account(db)
    if account:
        await delete_twitch_account(db, account.id)
        await miner_service.stop()
        return {"message": "Twitch account disconnected successfully"}
    return {"message": "No connected Twitch account found"}
