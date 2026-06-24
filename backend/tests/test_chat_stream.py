"""SSE chat tests. The model-calling cases are marked 'llm' (cost tokens)."""

import json

import pytest

from app import agent, db, rag_service


def _parse_sse(text: str) -> list[dict]:
    """Parse an SSE response body into a list of JSON event dicts."""
    events = []
    for block in text.strip().split("\n\n"):
        lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
        if lines:
            events.append(json.loads("".join(lines)))
    return events


def test_instant_answer_no_model(client, conversation_id, visitor_token):
    """A bare Qn message returns an instant event and the answer with no model call."""
    with client.stream(
        "POST",
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "conversation_token": visitor_token,
            "message": "Q2",
            "visitor_name": "EF",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    events = _parse_sse(body)
    types = [e["type"] for e in events]
    assert "instant" in types
    assert types[-1] == "done"
    assert events[0]["faq"] == 2

    rows = db.get_messages(conversation_id)
    assert [r["role"] for r in rows] == ["visitor", "avatar"]
    assert rows[1]["tool_calls"] == [{"type": "instant", "faq": 2}]


@pytest.mark.llm
def test_chat_streams_tokens_and_persists(client, conversation_id, visitor_token):
    """A plain message streams token events, a done event, and persists the avatar row."""
    with client.stream(
        "POST",
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "conversation_token": visitor_token,
            "message": "In one short sentence, who is this digital twin?",
            "visitor_name": "GH",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    events = _parse_sse(body)
    types = [e["type"] for e in events]
    assert "token" in types
    assert types[-1] == "done"

    rows = db.get_messages(conversation_id)
    assert rows[-1]["role"] == "avatar"
    assert rows[-1]["content"]


def test_chat_contact_intent_triggers_push_before_email(
    client,
    conversation_id,
    visitor_token,
    monkeypatch,
):
    """Asking to get in touch immediately notifies the owner and asks for contact details."""
    called = {}

    def fake_push(message):
        called["push_message"] = message
        return "Message delivered to the human owner."

    def fail_retrieve(*args, **kwargs):
        raise AssertionError("contact intent should not run retrieval")

    async def fail_stream(*args, **kwargs):
        raise AssertionError("contact intent should not call the LLM")
        yield {}

    monkeypatch.setattr(agent, "handle_push_tool", fake_push)
    monkeypatch.setattr(rag_service, "retrieve_knowledge", fail_retrieve)
    monkeypatch.setattr(agent, "stream_agent", fail_stream)

    with client.stream(
        "POST",
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "conversation_token": visitor_token,
            "message": "Vorrei mettermi in contatto con Fabrizio per una consulenza.",
            "language": "it",
            "visitor_name": "IJ",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    events = _parse_sse(body)
    done = events[-1]
    assert events[0] == {"type": "tool", "phase": "called", "tool": "push_tool"}
    assert events[1]["type"] == "token"
    assert "Ho avvisato" in events[1]["text"]
    assert "email" in events[1]["text"]
    assert done["type"] == "done"
    assert done["needs_attention"] is True

    assert "mettermi in contatto" in called["push_message"]
    rows = db.get_messages(conversation_id)
    assert [r["role"] for r in rows] == ["visitor", "avatar"]
    assert rows[-1]["tool_calls"] == [{"tool": "push_tool", "trigger": "contact_intent"}]
    assert rows[-1]["needs_attention"] is True
    assert rows[-1]["read"] is False
