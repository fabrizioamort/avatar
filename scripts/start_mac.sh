#!/usr/bin/env bash
# Build and run the Avatar container on macOS/Linux.
# Stops and removes any existing container, rebuilds the image, then runs it.
# Mounts local Application Default Credentials so the container reaches Firestore.
set -euo pipefail

IMAGE="avatar"
NAME="avatar"
HOST_PORT="8000"
CONTAINER_PORT="8080"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Resolve the GCP project: prefer .env, fall back to the active gcloud config.
PROJECT="$(grep -E '^GOOGLE_CLOUD_PROJECT=' .env | head -1 | cut -d= -f2- || true)"
[ -z "$PROJECT" ] && PROJECT="$(gcloud config get-value project 2>/dev/null || true)"

# Local Application Default Credentials to mount read-only into the container.
ADC="$HOME/.config/gcloud/application_default_credentials.json"
if [ ! -f "$ADC" ]; then
  echo "ADC not found at $ADC. Run: gcloud auth application-default login" >&2
  exit 1
fi

echo "Stopping any existing $NAME container..."
docker rm -f "$NAME" >/dev/null 2>&1 || true

echo "Building image $IMAGE..."
docker build -t "$IMAGE" .

echo "Starting container $NAME (project $PROJECT)..."
docker run -d --name "$NAME" --env-file .env \
  -e PORT="$CONTAINER_PORT" \
  -e GOOGLE_CLOUD_PROJECT="$PROJECT" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/gcp/adc.json \
  -v "$ADC:/gcp/adc.json:ro" \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"

echo "Avatar is running at http://localhost:$HOST_PORT"
