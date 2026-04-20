param(
    [string]$EnvironmentName = "dev",
    [string]$MetadataDir = "metadata",
    [string]$DesiredStatePath = "registry/desired_state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-DefaultEnv {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $current = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($current)) {
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

function Require-Env {
    param(
        [Parameter(Mandatory = $true)][string]$Name
    )

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Environment variable '$Name' is required. Set it before running run_local.ps1."
    }
}

Set-DefaultEnv "ENVIRONMENT_NAME" $EnvironmentName
Set-DefaultEnv "BUILD_DESIRED_STATE_FROM_METADATA" "true"
Set-DefaultEnv "METADATA_DIR" $MetadataDir
Set-DefaultEnv "DESIRED_STATE_PATH" $DesiredStatePath

# Safe local defaults: rebuild desired_state, generate artifacts, avoid real apply.
Set-DefaultEnv "PREPARE_SOURCE_MODE" "DRY_RUN"
Set-DefaultEnv "PREPARE_SOURCE_EXECUTOR" "DRY_RUN"
Set-DefaultEnv "ATTACH_EXTRACT_MODE" "FILE_ONLY"
Set-DefaultEnv "ATTACH_EXTRACT_EXECUTOR" "FILE_ONLY"
Set-DefaultEnv "INITIAL_LOAD_MODE" "DRY_RUN"
Set-DefaultEnv "INITIAL_LOAD_EXECUTOR" "DRY_RUN"
Set-DefaultEnv "INSTANTIATION_MODE" "DRY_RUN"
Set-DefaultEnv "INSTANTIATION_EXECUTOR" "DRY_RUN"
Set-DefaultEnv "ATTACH_REPLICAT_MODE" "FILE_ONLY"
Set-DefaultEnv "ATTACH_REPLICAT_EXECUTOR" "FILE_ONLY"
Set-DefaultEnv "ACTIVATION_MODE" "DRY_RUN"
Set-DefaultEnv "ACTIVATION_EXECUTOR" "DRY_RUN"

Require-Env "ORACLE_USER"
Require-Env "ORACLE_PASSWORD"
Require-Env "ORACLE_DSN"

$python = $null
if (Test-Path ".\.venv\Scripts\python.exe") {
    $python = (Resolve-Path ".\.venv\Scripts\python.exe").Path
} elseif (Test-Path ".\venv\Scripts\python.exe") {
    $python = (Resolve-Path ".\venv\Scripts\python.exe").Path
} else {
    $python = "python"
}

Write-Host "Running ogg_orchestrator locally..."
Write-Host "  ENVIRONMENT_NAME=$env:ENVIRONMENT_NAME"
Write-Host "  BUILD_DESIRED_STATE_FROM_METADATA=$env:BUILD_DESIRED_STATE_FROM_METADATA"
Write-Host "  METADATA_DIR=$env:METADATA_DIR"
Write-Host "  DESIRED_STATE_PATH=$env:DESIRED_STATE_PATH"
Write-Host "  PREPARE_SOURCE_EXECUTOR=$env:PREPARE_SOURCE_EXECUTOR"
Write-Host "  ATTACH_EXTRACT_EXECUTOR=$env:ATTACH_EXTRACT_EXECUTOR"
Write-Host "  INITIAL_LOAD_EXECUTOR=$env:INITIAL_LOAD_EXECUTOR"
Write-Host "  INSTANTIATION_EXECUTOR=$env:INSTANTIATION_EXECUTOR"
Write-Host "  ATTACH_REPLICAT_EXECUTOR=$env:ATTACH_REPLICAT_EXECUTOR"
Write-Host "  ACTIVATION_EXECUTOR=$env:ACTIVATION_EXECUTOR"

& $python "main.py"
exit $LASTEXITCODE
