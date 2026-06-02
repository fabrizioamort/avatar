"""Retrieve relevant owner-knowledge chunks via Firestore Vector Search.

Firestore cosine search returns a *distance* (lower is more similar), so results
are sorted ascending by distance and filtered by ``rag_max_distance``.
"""

import json
import logging
import time
from dataclasses import dataclass

from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from app import db, embeddings
from app.config import get_settings

KNOWLEDGE_CHUNKS = "knowledge_chunks"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    """A knowledge chunk returned from vector search, with its distance."""

    id: str
    title: str
    source_file: str
    heading_path: list[str]
    content: str
    prompt_text: str
    category: str
    distance: float
    priority: int


def retrieve_knowledge(
    query: str,
    *,
    top_k: int | None = None,
    max_distance: float | None = None,
    category: str | None = None,
) -> list[RetrievedChunk]:
    """Return active chunks nearest to ``query``, sorted by ascending distance."""
    settings = get_settings()
    top_k = top_k if top_k is not None else settings.rag_top_k
    max_distance = max_distance if max_distance is not None else settings.rag_max_distance

    start = time.perf_counter()
    query_vector = embeddings.embed_query(query)
    query_ref = db.get_client().collection(KNOWLEDGE_CHUNKS).where(
        filter=FieldFilter("is_active", "==", True)
    )
    if category:
        query_ref = query_ref.where(filter=FieldFilter("category", "==", category))

    vector_query = query_ref.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_vector),
        distance_measure=DistanceMeasure.COSINE,
        limit=top_k,
        distance_result_field="vector_distance",
        distance_threshold=max_distance,
    )

    results = []
    for doc in vector_query.stream():
        data = doc.to_dict()
        results.append(
            RetrievedChunk(
                id=data["id"],
                title=data.get("title", ""),
                source_file=data.get("source_file", ""),
                heading_path=list(data.get("heading_path", [])),
                content=data.get("content", ""),
                prompt_text=data.get("prompt_text", ""),
                category=data.get("category", ""),
                distance=float(data.get("vector_distance", 0.0)),
                priority=int(data.get("priority", 0)),
            )
        )
    results.sort(key=lambda c: c.distance)
    _log_retrieval(query, top_k, results, round((time.perf_counter() - start) * 1000, 1))
    return results


def _log_retrieval(query: str, top_k: int, results: list[RetrievedChunk], latency_ms: float) -> None:
    """One structured log line per retrieval. The raw query is gated by config.

    Visitor queries can contain personal information, so the query text is only
    logged when ``RAG_LOG_QUERIES`` is enabled.
    """
    record = {
        "event": "rag_retrieval",
        "query_chars": len(query),
        "top_k": top_k,
        "result_count": len(results),
        "best_distance": results[0].distance if results else None,
        "latency_ms": latency_ms,
        "sources": [r.source_file for r in results],
    }
    if get_settings().rag_log_queries:
        record["query"] = query
    logger.info("rag_retrieval %s", json.dumps(record))


def format_retrieved_context(
    chunks: list[RetrievedChunk], *, max_chars: int | None = None
) -> str:
    """Join chunk prompt texts into prompt context, truncated to a char budget."""
    if not chunks:
        return ""
    max_chars = max_chars if max_chars is not None else get_settings().rag_context_max_chars
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        block = chunk.prompt_text.strip()
        added = len(block) + (2 if parts else 0)
        if parts and used + added > max_chars:
            break
        parts.append(block)
        used += added
    return "\n\n".join(parts)
