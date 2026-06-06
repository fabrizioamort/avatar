"""Admin and visitor authentication helpers."""

import secrets

from fastapi import Cookie, HTTPException, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

COOKIE_NAME = "avatar_admin"
MAX_AGE = 60 * 60 * 24 * 7  # one week


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="avatar-admin")


def _visitor_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="avatar-visitor")


def verify_password(password: str) -> bool:
    """Constant-time comparison against the configured admin password."""
    return secrets.compare_digest(password, get_settings().admin_password)


def set_session_cookie(response: Response) -> None:
    """Issue a signed admin session cookie on the response."""
    token = _serializer().dumps("admin")
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the admin session cookie."""
    response.delete_cookie(COOKIE_NAME)


def is_authenticated(token: str | None) -> bool:
    """True when the cookie token is a valid, unexpired admin session."""
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_admin(avatar_admin: str | None = Cookie(default=None)) -> None:
    """FastAPI dependency that rejects requests without a valid admin cookie."""
    if not is_authenticated(avatar_admin):
        raise HTTPException(status_code=401, detail="Not authenticated")


def issue_visitor_token(conversation_id: str) -> str:
    """Create a signed visitor token scoped to one conversation id."""
    return _visitor_serializer().dumps({"conversation_id": conversation_id})


def verify_visitor_token(conversation_id: str, token: str | None) -> bool:
    """True when a visitor token is valid, unexpired, and scoped to the id."""
    if not token:
        return False
    try:
        payload = _visitor_serializer().loads(
            token,
            max_age=get_settings().visitor_session_max_age_seconds,
        )
    except (BadSignature, SignatureExpired):
        return False
    return payload.get("conversation_id") == conversation_id
