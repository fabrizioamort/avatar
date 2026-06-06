# Deployment (Google Cloud Run)

How to deploy Avatar to **Google Cloud Run** as a single container, run it in production, and verify it. Provisioning and deployment are driven by the scripts in `scripts/` (`setup_gcp.*` then `deploy_gcp.*`); nothing outward-facing happens until you run them.

> **A reference deployment is live** at `https://avatar-386833655338.europe-west8.run.app`. That project id and URL are one owner's. **To stand up your own**, use your own Google Cloud project id and (optionally) region. The scripts take `PROJECT_ID` / `REGION` as inputs, so there are no hardcoded identifiers to edit.

| | |
|---|---|
| **Service** | Cloud Run service `avatar` → generated `https://<service>-<hash>.<region>.run.app` |
| **Region** | `europe-west8` (Milan) by default — Cloud Run, Firestore, and Artifact Registry all in one region |
| **Database** | Firestore Native, **default** database (free quota only applies to `(default)`) |
| **Scaling** | `min-instances=0`, `max-instances=1`, request-based billing |
| **Resources** | 512 MiB memory, 1 vCPU, concurrency 40, 300 s timeout |
| **Build** | the existing multi-stage `Dockerfile`, built by Cloud Build from source |
| **Auth** | runs as the `avatar-runtime` service account; ADC end to end (no JSON keys) |

## Why this shape

**`min-instances=0` (accept cold starts).** Cloud Run bills idle minimum instances. The goal here is free-tier leverage, so we keep zero idle instances and accept a cold start on the first request after the service scales to zero. A personal twin's traffic is bursty and low-volume, so this is the right default. If you want snappier first responses and can accept the idle cost, set `--min-instances 1` in `scripts/deploy_gcp.*`.

**`max-instances=1` (single instance).** The chat, login, and Pushover abuse guards are held **in memory, per instance**. With one instance the per-IP, global, per-conversation, and budget counters behave as designed. The app is IO-bound (a chat reply is dominated by the OpenRouter LLM, streamed back asynchronously over SSE), so one instance at concurrency 40 comfortably serves a personal site. **If you raise `max-instances`, move the limiter to a shared store first** (Firestore counters, Redis/Memorystore, or equivalent).

**Request-based billing (`--cpu-throttling`).** CPU is only allocated while a request is being handled (including startup and shutdown), which is what keeps an idle service free. `512Mi` is enough for Python + the Agents SDK + a handful of live SSE connections; bump only `--memory` to `1Gi` if smoke testing shows memory pressure.

## Free-tier notes

- **Cloud Run** has a monthly free tier for request count, vCPU-seconds, and GiB-seconds. `min-instances=0` avoids idle billable time.
- **Firestore** free quota is daily (1 GiB stored, 50k reads, 20k writes, 20k deletes) and applies only to the **default** database. The inbox reads one parent document per conversation (not one per message) to stay well inside the read quota.
- **Secret Manager** gives 6 active secret versions and 10k access operations/month free. Avatar uses exactly five secrets (`OPENROUTER_API_KEY`, `ADMIN_PASSWORD`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`, `SESSION_SECRET`); `MODEL` and `OWNER_NAME` are non-secret env vars. Keep one active version per secret.
- **Artifact Registry** has a small free storage allowance. `setup_gcp.*` applies a cleanup policy (keep the 2 most recent versions, delete versions older than 30 days). See the note below about which repo source deploys actually use.
- **Vertex AI embeddings** (knowledge retrieval) are **billed usage, not free**. At a personal twin's scale the cost is tiny: ingestion embeds a handful of chunks once per knowledge edit, and each non-FAQ chat turn embeds one short query. Even so, treat it as real spend and rely on a budget alert rather than assuming free-tier coverage.
- **Budget alerts** notify but do not cap spend. Add a low budget alert in the Cloud Console as an early warning (it also covers the embedding spend above). Also set an OpenRouter spend cap or prepaid credit limit; the app-side limiter is not a provider-side billing cap.

## 1. Prerequisites

- `gcloud` installed and logged in (`gcloud auth login`), with a project set (`gcloud config set project YOUR_PROJECT_ID`).
- Application Default Credentials authorized: `gcloud auth application-default login`.
- The root `.env` fully populated (see [README setup](README.md#setup-instructions)), including `SESSION_SECRET`. `.env` is **never** uploaded to Cloud Build (`.gcloudignore` excludes it) and never baked into the image; secrets come from Secret Manager.
- `scripts/setup_gcp.*` run once (enables APIs, creates Firestore, the `avatar-runtime` service account, grants Firestore and Vertex AI access, and creates the secrets). No local Docker is needed — Cloud Build builds remotely.
- The **knowledge vector index** created once and the knowledge **ingested** at least once, so the Avatar has something to retrieve. Both are local steps (run against the same Firestore project via ADC); see [Knowledge retrieval (RAG)](README.md#knowledge-retrieval-rag). The `knowledge/` markdown is bundled in the image, but the embeddings live in Firestore, so re-run the ingest after any knowledge edit — it is not part of the container build. There is no admin ingest endpoint or scheduler in v1: ingestion is a deliberate, manual CLI step (a scheduler would only re-ingest the same bundled files).

## 2. Deploy

Run the setup script once, then deploy (re-run deploy for every subsequent release):

```bash
# one-time provisioning
PROJECT_ID=YOUR_PROJECT_ID ./scripts/setup_gcp.sh      # Windows: .\scripts\setup_gcp.ps1 -ProjectId YOUR_PROJECT_ID

# build + deploy from source
PROJECT_ID=YOUR_PROJECT_ID ./scripts/deploy_gcp.sh     # Windows: .\scripts\deploy_gcp.ps1 -ProjectId YOUR_PROJECT_ID
```

`deploy_gcp.*` runs `gcloud run deploy avatar --source .`, which builds the `Dockerfile` with Cloud Build and deploys it with the runtime service account, the non-secret env vars, and the secrets wired from Secret Manager. It prints the service URL when done. Override `REGION` / `SERVICE_NAME` via env vars (bash) or `-Region` / `-ServiceName` (PowerShell).

> **Artifact Registry repo note.** `gcloud run deploy --source` pushes built images to an auto-created repo named **`cloud-run-source-deploy`**, not the `avatar` repo that `setup_gcp.*` creates. So the cleanup policy currently lands on the unused `avatar` repo. To clean up the images source deploys actually produce, after your first deploy re-run setup with the source-deploy repo name, e.g. `REPOSITORY=cloud-run-source-deploy PROJECT_ID=YOUR_PROJECT_ID ./scripts/setup_gcp.sh` (it will skip everything that already exists and just (re)apply the cleanup policy to that repo).

## 3. Environment variables / secrets

Set as **non-secret Cloud Run env vars** (passed by `deploy_gcp.*`):

| Var | Value | Why |
|---|---|---|
| `MODEL` | from `.env` | the OpenRouter model id (e.g. `openai/gpt-5.4-mini` for production) |
| `OWNER_NAME` | from `.env` | the name shown in the UI |
| `ENVIRONMENT` | `production` | enables fail-closed production config validation |
| `COOKIE_SECURE` | `1` | production is HTTPS, so the admin session cookie must be `Secure` |
| `TRUST_PROXY_HEADERS` | `1` | trust Cloud Run's proxy headers for per-client IP throttling |
| `GOOGLE_CLOUD_PROJECT` | your project id | Firestore project |
| `FIRESTORE_DATABASE` | `(default)` | the only database with free quota |

Set as **Secret Manager secrets** (created by `setup_gcp.*` from `.env`, mounted as env vars at deploy):

`OPENROUTER_API_KEY`, `ADMIN_PASSWORD`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`, `SESSION_SECRET`.

Notes:
- **`ADMIN_PASSWORD`** must be at least 16 characters. If it is absent from `.env`, `setup_gcp.*` generates and stores a random value; retrieve it from Secret Manager before logging out.
- **`SESSION_SECRET`** signs the admin session cookie and visitor conversation tokens. It must be at least 32 random characters. If it is absent from `.env`, `setup_gcp.*` generates a strong random value and stores it. Setting it explicitly means rotating `ADMIN_PASSWORD` later won't invalidate live admin sessions.
- **`MODEL`** is whatever is in `.env`. For production set `MODEL=openai/gpt-5.4-mini` before deploying (`openai/gpt-5.4-nano` is the cheaper dev/test model and the code default). Change it later by editing `.env` and redeploying, or `gcloud run services update avatar --region <region> --update-env-vars MODEL=...`.
- To rotate a secret: `printf '%s' NEW_VALUE | gcloud secrets versions add NAME --data-file=-`, then redeploy (or `gcloud run services update` to pick up `:latest`).
- Runtime IAM required by the app: setup creates narrow custom project roles for Firestore document access and Vertex prediction, then grants `roles/secretmanager.secretAccessor` only on each configured secret. Run Avatar in a dedicated or otherwise low-blast-radius GCP project, and confirm the `avatar-runtime` service account has no owner/editor/admin roles.

## 4. Testing (post-deploy smoke)

Run against the printed `https://<service>-<hash>.<region>.run.app` URL. Use `MODEL=openai/gpt-5.4-nano` for cheap test calls if you like, and clean up test data afterwards.

- [ ] `gcloud run services describe avatar --region <region> --format='value(status.url)'` returns the URL; the service is serving traffic.
- [ ] `curl -s <URL>/api/config` → `{"owner_name":"..."}` (200).
- [ ] `/` loads the visitor UI (dark + light, desktop + mobile); the rings background and the LinkedIn/YouTube footer render.
- [ ] A normal question streams a reply (real LLM call over SSE); `Q2` returns the instant FAQ; `<URL>/?q=2` opens and immediately answers Q2.
- [ ] RAG retrieval works: a question about a specific part of your `knowledge.md` (e.g. a named project or skill) gets a grounded, accurate answer. Logs show a `rag_retrieval` line with a low `best_distance` and the expected `sources`: `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="avatar" AND textPayload:rag_retrieval' --freshness=15m`. (Raw queries are not logged unless `RAG_LOG_QUERIES=1`.)
- [ ] The vector index is `READY` (`gcloud firestore indexes composite list --database="(default)"`) and `knowledge_chunks` has the expected number of `is_active` docs (re-run `scripts/ingest_knowledge.py` if not).
- [ ] FAQ routing works (e.g. ask about a NameError → `faq_tool`), and links in replies are clickable.
- [ ] `/admin` → wrong password rejected; correct `ADMIN_PASSWORD` opens the dashboard; the inbox lists conversations and a thread opens quickly. Without the cookie, `GET /admin/conversations` returns 401.
- [ ] Post a human message from admin → it appears in the visitor's chat within ~10 s (polling), styled as the "live" bubble.
- [ ] Contact-capture flow ("I'd like to get in touch", give an email) fires a **Pushover** notification and sets `needs_attention`.
- [ ] In DevTools, the admin session cookie has the **`Secure`** flag (confirms `COOKIE_SECURE=1`).
- [ ] Cloud Run logs show no Firestore auth errors, memory errors, or missing env vars: `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="avatar" AND severity>=WARNING' --freshness=15m`.
- [ ] Abuse guards work: a >4,000-character message is truncated (note appended), rotating conversation IDs still hits the per-IP/global limit, and excessive requests return HTTP 429 before Firestore writes, RAG, LLM, or Pushover work.
- [ ] Clean up: delete the test conversation threads from Firestore and any screenshots.

## 5. Success criteria

Deployment is successful when:
- The app is reachable at its `run.app` URL over HTTPS, with `min-instances=0`, `max-instances=1`, request-based billing, and the `avatar-runtime` service account.
- Firestore uses the default database and the parent-doc inbox aggregate model.
- All of the visitor, admin (login-gated), three-way human-in-the-loop, `Qn`/`?q=` instant answers, FAQ-tool routing, RAG knowledge retrieval, and Pushover paths work end to end.
- Secrets are configured via Secret Manager (never baked into the image); the admin cookie is `Secure`.
- Logs are clean.

## Abuse Guards And Spend Controls

The backend enforces these controls before paid or limited work:

- Server-issued signed visitor sessions are required for public conversation reads and chat posts.
- Chat is limited by source IP, globally, by conversation id, and by an hourly service budget.
- Admin login attempts are limited by source IP.
- Pushover notifications are capped by conversation, source IP, and daily global quota; Pushover HTTP calls use timeouts and message length caps.
- Visitor message length, conversation length, and model transcript size are bounded.

The limiter is in-memory per instance. With `max-instances=1` (the default here) the counters are service-wide for the deployment. If you scale beyond one instance, move these counters to a shared store first. Keep provider-side backstops in place: OpenRouter spend cap or credit limit, GCP budget alerts/quotas, Pushover quota monitoring, and Cloud Logging alerts for elevated 429s, 5xxs, high request counts, and unusual Vertex/OpenRouter spend.

## 6. Custom domain (optional, deferred)

A custom domain is **deferred** in v1 — the `run.app` URL works on its own, and Google's recommended Cloud Run custom-domain path uses an external Application Load Balancer, which is not free-tier friendly. Cloud Run's built-in **domain mappings** are a lower-cost alternative but are not available in every region and have been in preview; check current availability for your region before relying on them. See https://docs.cloud.google.com/run/docs/mapping-custom-domains.

A subdomain of your site is worth it mainly for clean **iframe embedding**: serving the app from `avatar.<yourdomain>` (the same registrable domain as the host page) keeps the "Keep chat" cookie **first-party**. Until a custom domain is set up, the `scripts/wordpress-embed.html` snippet still works against the `run.app` URL (the cookie is third-party, so "Keep chat" may not persist in browsers that block third-party cookies). See SPEC.md "Tech stack decisions" for the `frame-ancestors` guidance.

## 7. Operations

- URL / status: `gcloud run services describe avatar --region <region>`.
- Logs: `gcloud run services logs read avatar --region <region>`, or the `gcloud logging read` query above.
- Update config without a rebuild: `gcloud run services update avatar --region <region> --update-env-vars KEY=value`.
- Roll back: `gcloud run revisions list --service avatar --region <region>`, then `gcloud run services update-traffic avatar --region <region> --to-revisions REVISION=100`.
- Scale (only after moving the rate limiter to a shared store): edit `--max-instances` in `scripts/deploy_gcp.*`.

## Legacy: fly.io

Earlier versions deployed to fly.io. Those artifacts (`scripts/fly.toml`, `scripts/deploy.sh`) have been removed in favour of the Cloud Run flow above; they remain in git history if ever needed.
