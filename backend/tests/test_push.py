"""Pushover sender hardening tests."""

from dataclasses import replace

from app import push
from app.config import get_settings


class _Response:
    status_code = 200
    text = '{"status":1}'

    def json(self):
        return {"status": 1}


class _BadJsonResponse:
    status_code = 502
    text = "bad gateway"

    def json(self):
        raise ValueError("not json")


def test_push_posts_with_timeout_and_truncates(monkeypatch):
    settings = replace(
        get_settings(),
        pushover_message_max_chars=10,
        pushover_timeout_connect_seconds=1.5,
        pushover_timeout_read_seconds=4.5,
    )
    captured = {}

    def fake_post(url, data, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(push, "get_settings", lambda: settings)
    monkeypatch.setattr(push.requests, "post", fake_post)

    result = push.push("x" * 20)

    assert result == "Message delivered to the human owner."
    assert captured["timeout"] == (1.5, 4.5)
    assert captured["data"]["message"] == "x" * 10 + "..."


def test_push_skips_request_without_credentials(monkeypatch):
    settings = replace(get_settings(), pushover_user="", pushover_token="")
    called = {"post": False}

    def fake_post(*args, **kwargs):
        called["post"] = True

    monkeypatch.setattr(push, "get_settings", lambda: settings)
    monkeypatch.setattr(push.requests, "post", fake_post)

    result = push.push("hello")

    assert result == "Notification could not be delivered to the human owner."
    assert called["post"] is False


def test_push_handles_non_json_response(monkeypatch):
    monkeypatch.setattr(push.requests, "post", lambda *a, **k: _BadJsonResponse())

    result = push.push("hello")

    assert result == "Notification could not be delivered to the human owner."
