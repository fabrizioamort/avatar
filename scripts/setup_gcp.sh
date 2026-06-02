#!/usr/bin/env bash
# One-time GCP provisioning for Avatar: APIs, Firestore, Artifact Registry,
# the runtime service account, and Secret Manager secrets read from .env.
# Idempotent: safe to re-run. Firestore location is PERMANENT once created.
set -euo pipefail

PROJECT_ID="${1:-${PROJECT_ID:-}}"
REGION="${REGION:-europe-west8}"
SERVICE_NAME="${SERVICE_NAME:-avatar}"   # used by deploy_gcp.sh
REPOSITORY="${REPOSITORY:-avatar}"

if [ -z "$PROJECT_ID" ]; then
  echo "Usage: PROJECT_ID=your-project ./scripts/setup_gcp.sh   (or pass as first arg)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RUNTIME_SA="avatar-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
SECRETS=(OPENROUTER_API_KEY ADMIN_PASSWORD PUSHOVER_USER PUSHOVER_TOKEN SESSION_SECRET)

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

echo "== Setting active project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" >/dev/null

echo "== Enabling APIs"
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project "$PROJECT_ID"

echo "== Firestore default database"
if gcloud firestore databases describe --database='(default)' --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "   default database already exists; leaving as-is."
else
  echo "   NOTE: Firestore location is PERMANENT once created."
  read -r -p "   Create default Native database in '$REGION'? type yes: " ans
  if [ "$ans" = "yes" ]; then
    gcloud firestore databases create --database='(default)' --location="$REGION" \
      --type=firestore-native --project "$PROJECT_ID"
  else
    echo "   Skipped Firestore creation."
  fi
fi

echo "== Artifact Registry repository: $REPOSITORY ($REGION)"
if gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "   repository exists."
else
  gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker \
    --location="$REGION" --description="Avatar container images" --project "$PROJECT_ID"
fi

echo "== Runtime service account: $RUNTIME_SA"
if gcloud iam service-accounts describe "$RUNTIME_SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "   service account exists."
else
  gcloud iam service-accounts create avatar-runtime \
    --display-name="Avatar Cloud Run runtime" --project "$PROJECT_ID"
fi

echo "== Granting roles/datastore.user to runtime SA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" --role="roles/datastore.user" \
  --condition=None >/dev/null

echo "== Secrets (from .env)"
for key in "${SECRETS[@]}"; do
  val="$(env_value "$key")"
  if [ -z "$val" ] && [ "$key" = "SESSION_SECRET" ]; then
    val="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))' 2>/dev/null || openssl rand -base64 32)"
    echo "   $key not in .env; generated a random value."
  fi
  if [ -z "$val" ]; then
    echo "   WARNING: $key empty in .env; skipping." >&2
    continue
  fi
  if ! gcloud secrets describe "$key" --project "$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$key" --replication-policy=automatic --project "$PROJECT_ID" >/dev/null
  fi
  printf '%s' "$val" | gcloud secrets versions add "$key" --data-file=- --project "$PROJECT_ID" >/dev/null
  gcloud secrets add-iam-policy-binding "$key" \
    --member="serviceAccount:$RUNTIME_SA" --role="roles/secretmanager.secretAccessor" \
    --condition=None --project "$PROJECT_ID" >/dev/null
  echo "   $key stored and access granted."
done

echo "== Artifact Registry cleanup policy (keep 2 most recent, delete >30d)"
POLICY="$(mktemp)"
cat > "$POLICY" <<'JSON'
[
  {"name": "keep-recent", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 2}},
  {"name": "delete-stale", "action": {"type": "Delete"}, "condition": {"tagState": "any", "olderThan": "2592000s"}}
]
JSON
gcloud artifacts repositories set-cleanup-policies "$REPOSITORY" \
  --location="$REGION" --policy="$POLICY" --project "$PROJECT_ID" >/dev/null \
  || echo "   (cleanup policy not applied; continuing)"
rm -f "$POLICY"

echo
echo "Setup complete. Next, deploy with:"
echo "   PROJECT_ID=$PROJECT_ID REGION=$REGION ./scripts/deploy_gcp.sh"
