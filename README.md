# Avatar

Interact with a digital twin of you. Visitors chat with an LLM-backed avatar of the site's
owner, and the owner can jump into any conversation live from an admin panel — a three-way
chat between visitor, avatar, and human.

Video walk-through: https://youtu.be/srlhW4H-Gtg

- **Architecture & engineering guide:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Deployment (Cloud Run):** [`DEPLOY.md`](DEPLOY.md)
- **Behaviour spec / design system:** [`SPEC.md`](SPEC.md) · [`design-system/`](design-system/)

## Setup

All secrets live in one `.env` in the project root:

```
OPENROUTER_API_KEY=sk-or-v1-...
MODEL=openai/gpt-5.4-nano
OWNER_NAME=Ed Donner
ADMIN_PASSWORD=your-chosen-admin-password
PUSHOVER_USER=...
PUSHOVER_TOKEN=...
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
FIRESTORE_DATABASE=(default)
SESSION_SECRET=a-long-random-string-at-least-32-chars
COOKIE_SECURE=0
```

- `OWNER_NAME` is the name shown throughout the UI (header, title, the avatar's self-reference,
  and your "live" bubble). It is configuration, never hardcoded — each owner sets their own.
- `ADMIN_PASSWORD` must be non-blank and at least 16 characters. `SESSION_SECRET` must be
  non-blank and at least 32 random characters; it signs admin cookies and visitor conversation
  tokens. The app fails closed at startup if either secret is missing or weak. `COOKIE_SECURE`
  is `0` for local http, `1` in production (set automatically on deploy).
- `GOOGLE_CLOUD_PROJECT` is your project id; `FIRESTORE_DATABASE` must be `(default)` (the free
  quota only applies to the default database).
- The `RAG_*` knobs are optional and default sensibly in `backend/app/config.py`.

### 1. OpenRouter

The avatar's LLM calls go through [OpenRouter](https://openrouter.ai). Create a key under
[Keys](https://openrouter.ai/keys), add it to `.env` as `OPENROUTER_API_KEY`, and add a little
credit. `openai/gpt-5.4-nano` is cheap for development; use a stronger model (e.g.
`openai/gpt-5.4-mini`) for a live site by setting `MODEL`.

### 2. Google Cloud (Firestore)

Conversations are stored in **Firestore** (Native mode) — no schema to create. You need the
[`gcloud` CLI](https://cloud.google.com/sdk/docs/install) and a project with billing enabled
(it sits comfortably in the free tier for a personal site).

```
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login        # ADC: how the app authenticates locally
```

Then run the idempotent setup script once to enable APIs and provision Firestore (default
database), Artifact Registry, the `avatar-runtime` service account, and Secret Manager secrets:

- macOS / Linux: `PROJECT_ID=YOUR_PROJECT_ID ./scripts/setup_gcp.sh`
- Windows: `.\scripts\setup_gcp.ps1 -ProjectId YOUR_PROJECT_ID`

It defaults to region `europe-west8` (override with `REGION`/`-Region`). **Firestore's location
is permanent**, so it confirms before creating the database. Authentication is ADC end to end —
no service-account JSON key is ever created or committed.

### 3. Validate

```
cd backend && uv run pytest tests/test_firestore_connection.py -v
```

All tests must pass before proceeding: they confirm the project id resolves, the database is
`(default)`, and a message can be written, read back, and deleted.

## Personalize the twin (`knowledge/`)

The twin's knowledge and voice come from a few files read into the system prompt at runtime:

- **`knowledge.md`** — a first-person profile of you. Chunked, embedded, and retrieved per turn
  (see RAG below) rather than pasted into the prompt wholesale.
- **`style.md`** — voice, formatting, and safety rules. Stays in the prompt verbatim.
- **`faq.jsonl`** — one JSON object per line (`faq`, `question`, `answer`, and a short `query`
  used for routing). Visitors can type a bare `Qn` (e.g. `Q2`) for an instant answer with no
  LLM call, and a deep link like `…/?q=2` opens the chat and asks Q2 directly.
- **`pic.jpg`** — your photo (the human avatar); a robotic variant is the twin (see
  `design-system/docs/avatar-generation.md`).

A few owner-specific bits live in the frontend: the footer social links in
`frontend/index.html` and the avatar images in `frontend/public/`.

### Knowledge retrieval (RAG)

`knowledge.md` is served by Retrieval-Augmented Generation: chunks embedded with Vertex AI
(`gemini-embedding-001`, 768d) and stored in a Firestore `knowledge_chunks` collection. Each
non-FAQ turn embeds the visitor's message and injects the nearest chunks (Firestore Vector
Search, cosine distance) into the prompt, falling back to the full profile if nothing is
confident enough. `Qn` and `faq_tool` never hit RAG. See [`ARCHITECTURE.md`](ARCHITECTURE.md)
for the full pipeline.

Create the vector index once:

```bash
gcloud firestore indexes composite create \
  --collection-group=knowledge_chunks \
  --query-scope=COLLECTION \
  --field-config=order=ASCENDING,field-path=is_active \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}' \
  --database="(default)"
```

Then ingest (re-run after any edit to `knowledge.md`; unchanged chunks are skipped):

```bash
cd backend
uv run python scripts/ingest_knowledge.py --dry-run   # preview
uv run python scripts/ingest_knowledge.py             # embed + write
uv run python scripts/eval_retrieval.py               # optional: hit@1/hit@3/MRR
```

Embeddings are billed usage (tiny at this scale); keep a budget alert. If you change
`RAG_EMBEDDING_DIM`, recreate the index and re-ingest with `--force-reembed`.

## Running

**Docker (recommended).** Builds and runs the single container with your root `.env`:

- macOS / Linux: `./scripts/start_mac.sh` (stop with `./scripts/stop_mac.sh`)
- Windows: `./scripts/start_pc.ps1` (stop with `./scripts/stop_pc.ps1`)

Then open http://localhost:8000 (admin at `/admin`). Docker must be running.

**Local development.** Backend and frontend in two terminals:

```
cd backend && uv run uvicorn app.main:app --reload --app-dir .
cd frontend && npm install && npm run dev
```

Vite proxies `/api` to the backend, so run both. The visitor page gets hot reload; for admin,
build the frontend (`npm run build`) and load `/admin` from the backend.

## Deploy to Cloud Run

The same container deploys to **Google Cloud Run**. After the setup script (above) and a fully
populated `.env`:

- macOS / Linux: `PROJECT_ID=YOUR_PROJECT_ID ./scripts/deploy_gcp.sh`
- Windows: `.\scripts\deploy_gcp.ps1 -ProjectId YOUR_PROJECT_ID`

The script builds via Cloud Build, wires secrets from Secret Manager, sets `COOKIE_SECURE=1`,
sets `ENVIRONMENT=production` / `TRUST_PROXY_HEADERS=1`, and deploys with
`min-instances=0` / `max-instances=1`. It prints the live
`https://<service>-<hash>.<region>.run.app` URL. Full guide and smoke-test checklist:
[`DEPLOY.md`](DEPLOY.md).

## Built-in protections

The backend guards paid resources before Firestore writes, RAG retrieval, LLM calls, or
Pushover calls:

- Visitor sessions are server-issued and signed; public reads and chat posts require a token
  scoped to the same conversation id.
- Chat is rate-limited by source IP, globally, by conversation id, and by an hourly service
  budget. These limits are in memory, so `max-instances=1` is part of the security model until
  you move them to Firestore, Redis, or another shared store.
- Visitor messages over 4,000 characters are truncated, long conversation histories are capped,
  and the transcript sent to the model is bounded.
- Admin login and Pushover notification attempts have separate rate limits.

Also configure provider-side backstops: an OpenRouter spend cap or credit limit, a low GCP
budget alert, and Pushover quota monitoring.
