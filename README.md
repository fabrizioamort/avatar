# Avatar

Interact with a digital version of you

## Introduction

This project is a web application for visitors to the site to interact with a Digital Twin of you. During their interaction, you can personally jump in (via an admin panel) and engage with the visitors direcly.

Video walk-through: https://youtu.be/srlhW4H-Gtg

## Setup instructions

All secrets live in a single `.env` file in the project root. By the end of this section it should contain:

```
OPENROUTER_API_KEY=sk-or-v1-...
MODEL=openai/gpt-5.4-nano
OWNER_NAME=Ed Donner
ADMIN_PASSWORD=your-chosen-admin-password
PUSHOVER_USER=...
PUSHOVER_TOKEN=...
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
FIRESTORE_DATABASE=(default)
SESSION_SECRET=a-long-random-string
COOKIE_SECURE=0
```

`OWNER_NAME` is the name of the person this Digital Twin represents (you). It is shown in the UI - the site header/subtitle, the page title, how the Avatar refers to itself, and on your own messages when you join a conversation from admin (e.g. "Ed Donner - live"). Set it to how you want your name to appear. It is configuration, never hardcoded, so each owner sets their own.

`SESSION_SECRET` signs the admin session cookie. It is optional locally - if unset, it is derived from `ADMIN_PASSWORD` - but set it to a long random value (e.g. run `openssl rand -hex 32`) so that changing your admin password later does not invalidate live admin sessions. `COOKIE_SECURE` gates whether that cookie requires HTTPS: leave it `0` (or unset) for local http; it is set to `1` automatically in production (see [Deploy to Cloud Run](#deploy-to-cloud-run)).

`GOOGLE_CLOUD_PROJECT` is your Google Cloud project id; `FIRESTORE_DATABASE` must be `(default)` (the Firestore free quota only applies to the default database). Both are set up in the next section.

### OpenRouter

The Avatar's LLM calls go through [OpenRouter](https://openrouter.ai). If you already have a key in `.env`, skip this.

1. Go to https://openrouter.ai and sign in (or sign up).
2. Click your avatar (top right) and choose **Keys**, or go straight to https://openrouter.ai/keys.
3. Click **Create Key**, give it a name (e.g. `avatar`), and click **Create**.
4. Copy the key (it starts with `sk-or-v1-`) and add it to `.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
5. Add some credit under **Settings > Credits** if your account has none. The Avatar uses the model in `MODEL`. `openai/gpt-5.4-nano` is very cheap and good for development and testing; for a live site, consider a stronger model such as `openai/gpt-5.4-mini` (just set `MODEL` accordingly).

### Google Cloud (Firestore)

Conversations are stored in **Firestore** (Native mode) on Google Cloud. There is no SQL or schema to create - the backend writes documents directly. You need the `gcloud` CLI ([install guide](https://cloud.google.com/sdk/docs/install)) and a Google Cloud project with billing enabled (Firestore, Cloud Run, and the rest sit comfortably inside the free tier for a personal site).

#### 1. Create a project and log in

1. Create a project at https://console.cloud.google.com/projectcreate (or reuse one), and note its **project id**.
2. Log in and set the project locally:
   ```
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. Authorize **Application Default Credentials** (ADC) - this is how the app authenticates to Firestore locally (and how the local Docker container does, by mounting the ADC file):
   ```
   gcloud auth application-default login
   ```
4. Add the project id to `.env`:
   ```
   GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
   FIRESTORE_DATABASE=(default)
   ```

#### 2. Provision Firestore and the rest with the setup script

The repo ships an idempotent setup script that enables the required APIs, creates the **default** Firestore Native database, the Artifact Registry repo, the Cloud Run runtime service account, and the Secret Manager secrets (read from `.env`). Run it once:

- macOS / Linux: `PROJECT_ID=YOUR_PROJECT_ID ./scripts/setup_gcp.sh`
- Windows: `.\scripts\setup_gcp.ps1 -ProjectId YOUR_PROJECT_ID`

It defaults to region `europe-west8` (Milan); pass `REGION=...` / `-Region ...` to choose another. **Firestore's location is permanent**, so the script confirms before creating the database. (If you only want local development, you can instead create just the database: `gcloud firestore databases create --database="(default)" --location=YOUR_REGION --type=firestore-native`.)

Firestore stores one document per message under `conversations/{conversation_id}/messages/{seq}`, plus a parent `conversations/{conversation_id}` aggregate that powers the admin inbox in a single read per conversation. Each message document carries `conversation_id`, `conversation_name`, `role` (`visitor`/`avatar`/`human`), `content`, `tool_calls`, `needs_attention`, `read`, `created_at`, and a per-conversation integer `id`.

> Authentication uses ADC end to end - no service-account JSON key is ever created, committed, or baked into the image. Locally you use your own ADC; on Cloud Run the app runs as the `avatar-runtime` service account.

### Validate the setup

Before running the app, confirm Firestore is reachable and writable with the connectivity test:

```
cd backend && uv run pytest tests/test_firestore_connection.py -v
```

All tests must pass. They check that a project id is resolvable (from `GOOGLE_CLOUD_PROJECT` or ADC), that `FIRESTORE_DATABASE` is `(default)`, and that a message can be inserted, read back (with the expected fields, including `needs_attention`, `read`, and `tool_calls`), and deleted. If a test fails, re-check the `gcloud` login / ADC steps and that the default database exists.

## Personalize the twin (the `knowledge/` folder)

The twin's knowledge and voice come from a few files in `knowledge/`, read into the system prompt at runtime. Edit these to make the twin yours:

- **`knowledge.md`** - a rich, first-person profile of you (background, work, courses, skills, personal notes). The main "who I am" source.
- **`style.md`** - how the twin should sound: voice and personality, formatting rules, and safety/guardrail rules for answering on the public internet.
- **`faq.jsonl`** - one JSON object per line. Each row has `faq` (number), `question` (the full question), `answer` (the full answer, in markdown), and `query` (a short, precise phrasing used only for routing). The prompt lists the `query` phrasings so the model can match a visitor's question to a number; the FAQ tool and the `Qn` shortcut then return the full original question and answer. Visitors can also type a bare `Qn` (e.g. `Q2`) for an instant answer with no LLM call, and a deep link like `…/?q=2` opens the chat and immediately asks Q2 (handy for sharing a direct answer or embedding).
- **`pic.jpg`** - your photo, used for the human avatar; a robotic variant is used for the twin (see `design-system/docs/avatar-generation.md`).

There is no vector database. (Earlier versions used `summary.txt` and a `linkedin.pdf`; these have been replaced by `knowledge.md` and `style.md`.)

A couple of owner-specific bits live in the frontend rather than `.env`: the **footer social links** in `frontend/index.html` point to the owner's LinkedIn and YouTube (update them to your own), and the avatar images in `frontend/public/` are generated from `pic.jpg` (see `design-system/docs/avatar-generation.md`). The background texture can also be swapped (rings / crosses / grid) via the `--grid-mark` token in `frontend/src/styles/tokens.css` — see `design-system/docs/background-texture.md`. The brand subtitle and any owner-specific copy are currently set for the default owner, so review those too when making the twin your own.

## Running the app

### Docker (recommended)

The app builds and runs as a single container. From the project root:

- macOS / Linux: `./scripts/start_mac.sh` to build and run, `./scripts/stop_mac.sh` to stop.
- Windows: `./scripts/start_pc.ps1` to build and run, `./scripts/stop_pc.ps1` to stop.

The start script stops any existing `avatar` container, rebuilds the image, and runs it with your root `.env`. When it finishes, open http://localhost:8000 (admin at http://localhost:8000/admin). Docker must be running.

### Local development

Run the backend and frontend in two terminals.

Backend (FastAPI on port 8000):

```
cd backend
uv run uvicorn app.main:app --reload --app-dir .
```

Frontend (Vite dev server):

```
cd frontend
npm install
npm run dev
```

Open the URL Vite prints. The Vite dev server proxies `/api` to the backend on http://localhost:8000, so run the backend alongside it. The visitor page (`/`) gets hot reload from Vite; `/admin` is proxied to the backend, so to preview admin changes, build the frontend (`npm run build`) and load `http://localhost:8000/admin` from the backend.

The visitor chat and the admin dashboard are both responsive (mobile and desktop, dark and light).

## Deploy to Cloud Run

The same single container deploys to **Google Cloud Run**. The full guide - free-tier notes, the runtime service account, secrets, the smoke-test checklist, and the (optional) custom domain - is in **[DEPLOY.md](DEPLOY.md)**. In short:

1. Run the setup script once (see [Google Cloud (Firestore)](#google-cloud-firestore) above) so the APIs, Firestore, the `avatar-runtime` service account, and the Secret Manager secrets all exist.
2. Make sure `.env` is fully populated. The setup script copies your secrets into Secret Manager; they are never baked into the image.
3. Deploy from source:
   - macOS / Linux: `PROJECT_ID=YOUR_PROJECT_ID ./scripts/deploy_gcp.sh`
   - Windows: `.\scripts\deploy_gcp.ps1 -ProjectId YOUR_PROJECT_ID`
4. The script runs `gcloud run deploy --source .` (build via Cloud Build), wires the secrets from Secret Manager, sets `COOKIE_SECURE=1`, and deploys with `min-instances=0` / `max-instances=1` (free-tier friendly; see DEPLOY.md for the tradeoffs).
5. The app is then live at the generated `https://<service>-<hash>.<region>.run.app` URL the script prints (admin at `/admin`).

Putting the app on your own website is **optional** - the `run.app` URL works on its own. A custom domain is deferred in v1 (Cloud Run's recommended custom-domain path uses an external load balancer, which is not free-tier friendly); see [DEPLOY.md](DEPLOY.md) and `scripts/wordpress-embed.html` for a paste-ready embed snippet.

## Built-in protections

The backend guards your API key automatically, with no configuration: visitor messages longer than 20,000 characters are truncated (with a short note appended) before being stored or sent to the model, and more than 20 messages per minute from a single conversation are rejected (HTTP 429, with a friendly slow-down message in the chat) before any model call is made.

