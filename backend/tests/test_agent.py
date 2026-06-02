"""Tests for system-prompt assembly (no model call)."""

from app import agent, knowledge
from app.config import get_settings


def test_build_system_prompt_includes_retrieved_knowledge_and_style():
    retrieved = "## Profile\nFabrizio is a GenAI Architect at TIM."
    prompt = agent.build_system_prompt(retrieved)
    owner = get_settings().owner_name
    assert owner in prompt
    assert retrieved in prompt  # the retrieved chunk text is injected
    assert "self-deprecating" in prompt  # from style.md
    assert "faq_tool" in prompt  # FAQ section + tool usage


def test_build_system_prompt_does_not_inject_full_knowledge_by_default():
    """Without retrieved context the full static profile is no longer dumped in."""
    prompt = agent.build_system_prompt()
    assert knowledge.knowledge_text() not in prompt


def test_old_sources_removed():
    """The LinkedIn PDF and summary loaders are gone; the prompt no longer references them."""
    assert not hasattr(knowledge, "linkedin_text")
    assert not hasattr(knowledge, "summary_text")
    assert "LinkedIn profile" not in agent.build_system_prompt()
