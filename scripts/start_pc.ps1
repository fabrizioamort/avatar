# Build and run the Avatar container on Windows.
# Stops and removes any existing container, rebuilds the image, then runs it.
# Mounts local Application Default Credentials so the container reaches Firestore.
$ErrorActionPreference = "Stop"

$Image = "avatar"
$Name = "avatar"
$HostPort = "8000"
$ContainerPort = "8080"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Resolve the GCP project: prefer .env, fall back to the active gcloud config.
$Project = ""
$line = Select-String -Path .env -Pattern '^GOOGLE_CLOUD_PROJECT=' | Select-Object -First 1
if ($line) { $Project = $line.Line -replace '^GOOGLE_CLOUD_PROJECT=', '' }
if (-not $Project) { $Project = (gcloud config get-value project 2>$null) }

# Local Application Default Credentials to mount read-only into the container.
$Adc = Join-Path $env:APPDATA "gcloud\application_default_credentials.json"
if (-not (Test-Path $Adc)) {
    throw "ADC not found at $Adc. Run: gcloud auth application-default login"
}

Write-Host "Stopping any existing $Name container..."
docker rm -f $Name 2>$null | Out-Null

Write-Host "Building image $Image..."
docker build -t $Image .

Write-Host "Starting container $Name (project $Project)..."
docker run -d --name $Name --env-file .env `
    -e PORT=$ContainerPort `
    -e GOOGLE_CLOUD_PROJECT=$Project `
    -e GOOGLE_APPLICATION_CREDENTIALS=/gcp/adc.json `
    -v "${Adc}:/gcp/adc.json:ro" `
    -p "${HostPort}:${ContainerPort}" $Image

Write-Host "Avatar is running at http://localhost:$HostPort"
