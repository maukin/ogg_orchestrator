param(
    [Parameter(Mandatory = $true)]
    [string]$EnvFile
)

if (!(Test-Path $EnvFile)) {
    Write-Error "Env file not found: $EnvFile"
    exit 1
}

$env:PYTHONPATH = "."

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()

    if ([string]::IsNullOrWhiteSpace($line)) { return }
    if ($line.StartsWith("#")) { return }

    $parts = $line -split "=", 2
    if ($parts.Count -ne 2) { return }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
}

Write-Host "=== EFFECTIVE CONFIG ==="
python scripts\print_effective_config.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to print effective config"
    exit $LASTEXITCODE
}

Write-Host "=== RUN ORCHESTRATOR ==="
python main.py
exit $LASTEXITCODE