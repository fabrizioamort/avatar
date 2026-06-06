"""Settings env parsing, including the Docker --env-file quote gotcha."""

import pytest

from app.config import _env, get_settings


def test_env_strips_surrounding_double_quotes(monkeypatch):
    monkeypatch.setenv("AVATAR_T", '"openai/gpt-5.4-nano"')
    assert _env("AVATAR_T") == "openai/gpt-5.4-nano"


def test_env_strips_surrounding_single_quotes(monkeypatch):
    monkeypatch.setenv("AVATAR_T", "'Ed Donner'")
    assert _env("AVATAR_T") == "Ed Donner"


def test_env_keeps_inner_quotes_and_unquoted(monkeypatch):
    monkeypatch.setenv("AVATAR_T", 'say "hi"')
    assert _env("AVATAR_T") == 'say "hi"'
    monkeypatch.setenv("AVATAR_T", "plain")
    assert _env("AVATAR_T") == "plain"


def test_env_default_when_missing(monkeypatch):
    monkeypatch.delenv("AVATAR_MISSING", raising=False)
    assert _env("AVATAR_MISSING", "fallback") == "fallback"


def test_blank_admin_password_raises(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-32-random-chars")
    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        get_settings()
    get_settings.cache_clear()


def test_blank_session_secret_raises(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password-32-chars")
    monkeypatch.setenv("SESSION_SECRET", "")
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        get_settings()
    get_settings.cache_clear()
