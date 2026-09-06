"""Sanitized logging configuration to ensure tokens and secrets are never exposed."""

from __future__ import annotations

import logging
import re
import sys
from typing import List

# Patterns matching OAuth tokens, Bearer strings, passwords, and private keys
REDACTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"(oauth:)[a-zA-Z0-9_-]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[a-zA-Z0-9\._\-]+", re.IGNORECASE),
    re.compile(r"(['\"]?password['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(['\"]?access_token['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(['\"]?refresh_token['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(['\"]?secret['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(['\"]?csrf_token['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
]


class RedactingFormatter(logging.Formatter):
    """Log formatter that automatically masks sensitive tokens, credentials, and cookies."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        
        # Redact OAuth and Bearer prefixes
        redacted = re.sub(r"(oauth:)[a-zA-Z0-9_-]+", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
        redacted = re.sub(r"(Bearer\s+)[a-zA-Z0-9\._\-]+", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
        
        # Redact JSON or query key-value credential fields
        for pat in REDACTION_PATTERNS[2:]:
            redacted = pat.sub(r"\1[REDACTED]\3", redacted)
            
        return redacted


def setup_logger(name: str = "twitch_miner") -> logging.Logger:
    """Initialize and return a secure redacting logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger("twitch_miner")
