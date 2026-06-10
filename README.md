# Avatar

A production-ready digital twin web app. Visitors chat with an LLM-backed avatar of the site
owner; the owner can join any conversation live from an admin panel — making every thread a
three-way exchange between **visitor**, **avatar**, and **human**.

- **Architecture guide:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Deployment guide:** [`DEPLOY.md`](DEPLOY.md)
- **Behaviour spec:** [`SPEC.md`](SPEC.md) · **Design system:** [`design-system/`](design-system/)

---

## Google Cloud Architecture

```
 ┌─────────────────────────────── Google Cloud Project ───────────────────────────────┐
 │                                                                                     │
 │   ┌─────────────────┐     build     ┌──────────────────┐   push    ┌────────────┐  │
 │   │   Source code   │ ──────────── ▶│   Cloud Build    │ ────────▶ │  Artifact  │  │
 │   │   (local / git) │               │  (Dockerfile,    │           │  Registry  │  │
 │   └─────────────────┘               │   multi-stage)   │           │  (images)  │  │
 │                                     └──────────────────┘           └─────┬──────┘  │
 │                                                                           │ deploy  │
 │                                                                           ▼         │
 │   ┌──────────────────────────────── Cloud Run ──────────────────────────────────┐  │
 │   │  service: avatar  (min 0 / max 1, 512 MiB, 1 vCPU, concurrency 40)         │  │
 │   │                                                                              │  │
 │   │  ┌──────────────────────────────────────────────────────────────────────┐   │  │
 │   │  │  Container (single image)                                            │   │  │
 │   │  │                                                                      │   │  │
 │   │  │  ┌──────────────────┐      ┌─────────────────────────────────────┐  │   │  │
 │   │  │  │  Vite SPA        │      │  FastAPI backend                    │  │   │  │
 │   │  │  │  (static build)  │      │                                     │  │   │  │
 │   │  │  │  /               │      │  /api/*     (public, SSE + JSON)    │  │   │  │
 │   │  │  │  /admin          │      │  /admin/*   (cookie-gated)          │  │   │  │
 │   │  │  └──────────────────┘      │                                     │  │   │  │
 │   │  │                            │  agent.py   rag_service.py          │  │   │  │
 │   │  │                            │  db.py      embeddings.py           │  │   │  │
 │   │  │                            │  auth.py    push.py                 │  │   │  │
 │   │  │                            └─────────────────────────────────────┘  │   │  │
 │   │  └──────────────────────────────────────────────────────────────────────┘   │  │
 │   │                                                                              │  │
 │   │  Runtime identity: avatar-runtime (service account, ADC — no JSON keys)     │  │
 │   └──────────────────────────────────────────────────────────────────────────────┘  │
 │         │              │                   │                  │                      │
 │         ▼              ▼                   ▼                  ▼                      │
 │  ┌─────────────┐ ┌─────────────┐  ┌──────────────┐  ┌────────────────┐            │
 │  │  Firestore  │ │  Vertex AI  │  │    Secret    │  │  Cloud Logging │            │
 │  │  (Native)   │ │  Embeddings │  │   Manager    │  │  & Monitoring  │            │
 │  │             │ │             │  │              │  │                │            │
 │  │ conv.       │ │ gemini-     │  │ OPENROUTER_  │  │ structured     │            │
 │  │  messages   │ │ embedding   │  │ API_KEY      │  │ logs + uptime  │            │
 │  │ knowledge_  │ │ -001 (768d) │  │ ADMIN_       │  │ checks         │            │
 │  │  chunks     │ │             │  │ PASSWORD     │  │                │            │
 │  │  (vectors)  │ │ ingest      │  │ SESSION_     │  └────────────────┘            │
 │  │             │ │ + query     │  │ SECRET       │                                │
 │  └─────────────┘ └─────────────┘  │ PUSHOVER_*   │                                │
 │                                   └──────────────┘                                │
 └───────────────────────────────────────────────────────────────────────────────────┘
              │                                             │
              ▼ (API key, streamed LLM completions)         ▼ (HTTP, human alerts)
       ┌─────────────┐                              ┌──────────────┐
       │  OpenRouter │                              │   Pushover   │
       │  (LLM via   │                              │ (mobile push │
       │   OpenAI    │                              │  to owner)   │
       │   Agents    │                              └──────────────┘
       │   SDK)      │
       └─────────────┘
```

### GCP services at a glance

| Service | Role | Notes |
|---|---|---|
| **Cloud Run** | Hosts the container | `min-instances=0` (scale to zero), `max-instances=1`, request-based billing |
| **Cloud Build** | Builds the Docker image | `gcloud run deploy --source .` — no local Docker needed |
| **Artifact Registry** | Stores container images | Cleanup policy: keep 2 latest, delete after 30 days |
| **Firestore (Native)** | Conversations + knowledge vectors | Default database (free quota applies only to `(default)`) |
| **Vertex AI** | Text embeddings for RAG | `gemini-embedding-001`, 768d; cosine distance vector search |
| **Secret Manager** | API keys and passwords | Five secrets; mounted as env vars at deploy; never baked into the image |
| **Cloud Logging** | Structured runtime logs | `rag_retrieval` lines, abuse events, errors |
| **IAM** | Least-privilege access | `avatar-runtime` SA: `datastore.user` + `aiplatform.user` + secret accessor |

Authentication to Google is **ADC end to end** — your own credentials locally, the
`avatar-runtime` service account in production. No service-account JSON key is ever created,
committed, or baked into the image.

---

## Quick Start

### Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) logged in and a GCP project with billing enabled
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local container runs)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Node.js 20+](https://nodejs.org/) — for the frontend build
- [OpenRouter](https://openrouter.ai) API key with a small credit balance

### 1. Clone and configure

```bash
git clone <repo-url> avatar && cd avatar
```

Copy `.env.example` to `.env` and fill in every value:

```env
OPENROUTER_API_KEY=sk-or-v1-...
MODEL=openai/gpt-5.4-nano         # cheap for dev; use gpt-5.4-mini for production
OWNER_NAME=Your Name
ADMIN_PASSWORD=<16+ chars>
PUSHOVER_USER=...
PUSHOVER_TOKEN=...
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
FIRESTORE_DATABASE=(default)
SESSION_SECRET=<32+ random chars>
COOKIE_SECURE=0                    # set to 1 in production
```

### 2. Provision Google Cloud

Run the idempotent setup script once. It enables APIs, creates the Firestore default database,
Artifact Registry, the `avatar-runtime` service account, and Secret Manager secrets from `.env`.

```bash
# macOS / Linux
PROJECT_ID=your-gcp-project-id ./scripts/setup_gcp.sh

# Windows (PowerShell)
.\scripts\setup_gcp.ps1 -ProjectId your-gcp-project-id
```

Default region is `europe-west8`. Override with the `REGION` environment variable (bash) or
`-Region` flag (PowerShell). **Firestore's location is permanent** — the script confirms before
creating the database.

### 3. Validate the connection

```bash
cd backend && uv run pytest tests/test_firestore_connection.py -v
```

All tests must pass before continuing.

### 4. Ingest knowledge

The owner profile is retrieved per turn via RAG. Create the vector index once, then ingest:

```bash
# Create the Firestore composite vector index (once)
gcloud firestore indexes composite create \
  --collection-group=knowledge_chunks \
  --query-scope=COLLECTION \
  --field-config=order=ASCENDING,field-path=is_active \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}' \
  --database="(default)"

# Ingest (re-run after any edit to knowledge/knowledge.md)
cd backend
uv run python scripts/ingest_knowledge.py --dry-run   # preview first
uv run python scripts/ingest_knowledge.py             # embed + write to Firestore
```

### 5. Run locally (Docker)

```bash
# macOS / Linux
./scripts/start_mac.sh

# Windows (PowerShell)
.\scripts\start_pc.ps1
```

Open http://localhost:8000 (visitor) and http://localhost:8000/admin (admin dashboard).

### 6. Deploy to Cloud Run

```bash
# macOS / Linux
PROJECT_ID=your-gcp-project-id ./scripts/deploy_gcp.sh

# Windows (PowerShell)
.\scripts\deploy_gcp.ps1 -ProjectId your-gcp-project-id
```

The script builds via Cloud Build, wires secrets from Secret Manager, sets `COOKIE_SECURE=1`
and `ENVIRONMENT=production`, and deploys with `min-instances=0` / `max-instances=1`. The live
`https://<service>-<hash>.<region>.run.app` URL is printed at the end.

---

## Personalize the Twin

All owner content lives in `knowledge/`:

| File | Purpose |
|---|---|
| `knowledge.md` | First-person owner profile — chunked, embedded, and retrieved via RAG each turn |
| `style.md` | Voice, formatting, and safety rules — always in the system prompt verbatim |
| `faq.jsonl` | Numbered FAQ (`faq`, `question`, `answer`, `query`) — instant `Qn` answers with no LLM call |
| `pic.jpg` | Your photo — used as the human avatar icon |

Social links and the robot avatar images are in `frontend/public/` and `frontend/index.html`.
The owner's name is always read from the `OWNER_NAME` env var and never hardcoded; set your own
value in `.env`.

---

## Development

### Backend

```bash
cd backend && uv run uvicorn app.main:app --reload --app-dir .
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```

Vite proxies `/api` and `/admin/*` to the backend on port 8000. The visitor page has hot
reload; for admin, build the frontend (`npm run build`) and serve from the backend.

### Run backend unit tests (no external cost)

```bash
cd backend && uv run pytest -m "not llm and not rag_live" -v
```

Tests marked `llm` call the LLM (`openai/gpt-5.4-nano`); `rag_live` hits live Firestore vector
search. Run them deliberately after setup is confirmed working.

---

## Configuration Reference

All config is environment-driven via the root `.env`.

### Required

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key — routes LLM calls |
| `MODEL` | OpenRouter model id (e.g. `openai/gpt-5.4-nano` for dev, `openai/gpt-5.4-mini` for production) |
| `OWNER_NAME` | Name shown in UI, admin bubbles, and the avatar's self-reference |
| `ADMIN_PASSWORD` | Admin login password — minimum 16 characters |
| `SESSION_SECRET` | Signs admin cookies and visitor tokens — minimum 32 random characters |
| `PUSHOVER_USER` | Pushover user key — for human-in-the-loop notifications |
| `PUSHOVER_TOKEN` | Pushover app token |
| `GOOGLE_CLOUD_PROJECT` | GCP project id |
| `FIRESTORE_DATABASE` | Must be `(default)` — only the default database has free quota |

### Optional / tunable

| Variable | Default | Description |
|---|---|---|
| `COOKIE_SECURE` | `0` | Set to `1` in production (HTTPS) to add the `Secure` flag to cookies |
| `ENVIRONMENT` | `production` | Set to `development` to relax startup validation |
| `TRUST_PROXY_HEADERS` | `0` | Set to `1` on Cloud Run so per-IP rate limits use the client IP |
| `RAG_ENABLED` | `true` | Toggle RAG retrieval |
| `RAG_TOP_K` | `4` | Number of knowledge chunks to retrieve per turn |
| `RAG_MAX_DISTANCE` | `0.65` | Cosine distance threshold — chunks beyond this are discarded |
| `RAG_CONTEXT_MAX_CHARS` | `12000` | Character budget for retrieved context injected into the prompt |
| `RAG_EMBEDDING_MODEL` | `gemini-embedding-001` | Vertex AI embedding model |
| `RAG_EMBEDDING_DIM` | `768` | Embedding dimensions — must match the Firestore vector index |
| `RAG_LOG_QUERIES` | `0` | Set to `1` to log raw query text (may contain visitor PII) |
| `MAX_MESSAGE_CHARS` | `4000` | Visitor message truncation limit |
| `MAX_CONVERSATION_MESSAGES` | `80` | Cap on messages loaded per conversation |
| `MAX_TRANSCRIPT_CHARS` | `12000` | Cap on the transcript string sent to the LLM |

### Secrets in production (Secret Manager)

The deploy script wires these five secrets from Secret Manager as env vars at runtime:
`OPENROUTER_API_KEY`, `ADMIN_PASSWORD`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`, `SESSION_SECRET`.

---

## Security

The backend enforces multiple layers of protection before any paid or rate-limited work occurs:

- **Visitor sessions** are server-issued and signed. Public reads and chat posts require a token
  scoped to the same `conversation_id`.
- **Rate limiting** operates on source IP, globally, per `conversation_id`, and via an hourly
  service budget. All counters are in memory — `max-instances=1` is part of the security model.
  Move counters to Firestore or Memorystore before raising the instance cap.
- **Message bounds** — visitor messages over `MAX_MESSAGE_CHARS` are truncated before storage
  or LLM calls; conversation history and transcript size are also capped.
- **Admin** — httpOnly `SameSite=Lax` cookie signed with `itsdangerous`; constant-time password
  check; `Secure` flag on in production; all admin data routes behind `require_admin`.
- **XSS** — all model and human text goes through an escape-first, whitelist-only markdown
  renderer. Visitor text is escaped plain text. No raw HTML passthrough exists.
- **CORS** — off in production (same-origin). A `DEV_CORS_ORIGINS` allowance is gated and
  must never be set in production.
- **No secrets in the image** — ADC for Google APIs; Secret Manager for external keys. `.env`
  is excluded from the build context via `.gcloudignore` and `.dockerignore`.
- **Pushover** — separate rate limits per conversation, per IP, and a daily global cap; HTTP
  calls use timeouts; message length is capped.

Add provider-side backstops: an OpenRouter spend cap, a GCP budget alert (covers Vertex AI
embedding spend), and Pushover quota monitoring.

---

## Operations

```bash
# Service URL and status
gcloud run services describe avatar --region europe-west8

# Tail logs
gcloud run services logs read avatar --region europe-west8

# Update a config value without a rebuild
gcloud run services update avatar --region europe-west8 --update-env-vars MODEL=openai/gpt-5.4-mini

# Rotate a secret
printf '%s' NEW_VALUE | gcloud secrets versions add OPENROUTER_API_KEY --data-file=-
# then redeploy to pick up :latest

# Roll back to a previous revision
gcloud run revisions list --service avatar --region europe-west8
gcloud run services update-traffic avatar --region europe-west8 --to-revisions REVISION=100

# Check vector index status
gcloud firestore indexes composite list --database="(default)"

# Check RAG retrieval quality
cd backend && uv run python scripts/eval_retrieval.py
```

---

## Free Tier Notes

This app is designed to run comfortably within the Google Cloud free tier for a personal site.

| Service | Free quota | How Avatar stays within it |
|---|---|---|
| **Cloud Run** | 2M requests, 360k vCPU-s, 180k GiB-s/month | `min-instances=0` — no idle billing |
| **Firestore** | 50k reads, 20k writes, 20k deletes/day; 1 GiB stored | Inbox reads one parent doc per conversation, not one per message |
| **Secret Manager** | 6 active versions, 10k accesses/month | Exactly 5 secrets, one version each |
| **Artifact Registry** | 0.5 GiB free | Cleanup policy keeps only 2 most recent images |
| **Vertex AI embeddings** | Billed usage (not free) | Ingest runs once per knowledge edit; one short query embed per non-FAQ turn |

Set a GCP budget alert as an early warning for embedding spend. OpenRouter has its own spend
cap configuration — set one.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla TypeScript, Vite, custom design system (tokens + components CSS) |
| Backend | Python 3.12, FastAPI, uvicorn |
| LLM | OpenAI Agents SDK via OpenRouter (streamed SSE) |
| Database | Google Cloud Firestore (Native mode) |
| Embeddings / RAG | Vertex AI `gemini-embedding-001`, Firestore Vector Search |
| Auth | `itsdangerous` signed httpOnly cookies |
| Notifications | Pushover (human-in-the-loop alerts) |
| Container | Docker multi-stage build (Node 24 + Python 3.12 slim) |
| CI / Build | Google Cloud Build |
| Registry | Google Artifact Registry |
| Hosting | Google Cloud Run |
| Secrets | Google Secret Manager |
| Package manager | `uv` (Python), `npm` (Node) |
