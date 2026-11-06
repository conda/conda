# Bootstrap and activate the conda development environment in PowerShell.
#
# Must be dot-sourced so the activation applies to the current session:
#
#     . .\dev\start.ps1 [options]
#
# All provisioning (download, install, create/update env) is done by start.bat so the
# two scripts cannot drift apart. Options are passed straight through to it, see
# `dev\start.bat /?`. This script only performs the PowerShell-specific activation.

# a script that isn't dot-sourced runs in a child scope and its changes are discarded
if ($MyInvocation.InvocationName -ne '.') {
    Write-Error 'start.ps1 must be dot-sourced to activate the environment: . .\dev\start.ps1'
    return
}

$startBat = Join-Path $PSScriptRoot 'start.bat'

# help and dry-run have nothing to activate, defer entirely to start.bat
if ($args | Where-Object { $_ -in '/?', '/N', '/n' }) {
    & cmd.exe /d /c "`"$startBat`" $args"
    return
}

# provision with start.bat, /E makes it print the resolved paths instead of activating
$output = & cmd.exe /d /c "`"$startBat`" /E $args" 2>&1
$exitCode = $LASTEXITCODE

# show progress and errors, but not the exported values
$output | Where-Object { "$_" -notmatch '^DEVENV:' } | ForEach-Object { Write-Host $_ }
if ($exitCode -ne 0) {
    Write-Error "start.bat failed with exit code $exitCode"
    return
}

$devenv = @{}
foreach ($line in $output) {
    if ("$line" -match '^DEVENV:([A-Z]+)=(.*)$') { $devenv[$Matches[1]] = $Matches[2] }
}
foreach ($key in 'NAME', 'ENV', 'SRC', 'BASEEXE', 'BASEPYTHONEXE', 'ROOT') {
    if (-not $devenv[$key]) {
        Write-Error "start.bat did not report '$key', cannot activate"
        return
    }
}

# deactivate any prior envs, matching start.bat
if ($Env:CONDA_SHLVL -and (Get-Command conda -ErrorAction SilentlyContinue)) {
    while ([int]$Env:CONDA_SHLVL -gt 0) {
        Write-Host "Deactivating $Env:CONDA_SHLVL environment(s)..."
        conda deactivate
        if ($LASTEXITCODE -ne 0) {
            Write-Error "failed to deactivate environment(s)"
            return
        }
    }
}

# import conda from our source code and not from site-packages
if ($Env:PYTHONPATH) {
    $Env:PYTHONPATH = "$($devenv.SRC);$Env:PYTHONPATH"
} else {
    $Env:PYTHONPATH = $devenv.SRC
}

# conda's PowerShell module runs whatever CONDA_EXE points at, point it at the base
# install so the env is activated by name rather than as "base"
Write-Host 'Initializing shell integration...'
$Env:CONDA_EXE = $devenv.BASEEXE
$Env:CONDA_PYTHON_EXE = $devenv.BASEPYTHONEXE
$Env:_CE_M = ''
$Env:_CE_CONDA = ''
$Env:CONDA_SHLVL = '0'

# use the module that start.bat just refreshed from this checkout, not the installed copy
$module = Join-Path $devenv.ENV 'shell\condabin\Conda.psm1'
if (-not (Test-Path $module)) { $module = Join-Path $devenv.ROOT 'shell\condabin\Conda.psm1' }
Import-Module $module -Global -Force -ArgumentList @{ ChangePs1 = $true }

Write-Host "Activating $($devenv.NAME)..."
conda activate $devenv.ENV
if ($LASTEXITCODE -ne 0) {
    Write-Error "failed to activate $($devenv.NAME)"
    return
}
