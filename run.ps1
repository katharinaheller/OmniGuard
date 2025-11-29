# Load .env manually before ddtrace-run # 
$envFile = Join-Path $PSScriptRoot ".env"

if (Test-Path $envFile) {
    Write-Host "Loading environment variables from .env..."
    $lines = Get-Content $envFile | Where-Object { $_ -match "=" -and $_ -notmatch "^\s*#" }

    foreach ($line in $lines) {
        $pair = $line -split "=", 2
        $key = $pair[0].Trim()
        $value = $pair[1].Trim()

        if ($key -and $value) {
            Write-Host "Setting $key"
            Set-Item -Path Env:$key -Value $value
        }
    }
} else {
    Write-Host "No .env file found. Skipping environment loading."
}

# Default Datadog site #
if (-not $env:DD_SITE) {
    $env:DD_SITE = "datadoghq.eu"
}

Write-Host "Starting OmniGuard with ddtrace-run..."
uv run ddtrace-run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
