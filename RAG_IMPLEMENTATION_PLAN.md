# Avatar RAG Implementation Plan

## Overview

This plan evolves Avatar from a single static `knowledge/knowledge.md` file in the system prompt to a Retrieval-Augmented Generation (RAG) system backed by Firestore Vector Search.

The goal is not to change the visitor/admin API contract. The chat endpoint should still stream the same SSE event types, preserve the existing `Qn` instant FAQ shortcut, preserve `faq_tool` and `push_tool`, and keep the human-in-the-loop conversation semantics unchanged.

**Status:** Planning phase  
**Date:** 2026-06-02  
**Technology Stack:** FastAPI + OpenAI Agents SDK through OpenRouter + Firestore Vector Search + Vertex AI / Google embedding model

## Current Codebase Constraints

The implementation must align with the current project, not an older draft:

- Chat streaming lives in `backend/app/main.py`, specifically `_chat_events()`.
- Agent prompt construction lives in `backend/app/agent.py`, specifically `build_system_prompt()` and `build_agent()`.
- Static knowledge loading lives in `backend/app/knowledge.py`.
- Firestore access is centralized in `backend/app/db.py`; keep that module as the only low-level Firestore access layer, or create a similarly narrow `rag_store.py` if the vector API makes that cleaner.
- `FIRESTORE_DATABASE` must remain `(default)`. The app rejects any other value, and the free quota only applies to the default database.
- `knowledge/style.md` remains static prompt guidance and is not embedded.
- `knowledge/faq.jsonl` remains special. Bare `Qn` messages bypass both RAG and the LLM. The existing `faq_tool` remains available to the agent.

## Important Corrections From Review

### 1. Integrate With `agent.py`, Not `chat.py`

The earlier plan referenced `backend/app/chat.py`, but that file does not exist.

The RAG flow should be:

1. `POST /api/chat` enters `_chat_events()` in `backend/app/main.py`.
2. The visitor message is inserted as today.
3. If the message is a bare `Qn`, return the instant FAQ answer exactly as today.
4. Otherwise retrieve RAG context for the current turn.
5. Build the transcript as today with `agent.render_transcript()`.
6. Stream through `agent.stream_agent(transcript, retrieved_context=...)` or equivalent.

`agent.build_system_prompt()` should accept retrieved knowledge text, rather than reading all of `knowledge.md`.

### 2. Firestore Vector Search Returns Distance, Not Similarity

Firestore cosine search returns a **distance**. Lower is better. A cosine distance near `0` is highly similar.

Therefore:

- Rename `RAG_MIN_SIMILARITY` to `RAG_MAX_DISTANCE`.
- Do not sort descending by score.
- Sort ascending by vector distance.
- If using Firestore's threshold option, use `distance_threshold=RAG_MAX_DISTANCE`.
- If exposing a UI/debug score, either call it `distance` or compute `similarity = 1 - distance` for display only.

### 3. Use The Current Firestore Python API

The Python API shape is:

```python
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

vector_query = collection.find_nearest(
    vector_field="embedding",
    query_vector=Vector(query_embedding),
    distance_measure=DistanceMeasure.COSINE,
    limit=top_k,
    distance_result_field="vector_distance",
    distance_threshold=max_distance,
)

docs = vector_query.stream()
```

The previous pseudocode using `find_closest`, `k`, and `distance_type` should be removed.

### 4. Update Embedding Model Choice

Do not hardcode `text-embedding-004` or claim it is the current state-of-the-art default. Current Google docs list:

- `gemini-embedding-001`: highest quality, up to 3072 dimensions.
- `text-embedding-005`: English/code focused, up to 768 dimensions.
- `text-multilingual-embedding-002`: multilingual, up to 768 dimensions.

Firestore vector indexes support dimensions up to 2048, so if using `gemini-embedding-001`, set `output_dimensionality` to 768 or 1536.

Recommended default for Avatar:

```text
RAG_EMBEDDING_MODEL=gemini-embedding-001
RAG_EMBEDDING_DIM=768
RAG_EMBEDDING_LOCATION=global
```

`text-embedding-005` at 768 dimensions is also reasonable if you want the smaller English/code-specialized model.

### 5. Do Not Claim Embeddings Are Free

At Avatar's expected scale, embedding cost should be tiny, but it is still priced usage. Use budget alerts and keep a small expected-cost note rather than promising free tier coverage.

## Knowledge Architecture

The knowledge folder can still be expanded from one file into multiple owner-authored markdown files, but retrieval should happen at the **chunk** level, not the file level.

Recommended structure:

```text
knowledge/
  background/
    introduction.md
    career-journey.md
    education-credentials.md
  expertise/
    technical-skills.md
    system-design.md
    cloud-infrastructure.md
    leadership.md
    specializations.md
  projects/
    current/
      avatar.md
      active-work.md
    past/
      project-a.md
      project-b.md
  interests/
    learning-areas.md
    open-source.md
    teaching-mentoring.md
    public-presence.md
    values-principles.md
  problem-solving/
    approach-methodology.md
    case-studies.md
    failure-learnings.md
  availability/
    what-im-looking-for.md
    collaboration-model.md
  style.md
  faq.jsonl
  pic.jpg
```

Existing `knowledge/knowledge.md` can be kept as the source for the first migration. Phase 1 can chunk the existing file so the application gets RAG behavior before all new owner-authored files exist.

## Markdown Document Format

Use YAML frontmatter for metadata. This is easier to parse reliably than ad hoc bold fields.

Example:

```markdown
---
title: System Design and Architecture
category: expertise
tags:
  - architecture
  - scaling
  - cloud
priority: 0
updated: 2026-06-02
---

# System Design and Architecture

## Overview

First-person narrative with concrete examples, scope, scale, and lessons.

## Representative Work

Specific project or decision-making detail.

## Key Takeaway

One or two sentences that summarize why this matters.
```

## Chunking Strategy

Do not embed entire markdown files unless they are very short. Chunk by markdown heading:

- One chunk per `##` section.
- Include the document title and heading path in the embedded text.
- Target roughly 300-800 words per chunk.
- If a section exceeds the target, split by paragraphs.
- Store a `content_hash` so unchanged chunks are not re-embedded.
- Store `source_file`, `heading_path`, and `chunk_index` for debugging and evals.

Embedding text should include enough metadata for semantic retrieval:

```text
Title: System Design and Architecture
Category: expertise
Tags: architecture, scaling, cloud
Section: Representative Work

<section body>
```

Prompt text can omit some metadata, but should include source titles for attribution/debugging.

## Firestore Schema

### Collection: `knowledge_chunks`

Use a top-level collection so vector indexes are simple.

```javascript
{
  // Identity
  id: "expertise-system-design--representative-work--000",
  source_file: "knowledge/expertise/system-design.md",
  source_hash: "sha256-of-whole-file",
  content_hash: "sha256-of-chunk-text",
  chunk_index: 0,

  // Display / prompt context
  title: "System Design and Architecture",
  heading_path: ["System Design and Architecture", "Representative Work"],
  content: "...chunk body...",
  prompt_text: "## System Design and Architecture\n### Representative Work\n...",

  // Retrieval
  embedding: Vector([...]),
  embedding_model: "gemini-embedding-001",
  embedding_dim: 768,
  embedding_task_type: "RETRIEVAL_DOCUMENT",

  // Metadata
  category: "expertise",
  subcategory: "technical",
  tags: ["architecture", "scaling", "cloud"],
  priority: 0,
  word_count: 520,

  // Lifecycle
  is_active: true,
  ingest_run_id: "ingest-2026-06-02T10-00-00Z",
  created_at: Timestamp(...),
  updated_at: Timestamp(...)
}
```

### Collection: `knowledge_ingest_runs`

```javascript
{
  id: "ingest-2026-06-02T10-00-00Z",
  status: "success", // success, partial_success, failed
  started_at: Timestamp(...),
  finished_at: Timestamp(...),
  files_seen: 18,
  chunks_seen: 47,
  chunks_embedded: 5,
  chunks_skipped_unchanged: 42,
  chunks_marked_inactive: 2,
  embedding_model: "gemini-embedding-001",
  embedding_dim: 768,
  errors: []
}
```

## Firestore Vector Indexes

Create indexes explicitly; do not rely on runtime failures as the normal setup path.

Base active-chunk index:

```bash
gcloud firestore indexes composite create \
  --collection-group=knowledge_chunks \
  --query-scope=COLLECTION \
  --field-config=order=ASCENDING,field-path="is_active" \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}' \
  --database="(default)"
```

Optional category-prefilter index:

```bash
gcloud firestore indexes composite create \
  --collection-group=knowledge_chunks \
  --query-scope=COLLECTION \
  --field-config=order=ASCENDING,field-path="is_active" \
  --field-config=order=ASCENDING,field-path="category" \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}' \
  --database="(default)"
```

If `RAG_EMBEDDING_DIM` changes, the vector index must be recreated and all chunks must be re-ingested.

## Embedding Service

Create `backend/app/embeddings.py`.

Responsibilities:

- Initialize the Google embedding client using ADC.
- Embed documents with task type `RETRIEVAL_DOCUMENT`.
- Embed user queries with task type `RETRIEVAL_QUERY` or `QUESTION_ANSWERING`.
- Support `output_dimensionality`.
- Validate returned vector length equals `RAG_EMBEDDING_DIM`.
- Surface clear errors for missing project/location/API enablement.

Dependencies to add to `backend/pyproject.toml`:

```toml
"google-genai>=1.0.0"
```

or, if using the older Vertex AI SDK:

```toml
"google-cloud-aiplatform>=1.0.0"
```

Pick one implementation path and keep it consistent.

## Ingestion Pipeline

Create `backend/scripts/ingest_knowledge.py`.

CLI:

```bash
cd backend
uv run python scripts/ingest_knowledge.py --dry-run
uv run python scripts/ingest_knowledge.py --verbose
uv run python scripts/ingest_knowledge.py --force-reembed
```

High-level flow:

1. Load settings from the root `.env`.
2. Discover markdown under `knowledge/`, excluding `style.md` unless explicitly requested.
3. Exclude `faq.jsonl`, `pic.jpg`, and non-markdown assets.
4. Parse frontmatter and markdown headings.
5. Create deterministic chunk IDs.
6. Hash chunks.
7. Fetch existing chunk docs by ID.
8. Skip unchanged chunks unless `--force-reembed`.
9. Embed changed/new chunks in batches where the client supports it.
10. Upsert changed/new chunks.
11. Mark chunks from missing/deleted files inactive.
12. Write an ingest run summary.

Rollback should be simple: because stale chunks are soft-disabled via `is_active=false`, a bad ingest can be corrected by re-running after fixing the source files.

## Retrieval Service

Create `backend/app/rag.py` or `backend/app/rag_service.py`.

Preferred API:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RetrievedChunk:
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
    ...
```

Firestore query shape:

```python
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

collection = db.get_client().collection("knowledge_chunks")
query_ref = collection.where(filter=FieldFilter("is_active", "==", True))

if category:
    query_ref = query_ref.where(filter=FieldFilter("category", "==", category))

vector_query = query_ref.find_nearest(
    vector_field="embedding",
    query_vector=Vector(query_embedding),
    distance_measure=DistanceMeasure.COSINE,
    limit=top_k + 2,
    distance_result_field="vector_distance",
    distance_threshold=max_distance,
)
```

Post-processing:

- Convert docs to `RetrievedChunk`.
- Sort by `(priority desc, distance asc)` only if you intentionally want manual priority to override distance.
- Otherwise sort by `distance asc` and use priority only as a tie-breaker.
- Truncate the final prompt context by character/token budget so large chunks cannot bloat the system prompt.

## Fallback Strategy

Use a fallback only when no retrieved chunk passes the distance threshold.

Preferred fallback:

1. Try the chunk for `knowledge/background/introduction.md`.
2. If unavailable, use a small static fallback loaded from the current `knowledge/knowledge.md`.
3. If no fallback exists, continue with style + transcript and instruct the Avatar to say it does not know and use `push_tool`.

Do not treat fallback as a high-confidence retrieved result. Mark it in logs as `fallback=true`.

## Prompt Integration

Modify `backend/app/agent.py`:

```python
def build_system_prompt(retrieved_knowledge: str = "") -> str:
    ...
```

The prompt should continue to include:

- role and digital twin identity
- owner name
- `knowledge.style_text()`
- three-way conversation rules
- FAQ routing list from `knowledge.faq_list_text()`
- `push_tool` guidance

Replace the full `knowledge.knowledge_text()` section with:

```text
# Relevant knowledge about {owner}

Use the following retrieved knowledge to answer the visitor. If it is insufficient, do not invent.

{retrieved_knowledge}
```

Modify `build_agent()` and `stream_agent()`:

```python
def build_agent(retrieved_knowledge: str = "") -> Agent:
    return Agent(
        name="Avatar",
        instructions=build_system_prompt(retrieved_knowledge),
        model=settings.model,
        tools=[faq_tool, push_tool],
    )


async def stream_agent(transcript: str, retrieved_knowledge: str = "") -> AsyncIterator[dict]:
    agent = build_agent(retrieved_knowledge)
    ...
```

Modify `_chat_events()` in `backend/app/main.py`:

```python
instant = knowledge.instant_faq_number(message)
if instant is not None:
    ...
    return

rows = [Message(**r) for r in db.get_messages(request.conversation_id)]
retrieved = rag.retrieve_knowledge(message)
retrieved_text = rag.format_retrieved_context(retrieved)
transcript = agent.render_transcript(rows, settings.owner_name)

async for event in agent.stream_agent(transcript, retrieved_text):
    ...
```

This preserves the existing public API and SSE event contract.

## Configuration

Add to `backend/app/config.py` settings:

```python
rag_enabled: bool
rag_top_k: int
rag_max_distance: float
rag_context_max_chars: int
rag_embedding_model: str
rag_embedding_dim: int
rag_embedding_location: str
```

Environment defaults:

```bash
RAG_ENABLED=true
RAG_TOP_K=4
RAG_MAX_DISTANCE=0.65
RAG_CONTEXT_MAX_CHARS=12000
RAG_EMBEDDING_MODEL=gemini-embedding-001
RAG_EMBEDDING_DIM=768
RAG_EMBEDDING_LOCATION=global
```

Keep:

```bash
FIRESTORE_DATABASE=(default)
GOOGLE_CLOUD_PROJECT=your-project-id
```

Do not add `GOOGLE_APPLICATION_CREDENTIALS` to the default docs. The project already uses ADC locally and the Cloud Run service account in production.

## Testing Strategy

### Unit Tests

Create focused tests that do not require live Google services:

- markdown/frontmatter parser
- chunking behavior
- deterministic chunk IDs
- content hash skip logic
- formatting retrieved context
- distance threshold behavior
- prompt builder includes retrieved context and excludes full `knowledge.md`
- `Qn` instant path still bypasses RAG

Use fake embedding and fake Firestore/store objects where possible.

### Integration Tests

Mark live-service tests clearly, for example `@pytest.mark.firestore` or `@pytest.mark.rag_live`.

Tests:

- ingest a small temporary markdown fixture into a test collection or namespaced test docs
- retrieve expected chunks for known queries
- chat flow with mocked retrieval
- one optional full chat flow with real retrieval and real LLM

### Retrieval Evaluation Set

Add a simple eval file:

```json
[
  {
    "query": "What cloud platforms has the owner worked with?",
    "expected_sources": ["knowledge/expertise/cloud-infrastructure.md"],
    "expected_category": "expertise"
  },
  {
    "query": "What is this Avatar project about?",
    "expected_sources": ["knowledge/projects/current/avatar.md"],
    "expected_category": "projects"
  }
]
```

Create `backend/scripts/eval_retrieval.py` to report:

- hit@1
- hit@3
- mean reciprocal rank
- queries with no confident result
- retrieved source files and distances

This is more useful than only asserting latency.

## Observability

Log one structured line per retrieval:

```python
logger.info(
    "rag_retrieval",
    extra={
        "query_chars": len(query),
        "top_k": top_k,
        "result_count": len(results),
        "best_distance": results[0].distance if results else None,
        "fallback": fallback_used,
        "latency_ms": latency_ms,
        "sources": [r.source_file for r in results],
    },
)
```

Do not log full visitor queries by default. Visitor messages can contain personal information. If query logging is needed for debugging, gate it behind an explicit env var.

Metrics to watch:

| Metric | Target |
| --- | --- |
| Retrieval P95 latency | < 500 ms initially; optimize later |
| Empty retrieval rate | Low after knowledge set is complete |
| Prompt context size | Under `RAG_CONTEXT_MAX_CHARS` |
| Embedding failures | 0 |
| Ingest changed chunks | Expected after knowledge edits |

## Deployment And Operations

Initial manual flow:

1. Enable required APIs if not already enabled.
2. Create Firestore vector indexes.
3. Add embedding dependency and deploy code.
4. Run `uv sync` in `backend/`.
5. Run `uv run python scripts/ingest_knowledge.py --dry-run`.
6. Run real ingest.
7. Run retrieval eval.
8. Run backend tests.
9. Deploy to Cloud Run.
10. Smoke test normal chat, `Qn`, FAQ tool, push tool, and admin.

Do not add Cloud Scheduler in v1 unless the knowledge source is external to the container. If markdown is bundled at deploy time, scheduled ingest only re-ingests the same files already deployed.

If an admin ingest endpoint is later added:

- protect it with admin auth or Cloud Run IAM/OIDC, not a raw `ADMIN_PASSWORD` bearer string
- make it unavailable by default unless `RAG_ADMIN_INGEST_ENABLED=true`
- avoid long-running request timeouts by using Cloud Run Jobs for larger ingestion

## Implementation Phases

### Phase 1: Minimal RAG Over Existing Knowledge

- [ ] Add embedding config to `config.py`.
- [ ] Add embedding dependency.
- [ ] Create embedding service.
- [ ] Create chunker that can split existing `knowledge/knowledge.md`.
- [ ] Create `knowledge_chunks` schema and indexes.
- [ ] Create ingest script with `--dry-run`.
- [ ] Ingest current `knowledge/knowledge.md`.
- [ ] Create retriever and retrieval eval script.

### Phase 2: Agent Integration

- [ ] Modify `agent.build_system_prompt()` to accept retrieved knowledge.
- [ ] Modify `agent.build_agent()` and `agent.stream_agent()`.
- [ ] Modify `_chat_events()` after the instant FAQ branch.
- [ ] Preserve SSE event contract.
- [ ] Add tests proving `Qn` bypasses RAG.
- [ ] Add mocked chat-with-RAG tests.

### Phase 3: Knowledge Refactor

- [ ] Split `knowledge/knowledge.md` into focused markdown files.
- [ ] Add frontmatter metadata.
- [ ] Re-ingest.
- [ ] Run retrieval evals and tune chunk size/top_k/distance threshold.
- [ ] Remove or de-emphasize full `knowledge.md` only after eval quality is acceptable.

### Phase 4: Production Hardening

- [ ] Add structured retrieval logging.
- [ ] Add deploy/setup docs for vector indexes.
- [ ] Add cost/budget note to README/DEPLOY.
- [ ] Add smoke-test checklist for RAG.
- [ ] Decide whether admin/manual ingest is needed after v1 usage.

## Files To Create Or Modify

| File | Action | Purpose |
| --- | --- | --- |
| `backend/app/config.py` | Modify | Add RAG and embedding settings |
| `backend/pyproject.toml` | Modify | Add embedding client dependency |
| `backend/app/embeddings.py` | Create | Generate query/document embeddings |
| `backend/app/rag_service.py` | Create | Retrieve and format relevant chunks |
| `backend/scripts/ingest_knowledge.py` | Create | Chunk markdown, embed, write Firestore docs |
| `backend/scripts/eval_retrieval.py` | Create | Measure retrieval quality |
| `backend/app/agent.py` | Modify | Inject retrieved knowledge into system prompt |
| `backend/app/main.py` | Modify | Retrieve context in chat flow after `Qn` bypass |
| `backend/tests/test_rag_*.py` | Create | Unit tests for chunking/retrieval/prompt integration |
| `knowledge/` | Modify later | Split `knowledge.md` into focused files |
| `README.md` | Modify | Document RAG setup and ingest |
| `DEPLOY.md` | Modify | Document vector indexes and smoke tests |

## Success Criteria

RAG is complete when:

- Existing `Qn` instant answers still work with no LLM call.
- Normal chat retrieves relevant chunks before calling the agent.
- The full static `knowledge.md` is no longer injected into every non-FAQ turn.
- The prompt includes style, FAQ routing, three-way conversation rules, and only relevant retrieved knowledge.
- Retrieval eval hit@3 is acceptable for the core owner-profile questions.
- Firestore vector distance handling is correct: lower distance is better.
- Embedding model and dimension are configurable and stored with each chunk.
- Re-running ingest skips unchanged chunks.
- Deleted chunks are marked inactive.
- Backend tests pass.
- Live smoke tests cover chat, FAQ, push, admin, and RAG retrieval.

## Open Decisions

1. Use `gemini-embedding-001` at 768 dimensions, or `text-embedding-005` at 768 dimensions?
2. Keep source-of-truth knowledge as deployed markdown, or eventually move editable knowledge to an admin/GCS flow?
3. Should `faq.jsonl` remain only a tool/instant-answer source, or should FAQ entries also be embedded for semantic retrieval?
4. What retrieval eval threshold is acceptable before removing full `knowledge.md` from the prompt?

## References

- Firestore vector search: https://firebase.google.com/docs/firestore/vector-search
- Vertex AI text embeddings: https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings
- Text embeddings API reference: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings-api
- Agent Platform pricing: https://cloud.google.com/vertex-ai/generative-ai/pricing
