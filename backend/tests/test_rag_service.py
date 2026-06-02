"""Tests for rag_service formatting (no live Firestore or embedding calls)."""

from app.rag_service import RetrievedChunk, format_retrieved_context


def _chunk(prompt_text: str, distance: float) -> RetrievedChunk:
    return RetrievedChunk(
        id="x",
        title="T",
        source_file="knowledge/k.md",
        heading_path=["T", "S"],
        content=prompt_text,
        prompt_text=prompt_text,
        category="general",
        distance=distance,
        priority=0,
    )


def test_format_empty():
    assert format_retrieved_context([]) == ""


def test_format_joins_prompt_texts():
    chunks = [_chunk("First block", 0.1), _chunk("Second block", 0.2)]
    out = format_retrieved_context(chunks)
    assert "First block" in out
    assert "Second block" in out
    assert "\n\n" in out


def test_format_respects_char_budget():
    chunks = [_chunk("A" * 100, 0.1), _chunk("B" * 100, 0.2), _chunk("C" * 100, 0.3)]
    out = format_retrieved_context(chunks, max_chars=150)
    # Only the first block fits under the budget; later ones are dropped.
    assert "A" * 100 in out
    assert "B" * 100 not in out


def test_format_keeps_at_least_first_chunk():
    chunks = [_chunk("Z" * 500, 0.1)]
    out = format_retrieved_context(chunks, max_chars=10)
    assert "Z" * 500 in out
