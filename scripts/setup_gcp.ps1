# One-time GCP provisioning for Avatar: APIs, Firestore, Artifact Registry,
# the runtime service account, and Secret Manager secrets read from .env.
# Idempotent: safe to re-run. Firestore location is PERMANENT once created.
param(
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = $(if ($env:REGION) { $env:REGION } else { "europe-west8" }),
    [string]$ServiceName = $(if ($env:SERVICE_NAME) { $env:SERVICE_NAME } else { "avatar" }),
    [string]$Repository = $(if ($env:REPOSITORY) { $env:REPOSITORY } else { "avatar" })
)
$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    throw "Usage: .\scripts\setup_gcp.ps1 -ProjectId your-project   (or set `$env:PROJECT_ID)"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$RuntimeSa = "avatar-runtime@$ProjectId.iam.gserviceaccount.com"
$Secrets = @("OPENROUTER_API_KEY", "ADMIN_PASSWORD", "PUSHOVER_USER", "PUSHOVER_TOKEN", "SESSION_SECRET")

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

Write-Host "== Setting active project: $ProjectId"
gcloud config set project $ProjectId | Out-Null

Write-Host "== Enabling APIs"
gcloud services enable `
    run.googleapis.com `
    firestore.googleapis.com `
    aiplatform.googleapis.com `
    artifactregistry.googleapis.com `
    cloudbuild.googleapis.com `
    secretmanager.googleapis.com `
    --project $ProjectId

Write-Host "== Firestore default database"
gcloud firestore databases describe --database="(default)" --project $ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   default database already exists; leaving as-is."
} else {
    Write-Host "   NOTE: Firestore location is PERMANENT once created."
    $ans = Read-Host "   Create default Native database in '$Region'? type yes"
    if ($ans -eq "yes") {
        gcloud firestore databases create --database="(default)" --location=$Region `
            --type=firestore-native --project $ProjectId
    } else {
        Write-Host "   Skipped Firestore creation."
    }
}

Write-Host "== Artifact Registry repository: $Repository ($Region)"
gcloud artifacts repositories describe $Repository --location=$Region --project $ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   repository exists."
} else {
    gcloud artifacts repositories create $Repository --repository-format=docker `
        --location=$Region --description="Avatar container images" --project $ProjectId
}

Write-Host "== Runtime service account: $RuntimeSa"
gcloud iam service-accounts describe $RuntimeSa --project $ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   service account exists."
} else {
    gcloud iam service-accounts create avatar-runtime `
        --display-name="Avatar Cloud Run runtime" --project $ProjectId
}

Write-Host "== Narrow runtime IAM roles"
$FirestoreRole = "avatarRuntimeFirestore"
$FirestorePerms = "datastore.databases.get,datastore.entities.create,datastore.entities.delete,datastore.entities.get,datastore.entities.list,datastore.entities.update"
gcloud iam roles describe $FirestoreRole --project $ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    gcloud iam roles update $FirestoreRole --project $ProjectId `
        --title="Avatar Firestore runtime" --permissions=$FirestorePerms --stage=GA | Out-Null
} else {
    gcloud iam roles create $FirestoreRole --project $ProjectId `
        --title="Avatar Firestore runtime" --permissions=$FirestorePerms --stage=GA | Out-Null
}
gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:$RuntimeSa" --role="projects/$ProjectId/roles/$FirestoreRole" `
    --condition=None | Out-Null

$VertexRole = "avatarRuntimeVertexPredict"
$VertexPerms = "aiplatform.endpoints.predict"
gcloud iam roles describe $VertexRole --project $ProjectId 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    gcloud iam roles update $VertexRole --project $ProjectId `
        --title="Avatar Vertex prediction runtime" --permissions=$VertexPerms --stage=GA | Out-Null
} else {
    gcloud iam roles create $VertexRole --project $ProjectId `
        --title="Avatar Vertex prediction runtime" --permissions=$VertexPerms --stage=GA | Out-Null
}
gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:$RuntimeSa" --role="projects/$ProjectId/roles/$VertexRole" `
    --condition=None | Out-Null

Write-Host "== Secrets (from .env)"
foreach ($key in $Secrets) {
    $val = Get-EnvValue $key
    if (-not $val -and $key -eq "ADMIN_PASSWORD") {
        $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
        $bytes = New-Object 'System.Byte[]' 24
        $rng.GetBytes($bytes)
        $val = [Convert]::ToBase64String($bytes)
        Write-Host "   $key not in .env; generated a random value. Retrieve it with:"
        Write-Host "      gcloud secrets versions access latest --secret=$key --project=$ProjectId"
    }
    if (-not $val -and $key -eq "SESSION_SECRET") {
        $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
        $bytes = New-Object 'System.Byte[]' 32
        $rng.GetBytes($bytes)
        $val = [Convert]::ToBase64String($bytes)
        Write-Host "   $key not in .env; generated a random value."
    }
    if (-not $val) {
        Write-Warning "   $key empty in .env; skipping."
        continue
    }
    gcloud secrets describe $key --project $ProjectId 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        gcloud secrets create $key --replication-policy=automatic --project $ProjectId | Out-Null
    }
    $tmp = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tmp, $val, (New-Object System.Text.UTF8Encoding($false)))
    gcloud secrets versions add $key --data-file=$tmp --project $ProjectId | Out-Null
    Remove-Item $tmp -Force
    gcloud secrets add-iam-policy-binding $key `
        --member="serviceAccount:$RuntimeSa" --role="roles/secretmanager.secretAccessor" `
        --condition=None --project $ProjectId | Out-Null
    Write-Host "   $key stored and access granted."
}

Write-Host "== Artifact Registry cleanup policy (keep 2 most recent, delete >30d)"
$policy = @'
[
  {"name": "keep-recent", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 2}},
  {"name": "delete-stale", "action": {"type": "Delete"}, "condition": {"tagState": "any", "olderThan": "2592000s"}}
]
'@
$policyFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($policyFile, $policy, (New-Object System.Text.UTF8Encoding($false)))
gcloud artifacts repositories set-cleanup-policies $Repository `
    --location=$Region --policy=$policyFile --project $ProjectId | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "   (cleanup policy not applied; continuing)" }
Remove-Item $policyFile -Force

Write-Host ""
Write-Host "Setup complete. Next, deploy with:"
Write-Host "   `$env:PROJECT_ID='$ProjectId'; `$env:REGION='$Region'; .\scripts\deploy_gcp.ps1"
