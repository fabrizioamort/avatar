"""Chat-flow RAG integration tests using mocked retrieval and a mocked agent.

These avoid live embedding / vector search / LLM calls: retrieval and the agent
stream are stubbed so the focus is the wiring in `_chat_events`.
"""

import json

from app import agent, rag_service
from app.rag_service import RetrievedChunk


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
        if lines:
            events.append(json.loads("".join(lines)))
    return events


def _post_chat(
    client,
    conversation_id: str,
    visitor_token: str,
    message: str,
    language: str | None = None,
) -> list[dict]:
    body = {
        "conversation_id": conversation_id,
        "conversation_token": visitor_token,
        "message": message,
        "visitor_name": "ZZ",
    }
    if language is not None:
        body["language"] = language
    with client.stream(
        "POST",
        "/api/chat",
        json=body,
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    return _parse_sse(body)


def test_qn_bypasses_rag(client, conversation_id, visitor_token, monkeypatch):
    """A bare Qn instant answer must not trigger retrieval or the agent."""
    called = {"retrieve": False, "stream": False}

    def fake_retrieve(*args, **kwargs):
        called["retrieve"] = True
        return []

    async def fake_stream(*args, **kwargs):
        called["stream"] = True
        yield {"type": "_final", "text": "", "tool_calls": []}

    monkeypatch.setattr(rag_service, "retrieve_knowledge", fake_retrieve)
    monkeypatch.setattr(agent, "stream_agent", fake_stream)

    events = _post_chat(client, conversation_id, visitor_token, "Q2")
    types = [e["type"] for e in events]
    assert "instant" in types
    assert types[-1] == "done"
    assert called["retrieve"] is False
    assert called["stream"] is False


def test_chat_retrieves_and_passes_context_to_agent(client, conversation_id, visitor_token, monkeypatch):
    """A normal message retrieves context and forwards it to the agent stream."""
    captured = {}

    def fake_retrieve(query, **kwargs):
        captured["query"] = query
        return [
            RetrievedChunk(
                id="c1",
                title="Profile",
                source_file="knowledge/knowledge.md",
                heading_path=["Profile"],
                content="body",
                prompt_text="## Profile\nFabrizio is a GenAI Architect.",
                category="general",
                distance=0.2,
                priority=0,
            )
        ]

    async def fake_stream(transcript, retrieved_knowledge="", language="en"):
        captured["transcript"] = transcript
        captured["retrieved"] = retrieved_knowledge
        captured["language"] = language
        yield {"type": "token", "text": "Hi"}
        yield {"type": "_final", "text": "Hi there", "tool_calls": []}

    monkeypatch.setattr(rag_service, "retrieve_knowledge", fake_retrieve)
    monkeypatch.setattr(agent, "stream_agent", fake_stream)

    events = _post_chat(client, conversation_id, visitor_token, "Tell me about your work")
    types = [e["type"] for e in events]
    assert "token" in types
    assert types[-1] == "done"

    assert captured["query"] == "Tell me about your work"
    assert "GenAI Architect" in captured["retrieved"]  # formatted prompt_text reached the agent
    assert captured["language"] == "en"

    from app import db

    rows = db.get_messages(conversation_id)
    assert rows[-1]["role"] == "avatar"
    assert rows[-1]["content"] == "Hi there"


def test_chat_falls_back_to_static_knowledge_when_no_chunks(
    client,
    conversation_id,
    visitor_token,
    monkeypatch,
):
    """When retrieval returns nothing, the static profile is used as a fallback."""
    captured = {}

    monkeypatch.setattr(rag_service, "retrieve_knowledge", lambda *a, **k: [])

    async def fake_stream(transcript, retrieved_knowledge="", language="en"):
        captured["retrieved"] = retrieved_knowledge
        captured["language"] = language
        yield {"type": "_final", "text": "ok", "tool_calls": []}

    monkeypatch.setattr(agent, "stream_agent", fake_stream)

    _post_chat(client, conversation_id, visitor_token, "Anything at all")
    from app import knowledge

    assert captured["retrieved"] == knowledge.knowledge_text()
    assert captured["language"] == "en"


def test_chat_passes_italian_language_to_agent(client, conversation_id, visitor_token, monkeypatch):
    """The selected frontend language reaches prompt construction through the agent stream."""
    captured = {}

    monkeypatch.setattr(rag_service, "retrieve_knowledge", lambda *a, **k: [])

    async def fake_stream(transcript, retrieved_knowledge="", language="en"):
        captured["transcript"] = transcript
        captured["retrieved"] = retrieved_knowledge
        captured["language"] = language
        yield {"type": "_final", "text": "ok", "tool_calls": []}

    monkeypatch.setattr(agent, "stream_agent", fake_stream)

    _post_chat(client, conversation_id, visitor_token, "Ciao, raccontami di te", language="it")

    assert captured["language"] == "it"
