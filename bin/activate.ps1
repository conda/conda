<#
.SYNOPSIS
Activates a conda virtualenv.

.DESCRIPTION
Activate.ps1 and deactivate.ps1 recreates the existing virtualenv BAT files in PS1 format so they "just work" inside a Powershell session.
This isn't idiomatic Powershell, just a translation.
#>

Param(
    [string]$global:condaEnvName
)

# fix for pre-PS3 - creates $PSScriptRoot
if (-not $PSScriptRoot)
{
    $PSScriptRoot = Split-Path $MyInvocation.MyCommand.Path -Parent
}

# Get location of Anaconda installation
$anacondaInstallPath = (get-item $PSScriptRoot).parent.FullName

# Build ENVS path
$env:ANACONDA_ENVS = $anacondaInstallPath + '\envs'

if (-not $condaEnvName)
{
    Write-Host
    Write-Host "Usage: activate envname [-UpdateRegistry]"
    Write-Host
    Write-Host "Deactivates previously activated Conda environment, then activates the chosen one."
    Write-Host
    Write-Host
    exit
}

if (-not (Test-Path $env:ANACONDA_ENVS\$condaEnvName\Python.exe))
{
    Write-Host
    Write-Warning "No environment named `"$condaEnvName`" exists in $env:ANACONDA_ENVS."
    Write-Host
    Write-Host
    exit
}

# Deactivate a previous activation if it is live
if (Test-Path env:\CONDA_DEFAULT_ENV)
{
    Invoke-Expression deactivate.ps1
}

$env:CONDA_DEFAULT_ENV = $condaEnvName
Write-Host
Write-Host "Activating environment `"$env:CONDA_DEFAULT_ENV...`""
$env:ANACONDA_BASE_PATH = $env:PATH
$env:PATH="$env:ANACONDA_ENVS\$env:CONDA_DEFAULT_ENV\;$env:ANACONDA_ENVS\$env:CONDA_DEFAULT_ENV\Scripts\;$env:ANACONDA_BASE_PATH"
Write-Host
Write-Host

# Capture existing user prompt
function global:condaUserPrompt {''}
$function:condaUserPrompt = $function:prompt

function global:prompt
{
    # Add the virtualenv prefix to the current user prompt.
    Write-Host "[$condaEnvName] " -nonewline -ForegroundColor Red
    & $function:condaUserPrompt
}
