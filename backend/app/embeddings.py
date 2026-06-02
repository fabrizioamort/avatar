"""Google embedding client (Vertex AI via ADC) for RAG document/query vectors.

Documents are embedded with task type RETRIEVAL_DOCUMENT and queries with
RETRIEVAL_QUERY, both at the configured output dimensionality. Cosine distance
is scale invariant, so the sub-3072 vectors do not need manual normalisation.
"""

from functools import lru_cache

from google import genai
from google.genai.types import EmbedContentConfig

from app.config import get_settings


@lru_cache
def _client() -> genai.Client:
    """Cached Vertex AI genai client authenticated via ADC."""
    settings = get_settings()
    kwargs: dict = {"vertexai": True, "location": settings.rag_embedding_location}
    if settings.gcp_project_id:
        kwargs["project"] = settings.gcp_project_id
    return genai.Client(**kwargs)


def _embed(text: str, task_type: str) -> list[float]:
    """Embed a single text and validate the returned dimensionality."""
    settings = get_settings()
    response = _client().models.embed_content(
        model=settings.rag_embedding_model,
        contents=text,
        config=EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=settings.rag_embedding_dim,
        ),
    )
    vector = list(response.embeddings[0].values)
    if len(vector) != settings.rag_embedding_dim:
        raise ValueError(
            f"Embedding model {settings.rag_embedding_model} returned "
            f"{len(vector)} dimensions, expected {settings.rag_embedding_dim}."
        )
    return vector


def embed_document(text: str) -> list[float]:
    """Embedding for a knowledge chunk to be stored and searched against."""
    return _embed(text, "RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """Embedding for a visitor query used to retrieve relevant chunks."""
    return _embed(text, "RETRIEVAL_QUERY")
