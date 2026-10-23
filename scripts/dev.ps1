param(
    [ValidateSet('Check', 'Test', 'Serve')][string]$Mode = 'Check',
    [switch]$BackendOnly,
    [switch]$DeviceTests
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Create .venv and install .[dev] first; see docs/local-privacy-scaffold.md.'
}

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed ($LASTEXITCODE)." }
}

# Save and restore process variables so this script never edits cloud or .env files.
$previous = @{}
Push-Location $projectRoot
try {
    foreach ($line in Get-Content -LiteralPath '.env.local.example') {
        if ($line -match '^([A-Z0-9_]+)=(.*)$') {
            $name = $Matches[1]
            $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
            [Environment]::SetEnvironmentVariable($name, $Matches[2], 'Process')
        }
    }
    Invoke-Checked $python @('-B', '-c', 'import pathlib, tomllib; p=tomllib.loads(pathlib.Path("config/privacy-mvp.toml").read_text()); assert p["deployment"]["record_authority"] == "owner_android_device"; assert p["privacy"]["audio_storage"] is False; print("Privacy design contract parsed. Run Android device tests to verify runtime protections.")')
    if ($Mode -eq 'Serve') {
        Invoke-Checked $python @('-B', '-m', 'uvicorn', 'knock_knock.api.main:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000')
    } elseif ($Mode -eq 'Test') {
        Invoke-Checked $python @('-B', '-m', 'pytest', '-p', 'no:cacheprovider')
        if (-not $BackendOnly) {
            $previous['KNOCK_KNOCK_BUILD_ROOT'] = [Environment]::GetEnvironmentVariable('KNOCK_KNOCK_BUILD_ROOT', 'Process')
            if (-not $env:KNOCK_KNOCK_BUILD_ROOT) {
                $env:KNOCK_KNOCK_BUILD_ROOT = Join-Path ([IO.Path]::GetTempPath()) 'knock-knock-private-build'
            }
            $gradleInit = Join-Path $PSScriptRoot 'gradle-isolated.init.gradle'
            Push-Location 'apps/android'
            try {
                Invoke-Checked '.\gradlew.bat' @('--no-daemon', '--max-workers=2', '-I', $gradleInit, 'testDebugUnitTest')
                if ($DeviceTests) {
                    Invoke-Checked '.\gradlew.bat' @('--no-daemon', '--max-workers=2', '-I', $gradleInit, 'connectedDebugAndroidTest')
                }
            } finally { Pop-Location }
        }
    }
} finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
    Pop-Location
}
