"""Authentication, JWT session management, bcrypt hashing, and CSRF protection."""

from __future__ import annotations

import hmac
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import bcrypt
import jwt
from fastapi import HTTPException, Security, Request, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


# --- Password Hashing with Bcrypt ---

def hash_password(plain_password: str) -> str:
    """Hash a password securely using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# --- JWT Tokens (Access & Refresh) ---

def create_access_token(subject: str, custom_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generate a short-lived access JWT token."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expires,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    if custom_claims:
        payload.update(custom_claims)
        
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Generate a long-lived refresh JWT token for rotation."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expires,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        if expected_type and payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- CSRF Token Protection ---

def generate_csrf_token(session_id: str) -> str:
    """Generate an HMAC-SHA256 CSRF token bound to the session/user."""
    message = f"csrf:{session_id}".encode("utf-8")
    return hmac.new(settings.CSRF_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_csrf_token(session_id: str, token: str) -> bool:
    """Verify the validity of a submitted CSRF token using constant-time comparison."""
    if not token or not session_id:
        return False
    expected = generate_csrf_token(session_id)
    return hmac.compare_digest(expected, token)


# --- FastAPI Auth Dependencies ---

async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> str:
    """Extract and authenticate the user from Bearer Token or Cookie."""
    token: Optional[str] = None
    
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_token(token, expected_type="access")
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
        
    # Check CSRF on state-changing methods if token is coming from cookies
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Double-submit cookie or header check
        csrf_header = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get("csrf_token")
        if csrf_cookie and csrf_header:
            if not hmac.compare_digest(csrf_cookie, csrf_header):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token mismatch",
                )

    return user_id
