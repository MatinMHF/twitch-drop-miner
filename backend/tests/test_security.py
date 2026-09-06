"""Tests for password hashing, JWT generation, and CSRF protection."""

import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    verify_csrf_token,
)


def test_password_hashing():
    raw = "SuperSecurePassword123!"
    hashed = hash_password(raw)

    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_access_and_refresh_tokens():
    user_id = "user-12345"
    access_token = create_access_token(user_id, {"role": "admin"})
    refresh_token = create_refresh_token(user_id)

    # Validate access token
    access_payload = decode_token(access_token, expected_type="access")
    assert access_payload["sub"] == user_id
    assert access_payload["role"] == "admin"
    assert access_payload["type"] == "access"

    # Validate refresh token
    refresh_payload = decode_token(refresh_token, expected_type="refresh")
    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"


def test_csrf_generation_and_validation():
    session_id = "session-abc-987"
    token = generate_csrf_token(session_id)

    assert len(token) == 64
    assert verify_csrf_token(session_id, token) is True
    assert verify_csrf_token("different-session", token) is False
    assert verify_csrf_token(session_id, "invalid-token") is False
