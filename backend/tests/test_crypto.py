"""Tests for AES-256-GCM token encryption and decryption."""

import pytest
from app.core.crypto import TokenCipher


def test_token_encryption_and_decryption():
    cipher = TokenCipher("test-master-encryption-key-1234567890")
    sample_oauth_token = "oauth:a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

    # Encrypt
    encrypted = cipher.encrypt(sample_oauth_token)
    assert encrypted != sample_oauth_token
    assert len(encrypted) > 20

    # Decrypt
    decrypted = cipher.decrypt(encrypted)
    assert decrypted == sample_oauth_token


def test_encryption_empty_string():
    cipher = TokenCipher("test-master-encryption-key-1234567890")
    assert cipher.encrypt("") == ""
    assert cipher.decrypt("") == ""


def test_decryption_tampered_ciphertext():
    cipher = TokenCipher("test-master-encryption-key-1234567890")
    encrypted = cipher.encrypt("secret-token")

    # Corrupt the payload
    corrupted = "X" + encrypted[1:]
    with pytest.raises(ValueError):
        cipher.decrypt(corrupted)


def test_different_keys_fail_decryption():
    cipher1 = TokenCipher("key-one-111111111111111111111111")
    cipher2 = TokenCipher("key-two-222222222222222222222222")

    encrypted = cipher1.encrypt("super-secret-token")
    with pytest.raises(ValueError):
        cipher2.decrypt(encrypted)
