"""Tests for the public API: config and conversation retrieval."""

import os

from app.models import ChatRequest
from tests.conftest import make_conversation


def test_config_returns_owner_name(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["owner_name"] == os.environ.get("OWNER_NAME", "Ed Donner")


def test_create_conversation_returns_signed_session(client):
    response = client.post("/api/conversations")
    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"]
    assert body["conversation_token"]


def test_chat_request_language_defaults_to_english():
    request = ChatRequest(conversation_id="c1", conversation_token="t1", message="hello")
    assert request.language == "en"


def test_chat_request_language_accepts_supported_values():
    assert ChatRequest(
        conversation_id="c1",
        conversation_token="t1",
        message="ciao",
        language="it",
    ).language == "it"
    assert ChatRequest(
        conversation_id="c1",
        conversation_token="t1",
        message="ciao",
        language="it-IT",
    ).language == "it"


def test_chat_request_language_invalid_values_fall_back_to_english():
    request = ChatRequest(
        conversation_id="c1",
        conversation_token="t1",
        message="hello",
        language="fr",
    )
    assert request.language == "en"


def test_get_conversation_without_token_rejected(client, conversation_id):
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 401


def test_get_conversation_with_wrong_token_rejected(client, conversation_id):
    session = client.post("/api/conversations").json()
    response = client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-Avatar-Conversation-Token": session["conversation_token"]},
    )
    assert response.status_code == 403


def test_chat_with_wrong_token_rejected(client, conversation_id):
    session = client.post("/api/conversations").json()
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "conversation_token": session["conversation_token"],
            "message": "hello",
        },
    )
    assert response.status_code == 403


def test_get_conversation_returns_messages(client, conversation_id, visitor_token):
    make_conversation(
        conversation_id,
        [
            {"role": "visitor", "content": "hello there", "conversation_name": "AB"},
            {"role": "avatar", "content": "hi, how can I help"},
        ],
    )
    response = client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-Avatar-Conversation-Token": visitor_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == conversation_id
    assert body["conversation_name"] == "AB"
    assert [m["role"] for m in body["messages"]] == ["visitor", "avatar"]
    assert body["messages"][0]["content"] == "hello there"


def test_get_conversation_after_filter(client, conversation_id, visitor_token):
    rows = make_conversation(
        conversation_id,
        [
            {"role": "visitor", "content": "first"},
            {"role": "avatar", "content": "second"},
            {"role": "visitor", "content": "third"},
        ],
    )
    first_id = rows[0]["id"]
    response = client.get(
        f"/api/conversations/{conversation_id}?after={first_id}",
        headers={"X-Avatar-Conversation-Token": visitor_token},
    )
    contents = [m["content"] for m in response.json()["messages"]]
    assert contents == ["second", "third"]
