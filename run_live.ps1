$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "."

# -----------------------------------------------------------------------------
# Base settings
# -----------------------------------------------------------------------------

$pythonCmd = "python"
$environmentName = "dev"
$desiredStatePath = "registry/desired_state.json"

# -----------------------------------------------------------------------------
# Target Oracle DB
# -----------------------------------------------------------------------------

$targetDbHost = "192.168.96.97"
$targetDbPort = "1521"
$targetDbService = "OASIPDB"
$targetDbUser = "rawdata"
$targetDbPassword = "rawdata"

$targetDbDsn = "${targetDbHost}:$targetDbPort/$targetDbService"
$targetDbConnectString = "$targetDbUser/$targetDbPassword@//${targetDbHost}:$targetDbPort/$targetDbService"

# -----------------------------------------------------------------------------
# Source Oracle DB
# -----------------------------------------------------------------------------

$sourceDbHost = "192.168.96.100"
$sourceDbPort = "1521"
$sourceDbService = "SRCPDB"
$sourceDbUser = "source_user"
$sourceDbPassword = "source_user"

$sourceDbConnectString = "$sourceDbUser/$sourceDbPassword@//${sourceDbHost}:$sourceDbPort/$sourceDbService"
$sourceDbGlobalName = "SRCPDB"

# -----------------------------------------------------------------------------
# GoldenGate
# -----------------------------------------------------------------------------

$oggHost = "192.168.96.119"
$oggPort = "9010"
$oggProtocol = "http"
$oggBaseUrl = "${oggProtocol}://${oggHost}:$oggPort"
$oggDeployment = "GG-01"
$oggUser = "ggadmin"
$oggPassword = "1q2w3e!Q@W#E"

# -----------------------------------------------------------------------------
# Script commands
# -----------------------------------------------------------------------------

$attachExtractScript = "$pythonCmd scripts/attach_extract_adapter.py {request} {response}"
$initialLoadScript = "$pythonCmd scripts/initial_load_adapter.py {request} {response}"
$instantiationScript = "$pythonCmd scripts/instantiation_adapter.py {request} {response}"
$attachReplicatScript = "$pythonCmd scripts/attach_replicat_adapter.py {request} {response}"

# -----------------------------------------------------------------------------
# App config
# -----------------------------------------------------------------------------

$env:ENVIRONMENT_NAME = $environmentName
$env:DESIRED_STATE_PATH = $desiredStatePath

$env:ORACLE_USER = $targetDbUser
$env:ORACLE_PASSWORD = $targetDbPassword
$env:ORACLE_DSN = $targetDbDsn

# -----------------------------------------------------------------------------
# Step config
# -----------------------------------------------------------------------------

$env:PREPARE_SOURCE_ACTION = "APPLY"
$env:PREPARE_SOURCE_EXECUTOR = "DRY_RUN"

$env:ATTACH_EXTRACT_ACTION = "APPLY"
$env:ATTACH_EXTRACT_EXECUTOR = "SCRIPT"
$env:ATTACH_EXTRACT_SCRIPT_COMMAND = $attachExtractScript
$env:ATTACH_EXTRACT_SCRIPT_TIMEOUT_SEC = "1800"

$env:INITIAL_LOAD_ACTION = "APPLY"
$env:INITIAL_LOAD_EXECUTOR = "SCRIPT"
$env:INITIAL_LOAD_SCRIPT_COMMAND = $initialLoadScript
$env:INITIAL_LOAD_SCRIPT_TIMEOUT_SEC = "3600"

$env:INSTANTIATION_ACTION = "APPLY"
$env:INSTANTIATION_EXECUTOR = "SCRIPT"
$env:INSTANTIATION_SCRIPT_COMMAND = $instantiationScript
$env:INSTANTIATION_SCRIPT_TIMEOUT_SEC = "1800"

$env:ATTACH_REPLICAT_ACTION = "APPLY"
$env:ATTACH_REPLICAT_EXECUTOR = "SCRIPT"
$env:ATTACH_REPLICAT_SCRIPT_COMMAND = $attachReplicatScript
$env:ATTACH_REPLICAT_SCRIPT_TIMEOUT_SEC = "1800"

$env:ACTIVATION_ACTION = "APPLY"

# -----------------------------------------------------------------------------
# GoldenGate REST config
# -----------------------------------------------------------------------------

$env:OGG_REST_BASE_URL = $oggBaseUrl
$env:OGG_REST_USERNAME = $oggUser
$env:OGG_REST_PASSWORD = $oggPassword
$env:OGG_REST_DEPLOYMENT_NAME = $oggDeployment
$env:OGG_REST_VERIFY_SSL = "false"
$env:OGG_REST_MODE = "OGG_REST_REAL"
$env:OGG_REST_CONNECTION = "OracleGoldenGate"
$env:TRANDATA_SCOPE = "TABLE"
$env:ALLOW_REAL_PREPARE_SOURCE = "false"

# -----------------------------------------------------------------------------
# Initial load config
# -----------------------------------------------------------------------------

$env:SOURCE_DB_CONNECT_STRING = $sourceDbConnectString
$env:TARGET_DB_CONNECT_STRING = $targetDbConnectString
$env:SOURCE_DB_GLOBAL_NAME = $sourceDbGlobalName

$env:DATAPUMP_NETWORK_LINK = "source_link"
$env:DATAPUMP_DIRECTORY = "DATA_PUMP_DIR"
$env:INITIAL_LOAD_REQUIRE_EMPTY_TARGET = "true"
$env:DATAPUMP_DEFAULT_PARALLEL = "1"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

Write-Host "PREPARE_SOURCE_ACTION=$env:PREPARE_SOURCE_ACTION"
Write-Host "PREPARE_SOURCE_EXECUTOR=$env:PREPARE_SOURCE_EXECUTOR"
Write-Host "ATTACH_EXTRACT_ACTION=$env:ATTACH_EXTRACT_ACTION"
Write-Host "ATTACH_EXTRACT_EXECUTOR=$env:ATTACH_EXTRACT_EXECUTOR"
Write-Host "INITIAL_LOAD_ACTION=$env:INITIAL_LOAD_ACTION"
Write-Host "INITIAL_LOAD_EXECUTOR=$env:INITIAL_LOAD_EXECUTOR"
Write-Host "INSTANTIATION_ACTION=$env:INSTANTIATION_ACTION"
Write-Host "INSTANTIATION_EXECUTOR=$env:INSTANTIATION_EXECUTOR"
Write-Host "ATTACH_REPLICAT_ACTION=$env:ATTACH_REPLICAT_ACTION"
Write-Host "ATTACH_REPLICAT_EXECUTOR=$env:ATTACH_REPLICAT_EXECUTOR"
Write-Host "ACTIVATION_ACTION=$env:ACTIVATION_ACTION"

& $pythonCmd main.py