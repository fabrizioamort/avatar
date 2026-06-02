# Deploy Avatar to Cloud Run from source. Run scripts/setup_gcp.ps1 first.
# Non-secret config is passed as env vars; secrets are wired from Secret Manager.
param(
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = $(if ($env:REGION) { $env:REGION } else { "europe-west8" }),
    [string]$ServiceName = $(if ($env:SERVICE_NAME) { $env:SERVICE_NAME } else { "avatar" })
)
$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    throw "Usage: .\scripts\deploy_gcp.ps1 -ProjectId your-project   (or set `$env:PROJECT_ID)"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$RuntimeSa = "avatar-runtime@$ProjectId.iam.gserviceaccount.com"

# Read a value from .env, stripping one layer of surrounding quotes.
function Get-EnvValue([string]$key) {
    $m = Select-String -Path .env -Pattern "^$key=" | Select-Object -First 1
    if (-not $m) { return "" }
    $v = $m.Line.Substring($key.Length + 1)
    if ($v.Length -ge 2 -and $v[0] -eq $v[-1] -and ($v[0] -eq '"' -or $v[0] -eq "'")) {
        $v = $v.Substring(1, $v.Length - 2)
    }
    return $v
}

$Model = Get-EnvValue MODEL
if (-not $Model) { $Model = "openai/gpt-5.4-nano" }
$OwnerName = Get-EnvValue OWNER_NAME
if (-not $OwnerName) { $OwnerName = "Ed Donner" }

Write-Host "Deploying '$ServiceName' to Cloud Run ($Region, project $ProjectId)..."

# --source builds with Cloud Build and pushes to the cloud-run-source-deploy
# Artifact Registry repo. min-instances=0 (cold starts ok, no idle billing).
# max-instances=1 keeps the in-memory rate limiter correct. --cpu-throttling
# selects request-based billing (CPU only allocated while serving).
$envVars = "^@^MODEL=$Model@OWNER_NAME=$OwnerName@COOKIE_SECURE=1@GOOGLE_CLOUD_PROJECT=$ProjectId@FIRESTORE_DATABASE=(default)"
$secrets = "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest,PUSHOVER_USER=PUSHOVER_USER:latest,PUSHOVER_TOKEN=PUSHOVER_TOKEN:latest,SESSION_SECRET=SESSION_SECRET:latest"

gcloud run deploy $ServiceName `
    --source . `
    --project $ProjectId `
    --region $Region `
    --service-account $RuntimeSa `
    --allow-unauthenticated `
    --min-instances 0 `
    --max-instances 1 `
    --concurrency 40 `
    --memory 512Mi `
    --cpu 1 `
    --timeout 300 `
    --cpu-throttling `
    --port 8080 `
    --set-env-vars $envVars `
    --set-secrets $secrets

Write-Host ""
Write-Host "Done. Service URL:"
gcloud run services describe $ServiceName --region $Region --project $ProjectId --format="value(status.url)"
