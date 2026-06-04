"""Segurança de webhooks: HMAC, criptografia, idempotency."""
from __future__ import annotations
import hashlib
import hmac
import logging
import os
import secrets as py_secrets
import time
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_MASTER_KEY = os.getenv("WEBHOOK_MASTER_KEY", "").encode()
if not _MASTER_KEY:
    fallback = os.getenv("JWT_SECRET", "fallback-insecure-dev-key")
    _MASTER_KEY = urlsafe_b64encode(hashlib.sha256(fallback.encode()).digest())
    logger.warning("WEBHOOK_MASTER_KEY não configurada — usando fallback de dev")

_fernet = Fernet(_MASTER_KEY)


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Secret corrompido ou chave master errada")


def generate_secret(length: int = 32) -> str:
    return py_secrets.token_urlsafe(length)


def sign_payload(payload: bytes, secret: str, timestamp: int | None = None) -> tuple[str, int]:
    if timestamp is None:
        timestamp = int(time.time())
    msg = f"{timestamp}.".encode() + payload
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return sig, timestamp


def verify_signature(payload: bytes, signature: str, timestamp: int, secret: str, max_age_seconds: int = 300) -> bool:
    now = int(time.time())
    if abs(now - timestamp) > max_age_seconds:
        return False
    expected, _ = sign_payload(payload, secret, timestamp)
    return hmac.compare_digest(expected, signature)


def payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_signature_header(header_value: str) -> tuple[int, str] | None:
    if not header_value:
        return None
    try:
        parts = dict(p.split("=", 1) for p in header_value.split(","))
        return int(parts["t"]), parts["v1"]
    except (KeyError, ValueError):
        return None
