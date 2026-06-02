"""Measure retrieval quality against a small labelled eval set.

Reports hit@1, hit@3, and mean reciprocal rank. A retrieved chunk counts as a
match when its source_file is listed in ``expected_sources`` or any
``expected_headings`` substring appears in its heading path.

Usage:
    cd backend
    uv run python scripts/eval_retrieval.py
    uv run python scripts/eval_retrieval.py --eval-set scripts/eval_set.json --top-k 4
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import rag_service  # noqa: E402
from app.rag_service import RetrievedChunk  # noqa: E402


def matches(chunk: RetrievedChunk, expected_sources: list[str], expected_headings: list[str]) -> bool:
    """Whether a retrieved chunk satisfies an eval case's expectations."""
    if chunk.source_file in expected_sources:
        if not expected_headings:
            return True
        path = " > ".join(chunk.heading_path)
        return any(h.lower() in path.lower() for h in expected_headings)
    return False


def first_match_rank(chunks: list[RetrievedChunk], case: dict) -> int | None:
    """1-based rank of the first matching chunk, or None if none match."""
    sources = case.get("expected_sources", [])
    headings = case.get("expected_headings", [])
    for rank, chunk in enumerate(chunks, start=1):
        if matches(chunk, sources, headings):
            return rank
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality.")
    parser.add_argument("--eval-set", default=str(Path(__file__).parent / "eval_set.json"))
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    cases = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    hit1 = hit3 = 0
    reciprocal_sum = 0.0
    misses = 0

    for case in cases:
        chunks = rag_service.retrieve_knowledge(case["query"], top_k=args.top_k)
        rank = first_match_rank(chunks, case)
        best = f"{chunks[0].distance:.3f}" if chunks else "n/a"
        sources = ", ".join(c.heading_path[-1] for c in chunks) or "none"
        print(f"\nQ: {case['query']}")
        print(f"   best_distance={best} rank={rank} retrieved=[{sources}]")
        if rank is None:
            misses += 1
            continue
        if rank == 1:
            hit1 += 1
        if rank <= 3:
            hit3 += 1
        reciprocal_sum += 1.0 / rank

    n = len(cases)
    print("\n--- Summary ---")
    print(f"cases: {n}")
    print(f"hit@1: {hit1}/{n} = {hit1 / n:.2f}")
    print(f"hit@3: {hit3}/{n} = {hit3 / n:.2f}")
    print(f"MRR:   {reciprocal_sum / n:.3f}")
    print(f"no confident result: {misses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
