"""Tests for system-prompt assembly (no model call)."""

from app import agent, knowledge
from app import abuse
from app.config import get_settings
from app.models import Message


def test_build_system_prompt_includes_retrieved_knowledge_and_style():
    retrieved = "## Profile\nFabrizio is a GenAI Architect at TIM."
    prompt = agent.build_system_prompt(retrieved)
    owner = get_settings().owner_name
    assert owner in prompt
    assert retrieved in prompt  # the retrieved chunk text is injected
    assert "self-deprecating" in prompt  # from style.md
    assert "faq_tool" in prompt  # FAQ section + tool usage


def test_build_system_prompt_defaults_to_english():
    prompt = agent.build_system_prompt("## Profile\nContext")
    assert "Reply in English unless the visitor explicitly asks" in prompt


def test_build_system_prompt_can_request_italian():
    prompt = agent.build_system_prompt("## Profile\nContext", language="it")
    assert "Reply in Italian unless the visitor explicitly asks" in prompt


def test_build_system_prompt_does_not_inject_full_knowledge_by_default():
    """Without retrieved context the full static profile is no longer dumped in."""
    prompt = agent.build_system_prompt()
    assert knowledge.knowledge_text() not in prompt


def test_old_sources_removed():
    """The LinkedIn PDF and summary loaders are gone; the prompt no longer references them."""
    assert not hasattr(knowledge, "linkedin_text")
    assert not hasattr(knowledge, "summary_text")
    assert "LinkedIn profile" not in agent.build_system_prompt()


def test_render_transcript_respects_max_chars():
    rows = [
        Message(
            id=i,
            conversation_id="c1",
            role="visitor",
            content=f"message {i} " + ("x" * 200),
            created_at="2026-01-01T00:00:00+00:00",
        )
        for i in range(20)
    ]
    rendered = agent.render_transcript(rows, "Owner", max_chars=500)
    assert len(rendered) <= 500
    assert rendered.endswith("Reply as the Avatar:")


def test_push_tool_blocks_without_context(monkeypatch):
    called = {"push": False}
    monkeypatch.setattr(agent, "push", lambda message: called.update(push=True))
    result = agent.handle_push_tool("hello")
    assert "could not be delivered" in result
    assert called["push"] is False


def test_push_tool_quota_blocks_before_pushover(monkeypatch):
    called = {"push": False}
    tokens = agent.set_push_context("c1", "127.0.0.1")
    try:
        monkeypatch.setattr(abuse, "enforce_push_request", lambda *a, **k: False)
        monkeypatch.setattr(agent, "push", lambda message: called.update(push=True))
        result = agent.handle_push_tool("hello")
    finally:
        agent.reset_push_context(tokens)
    assert "rate limit" in result.lower()
    assert called["push"] is False
