<#
.SYNOPSIS
Deactivates an existing conda virtualenv.

.DESCRIPTION
Activate.ps1 and deactivate.ps1 recreates the existing virtualenv BAT files in PS1 format so they "just work" inside a Powershell session.
This isn't idiomatic Powershell, just a translation.
#>

Param(
    [string]$condaEnvName
)

# fix for pre-PS3 - creates $PSScriptRoot
if (-not $PSScriptRoot)
{
    $PSScriptRoot = Split-Path $MyInvocation.MyCommand.Path -Parent
}

# Get location of Anaconda installation
$anacondaInstallPath = (Get-Item $PSScriptRoot).parent.FullName

# Build ENVS path
$env:ANACONDA_ENVS = $anacondaInstallPath + '\envs'

if (-not (Test-Path env:\CONDA_DEFAULT_ENV))
{
    Write-Host
    Write-Host "No active Conda environment detected."
    Write-Host
    Write-Host "Usage: deactivate"
    Write-Host "Deactivates previously activated Conda environment."
    Write-Host
    Write-Host
    exit
}

# Deactivate a previous activation if it is live
if (Test-Path env:\CONDA_DEFAULT_ENV)
{
    Write-Host
    Write-Host "Deactivating environment `"$env:CONDA_DEFAULT_ENV...`""

    # This removes the previous env from the path and restores the original path
    $env:PATH = $env:ANACONDA_BASE_PATH

    # Restore original user prompt
    $function:prompt = $function:condaUserPrompt

    # Clean up
    Remove-Item env:\CONDA_DEFAULT_ENV
    Remove-Item function:\condaUserPrompt

    Write-Host
    Write-Host
}
