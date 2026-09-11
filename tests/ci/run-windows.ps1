param([string]$Subdir, [string]$TestType)

$ErrorActionPreference = 'Stop'
$pytestArgs = $args
if ($Subdir -eq 'win-arm64') {
    $env:PYTHONPATH = (Get-Location).Path
    $hook = python -m conda shell.powershell hook
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $hook | Out-String | Invoke-Expression
    $pytestArgs += "@tests/ci/win-arm64-$TestType.txt"
}

python -m pytest @pytestArgs
exit $LASTEXITCODE
