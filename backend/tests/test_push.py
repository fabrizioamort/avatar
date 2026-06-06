"""Pushover sender hardening tests."""

from dataclasses import replace

from app import push
from app.config import get_settings


class _Response:
    status_code = 200

    def json(self):
        return {"status": 1}


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
