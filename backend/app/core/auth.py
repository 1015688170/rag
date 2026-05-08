from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import Settings

SESSION_COOKIE_NAME = "rag_session"


class AuthError(Exception):
    pass


def verify_password(settings: Settings, username: str, password: str) -> bool:
    username_matches = secrets.compare_digest(username, settings.admin_username)
    password_matches = secrets.compare_digest(password, settings.admin_password)
    return username_matches and password_matches


def create_session_token(settings: Settings, username: str) -> str:
    payload = {
        "username": username,
        "issued_at": int(time.time()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _urlsafe_b64encode(payload_bytes)
    signature = _sign(settings.session_secret, encoded_payload)
    return f"{encoded_payload}.{signature}"


def validate_session_token(settings: Settings, token: str | None) -> dict[str, Any]:
    if not token or "." not in token:
        raise AuthError("missing token")
    encoded_payload, signature = token.rsplit(".", 1)
    expected_signature = _sign(settings.session_secret, encoded_payload)
    if not secrets.compare_digest(signature, expected_signature):
        raise AuthError("invalid signature")

    try:
        payload = json.loads(_urlsafe_b64decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise AuthError("invalid payload") from exc

    username = str(payload.get("username") or "")
    issued_at = int(payload.get("issued_at") or 0)
    if username != settings.admin_username:
        raise AuthError("invalid username")
    if issued_at <= 0 or time.time() - issued_at > settings.session_expire_hours * 3600:
        raise AuthError("expired token")
    return payload


def session_max_age(settings: Settings) -> int:
    return settings.session_expire_hours * 3600


def _sign(secret: str, encoded_payload: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    return _urlsafe_b64encode(digest)


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))
