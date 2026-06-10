"""Application settings loaded from the project-root .env file."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    """Read an env var, stripping surrounding quotes.

    python-dotenv strips quotes from .env values, but Docker's --env-file keeps
    them, so the same .env must be normalised here to work both ways.
    """
    value = os.getenv(name, default)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


@dataclass(frozen=True)
class Settings:
    """Frozen view of the environment values the app needs."""

    openrouter_api_key: str
    model: str
    owner_name: str
    admin_password: str
    pushover_user: str
    pushover_token: str
    gcp_project_id: str
    firestore_database: str
    session_secret: str
    environment: str
    cookie_secure: bool
    frontend_dist: Path
    knowledge_dir: Path
    rag_enabled: bool
    rag_top_k: int
    rag_max_distance: float
    rag_context_max_chars: int
    rag_embedding_model: str
    rag_embedding_dim: int
    rag_embedding_location: str
    rag_log_queries: bool
    trust_proxy_headers: bool
    chat_rate_per_ip: str
    chat_rate_global: str
    chat_rate_per_conversation: str
    chat_budget_per_hour: str
    admin_login_rate_per_ip: str
    max_message_chars: int
    max_conversation_messages: int
    max_transcript_chars: int
    visitor_session_max_age_seconds: int
    pushover_message_max_chars: int
    pushover_timeout_connect_seconds: float
    pushover_timeout_read_seconds: float
    pushover_rate_per_conversation: str
    pushover_rate_per_ip: str
    pushover_rate_global: str


def _require_secret(name: str, *, min_length: int) -> str:
    value = _env(name)
    if not value.strip():
        raise ValueError(f"{name} must be set and non-blank.")
    if len(value) < min_length:
        raise ValueError(f"{name} must be at least {min_length} characters long.")
    return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings read from the environment."""
    environment = _env("ENVIRONMENT", "production").lower()
    admin_password = _require_secret("ADMIN_PASSWORD", min_length=8)
    session_secret = _require_secret("SESSION_SECRET", min_length=32)
    if environment == "production" and not _env("SESSION_SECRET").strip():
        raise ValueError("SESSION_SECRET must be set in production.")
    firestore_database = _env("FIRESTORE_DATABASE", "(default)")
    if firestore_database != "(default)":
        raise ValueError(
            "FIRESTORE_DATABASE must be '(default)'; the Firestore free quota only "
            f"applies to the default database (got {firestore_database!r})."
        )
    return Settings(
        openrouter_api_key=_env("OPENROUTER_API_KEY"),
        model=_env("MODEL", "openai/gpt-5.4-nano"),
        owner_name=_env("OWNER_NAME", "Ed Donner"),
        admin_password=admin_password,
        pushover_user=_env("PUSHOVER_USER"),
        pushover_token=_env("PUSHOVER_TOKEN"),
        gcp_project_id=_env("GOOGLE_CLOUD_PROJECT") or _env("GCP_PROJECT_ID"),
        firestore_database=firestore_database,
        session_secret=session_secret,
        environment=environment,
        cookie_secure=_env("COOKIE_SECURE") == "1",
        frontend_dist=Path(_env("FRONTEND_DIST") or REPO_ROOT / "frontend" / "dist"),
        knowledge_dir=Path(_env("KNOWLEDGE_DIR") or REPO_ROOT / "knowledge"),
        rag_enabled=_env("RAG_ENABLED", "true").lower() not in ("0", "false", "no"),
        rag_top_k=int(_env("RAG_TOP_K", "4")),
        rag_max_distance=float(_env("RAG_MAX_DISTANCE", "0.65")),
        rag_context_max_chars=int(_env("RAG_CONTEXT_MAX_CHARS", "12000")),
        rag_embedding_model=_env("RAG_EMBEDDING_MODEL", "gemini-embedding-001"),
        rag_embedding_dim=int(_env("RAG_EMBEDDING_DIM", "768")),
        rag_embedding_location=_env("RAG_EMBEDDING_LOCATION", "global"),
        rag_log_queries=_env("RAG_LOG_QUERIES", "0").lower() in ("1", "true", "yes"),
        trust_proxy_headers=_env("TRUST_PROXY_HEADERS", "0").lower() in ("1", "true", "yes"),
        chat_rate_per_ip=_env("CHAT_RATE_PER_IP", "30/minute"),
        chat_rate_global=_env("CHAT_RATE_GLOBAL", "180/minute"),
        chat_rate_per_conversation=_env("CHAT_RATE_PER_CONVERSATION", "20/minute"),
        chat_budget_per_hour=_env("CHAT_BUDGET_PER_HOUR", "600/hour"),
        admin_login_rate_per_ip=_env("ADMIN_LOGIN_RATE_PER_IP", "5/minute"),
        max_message_chars=int(_env("MAX_MESSAGE_CHARS", "4000")),
        max_conversation_messages=int(_env("MAX_CONVERSATION_MESSAGES", "80")),
        max_transcript_chars=int(_env("MAX_TRANSCRIPT_CHARS", "12000")),
        visitor_session_max_age_seconds=int(_env("VISITOR_SESSION_MAX_AGE_SECONDS", "604800")),
        pushover_message_max_chars=int(_env("PUSHOVER_MESSAGE_MAX_CHARS", "512")),
        pushover_timeout_connect_seconds=float(_env("PUSHOVER_TIMEOUT_CONNECT_SECONDS", "2")),
        pushover_timeout_read_seconds=float(_env("PUSHOVER_TIMEOUT_READ_SECONDS", "5")),
        pushover_rate_per_conversation=_env("PUSHOVER_RATE_PER_CONVERSATION", "2/hour"),
        pushover_rate_per_ip=_env("PUSHOVER_RATE_PER_IP", "5/hour"),
        pushover_rate_global=_env("PUSHOVER_RATE_GLOBAL", "20/day"),
    )
