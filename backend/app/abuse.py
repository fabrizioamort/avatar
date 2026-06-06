"""In-process abuse guards for public chat, admin login, and push notifications."""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass

from fastapi import HTTPException, Request
from limits import RateLimitItem, parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from app.config import get_settings

logger = logging.getLogger(__name__)

_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)


@dataclass(frozen=True)
class RequestIdentity:
    """Stable request identity used by rate-limit keys."""

    source_ip: str


def reset_limits() -> None:
    """Clear in-memory limiter state for tests."""
    global _storage, _limiter
    _storage = MemoryStorage()
    _limiter = MovingWindowRateLimiter(_storage)


def _rate(value: str) -> RateLimitItem:
    return parse(value)


def _check(rate: RateLimitItem, *parts: str) -> bool:
    key = ":".join(str(part) for part in parts)
    return _limiter.hit(rate, key)


def _raise_limited() -> None:
    raise HTTPException(status_code=429, detail="Too many requests; please slow down.")


def _public_ip_from_xff(header: str) -> str | None:
    for raw in header.split(","):
        candidate = raw.strip()
        try:
            parsed = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if parsed.is_global:
            return candidate
    return None


def identify_request(request: Request) -> RequestIdentity:
    """Return the source identity for throttling.

    By default this uses the socket peer reported by ASGI. Deployments that sit
    behind a trusted proxy can opt into X-Forwarded-For parsing with
    TRUST_PROXY_HEADERS=1; only the left-most public address is accepted.
    """
    settings = get_settings()
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            public_ip = _public_ip_from_xff(forwarded)
            if public_ip:
                return RequestIdentity(source_ip=public_ip)
    host = request.client.host if request.client else "unknown"
    return RequestIdentity(source_ip=host)


def enforce_chat_request(identity: RequestIdentity, conversation_id: str) -> None:
    """Apply all cheap chat limits before database, RAG, or LLM work."""
    settings = get_settings()
    checks = [
        (_rate(settings.chat_rate_per_ip), "chat", "ip", identity.source_ip),
        (_rate(settings.chat_rate_global), "chat", "global"),
        (_rate(settings.chat_rate_per_conversation), "chat", "conversation", conversation_id),
        (_rate(settings.chat_budget_per_hour), "chat", "budget"),
    ]
    if not all(_check(rate, *parts) for rate, *parts in checks):
        _raise_limited()


def enforce_admin_login_request(identity: RequestIdentity) -> None:
    """Limit password attempts by source address."""
    settings = get_settings()
    if not _check(_rate(settings.admin_login_rate_per_ip), "admin-login", identity.source_ip):
        logger.warning("Admin login rate limit exceeded from source=%s", identity.source_ip)
        _raise_limited()


def enforce_push_request(identity: RequestIdentity, conversation_id: str) -> bool:
    """Return False when push quotas are exhausted."""
    settings = get_settings()
    checks = [
        (_rate(settings.pushover_rate_per_conversation), "push", "conversation", conversation_id),
        (_rate(settings.pushover_rate_per_ip), "push", "ip", identity.source_ip),
        (_rate(settings.pushover_rate_global), "push", "global"),
    ]
    return all(_check(rate, *parts) for rate, *parts in checks)
