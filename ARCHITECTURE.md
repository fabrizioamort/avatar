# Avatar — Architecture & Engineering Guide

This document describes how Avatar is built: its runtime topology, request flows, data
model, and the responsibilities of every module. It is the reference a new engineer reads
before changing the code.

For *what* the product does and *why* (the behavioural contract), see [`SPEC.md`](SPEC.md);
for the implementation contract the build was held to, see [`BUILD-SPEC.md`](BUILD-SPEC.md);
for setup and run instructions see [`README.md`](README.md); for deployment see
[`DEPLOY.md`](DEPLOY.md); for look and feel see [`design-system/`](design-system/).

---

## 1. What it is

Avatar is a single-owner "digital twin" web app. Visitors chat with an LLM-backed avatar of
the owner; the owner can join any conversation live from an admin panel, making the thread a
three-way conversation between **visitor**, **avatar**, and **human**.

Three properties shape the whole design:

- **One owner, low/bursty traffic.** Everything is sized to fit comfortably in the Google
  Cloud free tier and run on a single Cloud Run instance.
- **Three-way conversation.** A turn is not a clean user/assistant alternation — the human
  can interleave authoritative messages. The transcript is therefore rendered into a single
  task string (not a chat-role array) and the agent is instructed to only ever speak as the
  avatar.
- **Streaming first, polling second.** The active visitor sees the avatar's reply stream over
  SSE. A lightweight poll picks up *asynchronous* human messages that arrive out of band.

## 2. Topology

```
                Browser (visitor)                     Browser (admin)
                       │                                     │
                 same-origin HTTP / SSE              same-origin HTTP (cookie auth)
                       │                                     │
                       ▼                                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  Cloud Run service "avatar"  (single container, FastAPI)      │
        │                                                               │
        │   /            /admin          static assets   →  Vite build  │
        │   /api/*  (public)             /admin/* (admin, cookie-gated) │
        │                                                               │
        │   agent.py ── OpenRouter (LLM, streamed)                      │
        │   rag_service ── embeddings.py ── Vertex AI (gemini-embed)    │
        │   db.py ───────────────────────── Firestore (Native)         │
        │   push.py ─────────────────────── Pushover (human alerts)    │
        └──────────────────────────────────────────────────────────────┘
                       │                         │
                  Secret Manager            ADC (avatar-runtime SA)
              (API keys, password)        Firestore + Vertex AI access
```

The frontend (static Vite build) and the backend (FastAPI) ship in **one container**. The
backend serves the built SPA at `/` and `/admin` and exposes the JSON/SSE API under `/api`
and `/admin`. Because the SPA and API are same-origin, the browser sends no CORS preflight
and the admin session cookie is first-party (a dev-only CORS allowance exists, see §11).

External dependencies:

| Dependency | Used for | Auth |
|---|---|---|
| **OpenRouter** | the avatar's LLM completions (streamed) | API key |
| **Vertex AI** (`gemini-embedding-001`) | RAG embeddings (ingest + query) | ADC |
| **Firestore** (Native, default DB) | conversations + knowledge vectors | ADC |
| **Pushover** | human-in-the-loop notifications | user/token |
| **Secret Manager** | secrets at deploy time | ADC |

Authentication to Google is **ADC end to end** — locally your own credentials, in production
the `avatar-runtime` service account. No service-account JSON key is ever created or baked
into the image.

## 3. Repository map

```
backend/
  app/
    main.py          FastAPI app: routes, SSE chat, abuse guards, static serving
    config.py        cached, frozen Settings read from the root .env
    models.py        Pydantic request/response/event models (the API contract)
    db.py            the ONLY module that talks to Firestore (conversations)
    agent.py         OpenRouter wiring, tools, system prompt, streaming
    knowledge.py     knowledge.md / style.md / faq.jsonl loaders, Qn shortcut
    rag_service.py   Firestore Vector Search retrieval + context formatting
    embeddings.py    Vertex AI embedding client (document + query)
    chunker.py       markdown -> embeddable chunks (by heading)
    auth.py          signed httpOnly admin cookie (itsdangerous)
    push.py          Pushover sender
  scripts/
    ingest_knowledge.py   chunk + embed + upsert knowledge into Firestore
    eval_retrieval.py     retrieval quality (hit@1/hit@3/MRR) over eval_set.json
  tests/             pytest suite (unit + marked llm / rag_live)
frontend/
  index.html  admin.html      the two SPA entry points
  src/
    visitor/main.ts   visitor chat page controller
    admin/main.ts     admin dashboard controller
    lib/              api, types, markdown, dom, theme, time helpers
    styles/           tokens.css -> components.css -> page css
  public/             icons.svg, avatar PNGs, favicon (copied to dist root)
knowledge/            owner profile (knowledge.md), voice (style.md), faq.jsonl, pic.jpg
scripts/              start/stop (docker) + setup_gcp / deploy_gcp (sh + ps1)
design-system/        tokens, components, mockups, and design docs
Dockerfile            multi-stage: build frontend, run backend that serves it
```

## 4. Backend module reference

### `config.py`
Loads the project-root `.env` once at import (`override=True`) and exposes a cached
`get_settings()` returning a frozen `Settings` dataclass. `_env()` strips one layer of
surrounding quotes so the same `.env` works both with python-dotenv (local) and Docker's
`--env-file` (which keeps quotes). Enforces a single invariant — `FIRESTORE_DATABASE` must be
`(default)`, because the Firestore free quota only applies to the default database. Defaults
live here (`MODEL=openai/gpt-5.4-nano`, all `RAG_*` knobs), so most owners set only secrets.

### `models.py`
The wire contract, as Pydantic v2 models: `Message`, `ChatRequest`, `LoginRequest`,
`HumanMessageRequest`, `ConversationThread`, `ConversationSummary`, `ConfigResponse`. `Role`
is `Literal["visitor", "avatar", "human"]`. The frontend mirrors these in `lib/types.ts`.

### `db.py` — Firestore access layer
The single module that touches the conversation store. Data model (see §5):

- `conversations/{conversation_id}` — the inbox **aggregate** (preview, last timestamp,
  counts, `unread`, `needs_attention`, `last_seq`).
- `conversations/{conversation_id}/messages/{seq}` — one document per message, id zero-padded
  so lexical order equals numeric order.

Key functions:
- `insert_message(...)` runs inside a `@firestore.transactional` so the per-conversation
  sequence number and the parent aggregate stay consistent under concurrent writes.
- `get_messages(id, after_id=None)` — all rows ascending, optionally after an id (visitor
  polling passes `lastSeenId`).
- `list_conversations()` — **one document read per conversation** by reading the parent
  aggregate, not by scanning messages. This is what keeps the inbox inside the read quota.
- `open_conversation(id)` — opens a thread in one round-trip: batch-marks unread rows read,
  clears attention, and returns the updated rows.
- `clear_attention`, `latest_name`, `delete_conversation` (used by tests/cleanup).

### `agent.py` — the avatar
- `configure_openrouter()` (called once at app startup via the lifespan handler) points the
  OpenAI Agents SDK at OpenRouter: an `AsyncOpenAI` client with OpenRouter's base URL,
  `set_default_openai_api("chat_completions")` (the default `responses` API fails on
  OpenRouter), and tracing disabled.
- Tools, declared with `@function_tool` (name = function name, description = docstring):
  - `faq_tool(number)` → full FAQ question+answer from `knowledge.find_faq`.
  - `push_tool(message)` → Pushover alert to the human; its presence on a turn sets
    `needs_attention`.
- `build_system_prompt(retrieved_knowledge)` assembles the multi-way prompt: role, the
  RAG-retrieved profile context for this turn, the owner's voice (`style.md`, verbatim), the
  three-way rules (treat the human's words as authoritative; only ever speak as the avatar),
  the numbered FAQ routing list, and output rules (markdown, no code fences, no "Avatar:"
  prefix). Owner name always comes from config.
- `render_transcript(rows, owner_name)` flattens the stored rows into labelled lines
  (`Visitor:`, `Avatar:`, `{owner} (the human):`) ending in `Reply as the Avatar:`. This
  single string — not a role array — is the agent input, which is how a three-way thread is
  expressed to a two-party model.
- `stream_agent(...)` runs `Runner.run_streamed` and yields normalized dicts: `token` for
  text deltas, `tool` when a tool is called, and a final internal `_final` carrying the
  assembled text + collected tool calls so the route can persist before emitting `done`.

### `knowledge.py` — static knowledge & the Qn shortcut
Cached loaders for `knowledge.md` (profile; used as the RAG fallback), `style.md` (voice;
always in the prompt verbatim), and `faq.jsonl`. `faq_list_text()` renders the short `query`
phrasings for prompt routing; `find_faq(n)` returns the full question+answer for `faq_tool`.
`instant_faq_number()` / `get_instant_answer()` implement the `Qn` shortcut: a bare `Q2`
matches `^q(\d{1,2})$` and is answered directly from the FAQ with **no LLM call**.

### RAG: `rag_service.py`, `embeddings.py`, `chunker.py`
See §6. `chunker.py` splits markdown into per-heading chunks; `embeddings.py` wraps the
Vertex AI embedding client (document vs query task types); `rag_service.py` runs Firestore
Vector Search and formats the retrieved context for the prompt.

### `auth.py` — admin session
A signed, httpOnly, `SameSite=Lax` cookie via `itsdangerous.URLSafeTimedSerializer` (one-week
expiry). `verify_password` uses `secrets.compare_digest` (constant time). `require_admin` is
the FastAPI dependency guarding every admin data route. `COOKIE_SECURE` gates the `Secure`
flag (off for local http, `1` in production).

### `push.py` — human notifications
A tiny POST to the Pushover API; returns a human-readable status string that becomes the
tool's output. Failures are logged and degrade gracefully (the chat still completes).

## 5. Data model

Firestore Native, default database. Two collection families:

**Conversations** (`db.py`):

```
conversations/{conversation_id}                 ← inbox aggregate (1 read per convo)
  conversation_name, preview, last_created_at,
  last_id, last_seq, message_count, unread, needs_attention

conversations/{conversation_id}/messages/{seq}  ← one per message (seq zero-padded to 12)
  id (int seq), conversation_id, conversation_name, role,
  content, tool_calls, needs_attention, read, created_at (ISO)
```

The parent aggregate is the core performance decision: the admin inbox lists conversations
with one document read each, instead of scanning every message. Writes keep the aggregate in
sync transactionally.

**Knowledge vectors** (`rag_service.py` / `ingest_knowledge.py`):

```
knowledge_chunks/{chunk_id}
  id, source_file, content_hash, chunk_index, title, heading_path,
  content, prompt_text, embedding (Vector, 768d), embedding_model/dim/task_type,
  category, tags, priority, word_count, is_active, ingest_run_id, created_at/updated_at

knowledge_ingest_runs/{run_id}   ← audit record of each ingest
```

A composite vector index on (`is_active`, `embedding`) must exist for vector search (created
once; see README). Stale chunks are **soft-disabled** (`is_active=false`), never hard-deleted,
so a bad ingest is corrected by fixing the source and re-running.

## 6. Knowledge retrieval (RAG)

The owner profile is too large and too varied to paste into every prompt, so it is retrieved
per turn.

**Ingest (offline, `scripts/ingest_knowledge.py`, run after editing `knowledge.md`):**
1. `chunker.py` splits each markdown file into chunks — one per `##` section (plus the intro
   under the `#` title), further split on paragraph boundaries above ~800 words. Each chunk
   gets a deterministic id and a `content_hash`. `style.md` is excluded by default.
2. The embed text is metadata-prefixed (title/category/tags/section) and embedded with Vertex
   AI as `RETRIEVAL_DOCUMENT` at 768 dimensions.
3. Upsert to `knowledge_chunks`. Unchanged chunks (same hash + model + dim) are **skipped**;
   ids no longer produced are marked inactive; a run record is written.

**Retrieve (online, `rag_service.retrieve_knowledge`, per non-FAQ turn):**
1. The visitor message is embedded as `RETRIEVAL_QUERY`.
2. Firestore Vector Search returns the nearest active chunks by **cosine distance** (lower =
   closer), filtered by `rag_max_distance` and limited to `rag_top_k`.
3. `format_retrieved_context` joins the chunks' `prompt_text` within a character budget; the
   result is injected into the system prompt.
4. If nothing is confident enough (or RAG is disabled), the backend falls back to the full
   `knowledge.md`.

`Qn` instant answers and the `faq_tool` never touch RAG. Every retrieval emits one structured
`rag_retrieval` log line (raw query text only when `RAG_LOG_QUERIES=1`, since queries may
contain personal data). `eval_retrieval.py` scores retrieval (hit@1/hit@3/MRR) against
`eval_set.json`.

## 7. Request flows

### 7.1 Visitor chat (`POST /api/chat`, SSE)

`enforce_chat_rate_limit` runs first (20/min per `conversation_id`, in-memory moving window) —
a 429 here happens *before* any model call. Then `_chat_events`:

1. Clamp the message to 20,000 chars (append a truncation note if over) and **store the
   visitor row**.
2. **Instant path:** if the message is a bare `Qn`, store the avatar answer and emit
   `instant` → `token` (the whole answer) → `done`. No LLM, no RAG.
3. **Normal path:** retrieve RAG context (or fall back to full profile), render the full
   transcript, and stream the agent. Forward `tool` and `token` events as they arrive. On the
   agent's `_final`, store the avatar row (with `tool_calls`; `needs_attention=true` iff
   `push_tool` fired) and emit `done` with the new message id.

Any exception inside the stream is surfaced as a single `error` event rather than a broken
connection.

Wire events (each one JSON object on a `data:` line):

```
{"type":"tool","phase":"called","tool":"faq_tool"|"push_tool"}
{"type":"token","text":"..."}
{"type":"instant","faq":2}
{"type":"done","message_id":123,"needs_attention":false}
{"type":"error","message":"..."}
```

SSE is `fastapi.sse.EventSourceResponse`; the handler yields plain dicts and FastAPI frames
them. The frontend POSTs (so `EventSource`, which is GET-only, can't be used) and parses the
stream manually in `lib/api.ts` (read → decode → split on `\n\n` → take `data:` lines → JSON).

### 7.2 Human-in-the-loop

The owner posts from admin via `POST /admin/conversations/{id}/messages`. The human row is
stored with `role=human`, `read=true`, `needs_attention=false`. **The avatar does not react**
to it. The visitor's page picks it up on the next poll and renders it as the distinct "live"
bubble (photo, yellow ring, spark badge). The human's words enter the avatar's context only on
the *next* visitor turn, where the prompt instructs the avatar to treat them as authoritative.

### 7.3 Visitor polling

The visitor page polls `GET /api/conversations/{id}?after={lastSeenId}` every 10s, easing to
60s after 5 minutes of no activity and snapping back to 10s on send. It is the only mechanism
for surfacing async human messages; it never clobbers an in-flight stream (`streaming` guard)
and de-dupes via `lastSeenId` + a rendered-id set.

### 7.4 Admin triage

`GET /admin/conversations` lists aggregates (recent first). Opening a thread
(`GET /admin/conversations/{id}`) **marks read + clears attention in the same round-trip** and
returns the updated rows. `needs_attention` (set when `push_tool` fires) renders as a "Needs
you" badge until opened; `POST .../resolve` clears it without opening.

## 8. API surface

All same-origin. Public under `/api`, admin under `/admin` (cookie-gated except
login/logout/me).

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /api/config` | – | owner name for the UI |
| `GET /api/conversations/{id}?after=` | possession of id | restore + visitor poll |
| `POST /api/chat` | rate-limited | streamed avatar reply (SSE) |
| `POST /admin/login` | password | set session cookie |
| `POST /admin/logout` | – | clear cookie |
| `GET /admin/me` | cookie | login-gate probe (200/401) |
| `GET /admin/conversations` | cookie | inbox aggregates |
| `GET /admin/conversations/{id}` | cookie | open thread (marks read + clears attention) |
| `POST /admin/conversations/{id}/messages` | cookie | post a human message |
| `POST /admin/conversations/{id}/resolve` | cookie | clear needs-attention |

Visitors stay anonymous: an unguessable `conversation_id` UUID in a cookie is the only
credential, and possession of the id is access to that thread. Route registration order
matters — all `/api` and `/admin` routes and the `/`, `/admin` page routes are registered
*before* the catch-all static `/` mount so it cannot shadow them.

## 9. Frontend architecture

Vanilla TypeScript + Vite, two entry points (`index.html` → `visitor/main.ts`,
`admin.html` → `admin/main.ts`), no UI framework. CSS load order is always
`tokens.css` → `components.css` → page CSS; design tokens are the single source of colour,
type, and spacing. Dark theme is the default, persisted in `localStorage['avatar-theme']`.

Shared `lib/`:
- **`api.ts`** — typed client for every endpoint; manual SSE parsing for `streamChat`; admin
  calls send `credentials:'same-origin'`. Maps a 429 to a friendly slow-down message.
- **`types.ts`** — mirrors the backend models and the SSE event union.
- **`markdown.ts`** — a deliberately small, **safe** markdown renderer: it escapes *all* HTML
  first, then converts a whitelist (headings, lists, bold/italic, inline code, links, and bare
  URLs). There is no raw-HTML passthrough, so neither model nor human text can inject markup.
  Visitor text is rendered as escaped plain text (no markdown at all).
- **`dom.ts`**, **`theme.ts`**, **`time.ts`** — element helper + `escapeHtml` + icon sprite
  refs; theme init/toggle; timestamp formatting.

**Visitor page (`visitor/main.ts`)** owns the conversation cookie (`avatar_cid` + `avatar_keep`,
"Keep chat" on by default), optimistic rendering, streaming via the `streamChat` handlers
(typing indicator → tool status → tokens → finalize, all auto-scrolling), the adaptive poll
loop, and the `?q=N` deep link (immediately submits `QN`, then strips the param). The composer
autofocuses on load and refocuses after every send.

**Admin page (`admin/main.ts`)** is a login gate plus an inbox/thread master-detail. On mobile
it shows one pane at a time (tap a row → thread, back button → inbox); desktop is side-by-side
and auto-selects the newest thread. Arrow keys move between conversations, Enter sends (Shift
+Enter newlines), and it polls the inbox every 10s, refreshing the open thread when its
`last_id` advances.

In production the SPA and API are same-origin (no CORS). In dev, Vite proxies `/api` and the
`/admin/*` API routes to the backend on `:8000`, while serving the visitor page itself with hot
reload (see `vite.config.ts`).

## 10. Configuration & secrets

All config is environment-driven, loaded from the root `.env` by `config.py`. Required:
`OPENROUTER_API_KEY`, `MODEL`, `OWNER_NAME`, `ADMIN_PASSWORD`, `PUSHOVER_USER`,
`PUSHOVER_TOKEN`, `GOOGLE_CLOUD_PROJECT`, `FIRESTORE_DATABASE=(default)`. Optional:
`SESSION_SECRET` (signs the admin cookie; defaults to `avatar::<ADMIN_PASSWORD>`),
`COOKIE_SECURE` (`1` in prod), `DEV_CORS_ORIGINS` (dev only), and the `RAG_*` knobs
(`RAG_ENABLED`, `RAG_TOP_K`, `RAG_MAX_DISTANCE`, `RAG_CONTEXT_MAX_CHARS`,
`RAG_EMBEDDING_MODEL/DIM/LOCATION`, `RAG_LOG_QUERIES`).

`OWNER_NAME` is the one identity value that flows everywhere — page title, brand subtitle, how
the avatar refers to itself, and the human's "live" bubble. **It is never hardcoded;** the
frontend reads it from `/api/config`, the backend from settings.

In production the five secrets (`OPENROUTER_API_KEY`, `ADMIN_PASSWORD`, `PUSHOVER_USER`,
`PUSHOVER_TOKEN`, `SESSION_SECRET`) live in Secret Manager and are mounted as env vars at
deploy; `MODEL`, `OWNER_NAME`, and the Firestore/cookie vars are plain Cloud Run env vars.

## 11. Security model

- **Admin:** signed httpOnly `SameSite=Lax` cookie; constant-time password check; every admin
  data route behind `require_admin`. `Secure` flag on in production.
- **Visitors:** anonymous, addressed only by an unguessable UUID; possession of the id is
  access to that thread.
- **XSS:** all rendered model/human text goes through the escape-first whitelist markdown
  renderer; visitor text is escaped plain text.
- **CORS:** off in production (same-origin). A dev-only allowance is gated behind
  `DEV_CORS_ORIGINS` and must never be set in production.
- **Abuse guards (protect the OpenRouter key, no config):** messages over 20,000 chars are
  truncated before storage/LLM; each `conversation_id` is capped at 20 messages/minute, a
  moving window held in memory. Both happen before any model call.
- **No secrets in the image:** ADC for Google, Secret Manager for keys; `.env` is excluded from
  the build context (`.gcloudignore`/`.dockerignore`).

> The in-memory rate limiter is correct only at `max-instances=1` (the default). Raising the
> instance cap requires moving the limiter to a shared store first, or the effective limit
> becomes 20/min *per instance*. See `DEPLOY.md`.

## 12. Build, run, deploy

**Container.** A multi-stage `Dockerfile`: stage 1 (`node:24-slim`) runs `npm ci && npm run
build`; stage 2 (`python:3.12-slim`) installs backend deps with `uv sync --frozen --no-dev`,
copies the backend, the built `frontend/dist`, and `knowledge/`, and runs uvicorn. Cloud Run's
injected `$PORT` is honoured (defaults to 8080).

**Local.** `scripts/start_pc.ps1` / `start_mac.sh` stop any running `avatar` container, rebuild,
and run it with the root `.env`. Or run backend (`uv run uvicorn app.main:app --reload`) and
frontend (`npm run dev`) separately for hot reload.

**GCP.** `scripts/setup_gcp.*` (idempotent) enables APIs, creates the default Firestore
database, Artifact Registry, the `avatar-runtime` service account (granted
`datastore.user` + `aiplatform.user`), and the Secret Manager secrets from `.env`.
`scripts/deploy_gcp.*` runs `gcloud run deploy --source .` (Cloud Build), wires the secrets,
sets `COOKIE_SECURE=1`, and deploys `min-instances=0` / `max-instances=1`. Full guide and the
post-deploy smoke checklist are in [`DEPLOY.md`](DEPLOY.md).

## 13. Testing

`backend/tests/` (pytest):
- Unmarked unit tests run with no external cost: config, knowledge/FAQ, auth (401 paths,
  tampered cookie, logout), public + admin API behaviour, abuse guards, chunker, RAG service.
- `@pytest.mark.llm` tests call the model (use `MODEL=openai/gpt-5.4-nano`); `@pytest.mark.rag_live`
  tests hit live embeddings + Firestore vector search.
- `test_firestore_connection.py` is the setup validation gate (see README): it proves a project
  id resolves, the DB is `(default)`, and a message round-trips.

Run the no-cost subset with `uv run pytest -m "not llm and not rag_live"`. Manual/end-to-end
plans with checkboxes live in [`test/`](test/). Always clean up test conversations and
screenshots afterwards.

## 14. Design decisions, recapped

| Decision | Why |
|---|---|
| Single transcript string, not a role array | A three-way thread (human interleaves) doesn't map to user/assistant turns |
| Parent-doc inbox aggregate | One read per conversation keeps the inbox inside Firestore's free read quota |
| Transactional message insert | Sequence number + aggregate stay consistent under concurrent writes |
| SSE for the active reply, polling for human messages | Stream what the visitor is waiting on; cheaply pick up out-of-band human posts |
| Escape-first whitelist markdown | Render model/human markdown without an XSS surface |
| RAG over the profile, FAQ/Qn bypass it | Retrieve only what a turn needs; instant answers stay instant and free |
| Soft-disable stale chunks | A bad ingest is fixed by editing the source and re-running, not by data loss |
| In-memory rate limit + `max-instances=1` | Simplest correct guard for a single-instance personal site |
| ADC + Secret Manager, no JSON keys | No long-lived credential ever touches the repo or image |
