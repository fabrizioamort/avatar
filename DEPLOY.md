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

**`max-instances=1` (single instance).** The per-conversation rate limit (20 messages/minute) is held **in memory, per instance**. With one instance the limit behaves exactly as designed. The app is IO-bound (a chat reply is dominated by the OpenRouter LLM, streamed back asynchronously over SSE), so one instance at concurrency 40 comfortably serves a personal site. **If you raise `max-instances`, move the rate limiter to a shared store first** (otherwise the effective limit becomes 20/min per instance).

**Request-based billing (`--cpu-throttling`).** CPU is only allocated while a request is being handled (including startup and shutdown), which is what keeps an idle service free. `512Mi` is enough for Python + the Agents SDK + a handful of live SSE connections; bump only `--memory` to `1Gi` if smoke testing shows memory pressure.

## Free-tier notes

- **Cloud Run** has a monthly free tier for request count, vCPU-seconds, and GiB-seconds. `min-instances=0` avoids idle billable time.
- **Firestore** free quota is daily (1 GiB stored, 50k reads, 20k writes, 20k deletes) and applies only to the **default** database. The inbox reads one parent document per conversation (not one per message) to stay well inside the read quota.
- **Secret Manager** gives 6 active secret versions and 10k access operations/month free. Avatar uses exactly five secrets (`OPENROUTER_API_KEY`, `ADMIN_PASSWORD`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`, `SESSION_SECRET`); `MODEL` and `OWNER_NAME` are non-secret env vars. Keep one active version per secret.
- **Artifact Registry** has a small free storage allowance. `setup_gcp.*` applies a cleanup policy (keep the 2 most recent versions, delete versions older than 30 days). See the note below about which repo source deploys actually use.
- **Budget alerts** notify but do not cap spend. Consider adding a low budget alert in the Cloud Console as an early warning.

## 1. Prerequisites

- `gcloud` installed and logged in (`gcloud auth login`), with a project set (`gcloud config set project YOUR_PROJECT_ID`).
- Application Default Credentials authorized: `gcloud auth application-default login`.
- The root `.env` fully populated (see [README setup](README.md#setup-instructions)), including `SESSION_SECRET`. `.env` is **never** uploaded to Cloud Build (`.gcloudignore` excludes it) and never baked into the image; secrets come from Secret Manager.
- `scripts/setup_gcp.*` run once (enables APIs, creates Firestore, the `avatar-runtime` service account, and the secrets). No local Docker is needed — Cloud Build builds remotely.

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
| `COOKIE_SECURE` | `1` | production is HTTPS, so the admin session cookie must be `Secure` |
| `GOOGLE_CLOUD_PROJECT` | your project id | Firestore project |
| `FIRESTORE_DATABASE` | `(default)` | the only database with free quota |

Set as **Secret Manager secrets** (created by `setup_gcp.*` from `.env`, mounted as env vars at deploy):

`OPENROUTER_API_KEY`, `ADMIN_PASSWORD`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`, `SESSION_SECRET`.

Notes:
- **`SESSION_SECRET`** signs the admin session cookie. If it is absent from `.env`, `setup_gcp.*` generates a strong random value and stores it. Setting it explicitly means rotating `ADMIN_PASSWORD` later won't invalidate live admin sessions.
- **`MODEL`** is whatever is in `.env`. For production set `MODEL=openai/gpt-5.4-mini` before deploying (`openai/gpt-5.4-nano` is the cheaper dev/test model and the code default). Change it later by editing `.env` and redeploying, or `gcloud run services update avatar --region <region> --update-env-vars MODEL=...`.
- To rotate a secret: `printf '%s' NEW_VALUE | gcloud secrets versions add NAME --data-file=-`, then redeploy (or `gcloud run services update` to pick up `:latest`).

## 4. Testing (post-deploy smoke)

Run against the printed `https://<service>-<hash>.<region>.run.app` URL. Use `MODEL=openai/gpt-5.4-nano` for cheap test calls if you like, and clean up test data afterwards.

- [ ] `gcloud run services describe avatar --region <region> --format='value(status.url)'` returns the URL; the service is serving traffic.
- [ ] `curl -s <URL>/api/config` → `{"owner_name":"..."}` (200).
- [ ] `/` loads the visitor UI (dark + light, desktop + mobile); the rings background and the LinkedIn/YouTube footer render.
- [ ] A normal question streams a reply (real LLM call over SSE); `Q2` returns the instant FAQ; `<URL>/?q=2` opens and immediately answers Q2.
- [ ] FAQ routing works (e.g. ask about a NameError → `faq_tool`), and links in replies are clickable.
- [ ] `/admin` → wrong password rejected; correct `ADMIN_PASSWORD` opens the dashboard; the inbox lists conversations and a thread opens quickly. Without the cookie, `GET /admin/conversations` returns 401.
- [ ] Post a human message from admin → it appears in the visitor's chat within ~10 s (polling), styled as the "live" bubble.
- [ ] Contact-capture flow ("I'd like to get in touch", give an email) fires a **Pushover** notification and sets `needs_attention`.
- [ ] In DevTools, the admin session cookie has the **`Secure`** flag (confirms `COOKIE_SECURE=1`).
- [ ] Cloud Run logs show no Firestore auth errors, memory errors, or missing env vars: `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="avatar" AND severity>=WARNING' --freshness=15m`.
- [ ] Abuse guards work: a >20,000-character message is truncated (note appended), and a 21st message within a minute on one conversation returns HTTP 429 (no model call).
- [ ] Clean up: delete the test conversation threads from Firestore and any screenshots.

## 5. Success criteria

Deployment is successful when:
- The app is reachable at its `run.app` URL over HTTPS, with `min-instances=0`, `max-instances=1`, request-based billing, and the `avatar-runtime` service account.
- Firestore uses the default database and the parent-doc inbox aggregate model.
- All of the visitor, admin (login-gated), three-way human-in-the-loop, `Qn`/`?q=` instant answers, FAQ-tool routing, and Pushover paths work end to end.
- Secrets are configured via Secret Manager (never baked into the image); the admin cookie is `Secure`.
- Logs are clean.

## Abuse guards (built in)

Two cheap protections for your OpenRouter key are enforced in the backend, with no configuration:

- Visitor messages longer than 20,000 characters are truncated (with a note appended) before being stored or sent to the model.
- Each `conversation_id` is limited to 20 messages/minute; excess requests get HTTP 429 *before* any LLM call, and the visitor UI shows a friendly slow-down message.

The rate limit is in-memory per instance. With `max-instances=1` (the default here) it is exactly 20/min per conversation. Your OpenRouter account limits remain the overall backstop.

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
