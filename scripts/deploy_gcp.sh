#!/usr/bin/env bash
# Deploy Avatar to Cloud Run from source. Run scripts/setup_gcp.sh first.
# Non-secret config is passed as env vars; secrets are wired from Secret Manager.
set -euo pipefail

PROJECT_ID="${1:-${PROJECT_ID:-}}"
REGION="${REGION:-europe-west8}"
SERVICE_NAME="${SERVICE_NAME:-avatar}"

if [ -z "$PROJECT_ID" ]; then
  echo "Usage: PROJECT_ID=your-project ./scripts/deploy_gcp.sh   (or pass as first arg)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RUNTIME_SA="avatar-runtime@${PROJECT_ID}.iam.gserviceaccount.com"

# Read a value from .env, stripping one layer of surrounding quotes.
env_value() {
  local key="$1" v
  v="$(grep -E "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
  if [ ${#v} -ge 2 ]; then
    local first="${v:0:1}" last="${v: -1}"
    if { [ "$first" = '"' ] && [ "$last" = '"' ]; } || { [ "$first" = "'" ] && [ "$last" = "'" ]; }; then
      v="${v:1:${#v}-2}"
    fi
  fi
  printf '%s' "$v"
}

MODEL="$(env_value MODEL)"; [ -z "$MODEL" ] && MODEL="openai/gpt-5.4-nano"
OWNER_NAME="$(env_value OWNER_NAME)"; [ -z "$OWNER_NAME" ] && OWNER_NAME="Ed Donner"

echo "Deploying '$SERVICE_NAME' to Cloud Run ($REGION, project $PROJECT_ID)..."

# --source builds with Cloud Build and pushes to the cloud-run-source-deploy
# Artifact Registry repo. min-instances=0 (cold starts ok, no idle billing).
# max-instances=1 keeps the in-memory rate limiter correct. --cpu-throttling
# selects request-based billing (CPU only allocated while serving).
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --service-account "$RUNTIME_SA" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 40 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --cpu-throttling \
  --port 8080 \
  --set-env-vars "^@^MODEL=${MODEL}@OWNER_NAME=${OWNER_NAME}@COOKIE_SECURE=1@GOOGLE_CLOUD_PROJECT=${PROJECT_ID}@FIRESTORE_DATABASE=(default)" \
  --set-secrets "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest,PUSHOVER_USER=PUSHOVER_USER:latest,PUSHOVER_TOKEN=PUSHOVER_TOKEN:latest,SESSION_SECRET=SESSION_SECRET:latest"

echo
echo "Done. Service URL:"
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" \
  --format="value(status.url)"
