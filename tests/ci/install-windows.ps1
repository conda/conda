param([string]$PythonVersion)

$ErrorActionPreference = 'Stop'
$ciRequirements = 'tests\requirements-ci.txt'
if ($env:CONDA_SUBDIR -eq 'win-arm64') {
    # Run conda from the checkout and use Git supplied by the runner.
    # Neither package is published for win-arm64 yet.
    $ciRequirements = "$env:RUNNER_TEMP\requirements-ci-native.txt"
    Get-Content tests\requirements-ci.txt |
        Where-Object { $_ -notmatch '^(conda|git)(\s|$)' } |
        Set-Content $ciRequirements
}

conda install `
    --yes `
    --file tests\requirements.txt `
    --file tests\requirements-Windows.txt `
    --file $ciRequirements `
    --file tests\requirements-s3.txt `
    python=$PythonVersion
exit $LASTEXITCODE
