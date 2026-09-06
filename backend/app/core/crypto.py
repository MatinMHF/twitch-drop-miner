"""AES-256-GCM Cryptographic utilities for encrypting tokens at rest."""

from __future__ import annotations

import base64
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from app.core.config import settings


class TokenCipher:
    """Handles AES-256-GCM encryption and decryption of sensitive credentials."""

    def __init__(self, master_key_hex: Optional[str] = None):
        key_source = (master_key_hex or settings.ENCRYPTION_KEY).encode("utf-8")
        
        # Derive a 256-bit (32-byte) key using HKDF-SHA256
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"twitch-drop-miner-token-encryption-salt-v1",
            info=b"aes-256-gcm-master-key-derivation",
        )
        self._key = hkdf.derive(key_source)
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string using AES-256-GCM with a 12-byte random nonce.
        
        Returns:
            Base64-encoded string containing [12-byte nonce + ciphertext + 16-byte tag].
        """
        if not plaintext:
            return ""
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        data = plaintext.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        # Pack nonce and ciphertext together and base64 encode
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, encoded_payload: str) -> str:
        """Decrypt Base64-encoded [nonce + ciphertext + tag] back to plaintext string."""
        if not encoded_payload:
            return ""
        try:
            raw = base64.b64decode(encoded_payload.encode("utf-8"))
            if len(raw) < 12 + 16:  # Nonce (12) + Tag (16) minimum
                raise ValueError("Ciphertext payload is truncated or corrupted.")
            nonce = raw[:12]
            ciphertext = raw[12:]
            decrypted = self._aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except Exception as exc:
            raise ValueError(f"Failed to decrypt sensitive token: {str(exc)}") from exc


cipher = TokenCipher()
