"""Abuse guards: input caps, rate limits, and pre-paid-work rejection."""

from dataclasses import replace

from app import abuse, agent, db, rag_service
from app.auth import issue_visitor_token
from app.config import get_settings
from app.main import (
    MAX_MESSAGE_CHARS,
    TRUNCATION_NOTE,
    clamp_message,
)


def test_clamp_message_leaves_short_text_unchanged():
    text = "a normal length question about your courses"
    assert clamp_message(text) == text


def test_clamp_message_boundary_is_inclusive():
    exactly = "x" * MAX_MESSAGE_CHARS
    assert clamp_message(exactly) == exactly
    assert clamp_message(exactly + "x") != exactly + "x"


def test_clamp_message_truncates_and_appends_note():
    text = "y" * (MAX_MESSAGE_CHARS + 5_000)
    clamped = clamp_message(text)
    assert clamped == "y" * MAX_MESSAGE_CHARS + " " + TRUNCATION_NOTE
    assert clamped.endswith(TRUNCATION_NOTE)
    # the original content is capped at the limit (the note is the only extra)
    assert len(clamped) == MAX_MESSAGE_CHARS + 1 + len(TRUNCATION_NOTE)


def _rate_settings(**overrides):
    settings = replace(get_settings(), **overrides)
    return lambda: settings


def _chat_body(conversation_id: str, token: str, message: str = "Q2") -> dict:
    return {
        "conversation_id": conversation_id,
        "conversation_token": token,
        "message": message,
        "visitor_name": "RL",
    }


def test_chat_rate_defaults_are_layered():
    settings = get_settings()
    assert settings.chat_rate_per_ip
    assert settings.chat_rate_global
    assert settings.chat_rate_per_conversation
    assert settings.chat_budget_per_hour


def test_rate_limit_returns_429_after_the_cap(client, conversation_id, visitor_token, monkeypatch):
    """The (N+1)th message from one conversation_id is rejected with 429, no model call."""
    monkeypatch.setattr(
        abuse,
        "get_settings",
        _rate_settings(chat_rate_per_conversation="3/minute"),
    )

    body = _chat_body(conversation_id, visitor_token)
    for _ in range(3):
        assert client.post("/api/chat", json=body).status_code == 200  # instant, no LLM

    blocked = client.post("/api/chat", json=body)
    assert blocked.status_code == 429
    assert "slow down" in blocked.json()["detail"].lower()


def test_rotating_conversation_ids_does_not_bypass_ip_limit(client, monkeypatch):
    """A new conversation_id still shares the same source-IP budget."""
    monkeypatch.setattr(
        abuse,
        "get_settings",
        _rate_settings(chat_rate_per_ip="1/minute"),
    )
    import uuid

    cids = [str(uuid.uuid4()), str(uuid.uuid4())]
    try:
        first_token = issue_visitor_token(cids[0])
        second_token = issue_visitor_token(cids[1])
        assert client.post("/api/chat", json=_chat_body(cids[0], first_token)).status_code == 200
        blocked = client.post("/api/chat", json=_chat_body(cids[1], second_token))
        assert blocked.status_code == 429
    finally:
        for cid in cids:
            db.delete_conversation(cid)


def test_missing_chat_token_rejected_before_paid_work(client, conversation_id, monkeypatch):
    called = {"insert": False, "retrieve": False, "stream": False}

    def fake_insert(*args, **kwargs):
        called["insert"] = True
        raise AssertionError("insert_message should not be called")

    def fake_retrieve(*args, **kwargs):
        called["retrieve"] = True
        raise AssertionError("retrieve_knowledge should not be called")

    async def fake_stream(*args, **kwargs):
        called["stream"] = True
        raise AssertionError("stream_agent should not be called")
        yield {}

    monkeypatch.setattr(db, "insert_message", fake_insert)
    monkeypatch.setattr(rag_service, "retrieve_knowledge", fake_retrieve)
    monkeypatch.setattr(agent, "stream_agent", fake_stream)

    response = client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "message": "hello", "visitor_name": "RL"},
    )

    assert response.status_code == 403
    assert called == {"insert": False, "retrieve": False, "stream": False}


def test_rate_limiter_rejects_before_paid_work(client, conversation_id, visitor_token, monkeypatch):
    monkeypatch.setattr(
        abuse,
        "get_settings",
        _rate_settings(chat_rate_per_ip="1/minute"),
    )
    assert client.post("/api/chat", json=_chat_body(conversation_id, visitor_token)).status_code == 200

    called = {"insert": False, "retrieve": False, "stream": False}
    monkeypatch.setattr(db, "insert_message", lambda *a, **k: called.update(insert=True))
    monkeypatch.setattr(rag_service, "retrieve_knowledge", lambda *a, **k: called.update(retrieve=True))

    async def fake_stream(*args, **kwargs):
        called["stream"] = True
        yield {"type": "_final", "text": "", "tool_calls": []}

    monkeypatch.setattr(agent, "stream_agent", fake_stream)
    blocked = client.post("/api/chat", json=_chat_body(conversation_id, visitor_token))
    assert blocked.status_code == 429
    assert called == {"insert": False, "retrieve": False, "stream": False}


def test_conversation_message_limit_rejects_before_llm_work(
    client,
    conversation_id,
    visitor_token,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.main.get_settings",
        _rate_settings(max_conversation_messages=0),
    )
    called = {"insert": False, "retrieve": False, "stream": False}
    monkeypatch.setattr(db, "insert_message", lambda *a, **k: called.update(insert=True))
    monkeypatch.setattr(rag_service, "retrieve_knowledge", lambda *a, **k: called.update(retrieve=True))

    async def fake_stream(*args, **kwargs):
        called["stream"] = True
        yield {"type": "_final", "text": "", "tool_calls": []}

    monkeypatch.setattr(agent, "stream_agent", fake_stream)

    blocked = client.post("/api/chat", json=_chat_body(conversation_id, visitor_token, "hello"))
    assert blocked.status_code == 429
    assert called == {"insert": False, "retrieve": False, "stream": False}
