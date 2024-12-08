param([parameter(Position=0,Mandatory=$false)] [Hashtable] $CondaModuleArgs=@{})

# Defaults from before we had arguments.
if (-not $CondaModuleArgs.ContainsKey('ChangePs1')) {
    $CondaModuleArgs.ChangePs1 = $True
}

## ENVIRONMENT MANAGEMENT ######################################################

<#
    .SYNOPSIS
        Obtains a list of valid conda environments.

    .EXAMPLE
        Get-CondaEnvironment

    .EXAMPLE
        genv
#>
function Get-CondaEnvironment {
    [CmdletBinding()]
    param()

    process {
        $condaArgs = @($Env:CONDA_EXE, $Env:_CE_M, $Env:_CE_CONDA, "env", "list") | Where-Object { $_ -ne $null -and $_ -ne '' }
        & $condaArgs[0] $condaArgs[1..($condaArgs.Length-1)] | 
            Where-Object { -not $_.StartsWith("#") } | 
            Where-Object { -not $_.Trim().Length -eq 0 } | 
            ForEach-Object {
                $envLine = $_ -split "\s+"
                $Active = $envLine[1] -eq "*"
                [PSCustomObject] @{
                    Name = $envLine[0]
                    Active = $Active
                    Path = if ($Active) {$envLine[2]} else {$envLine[1]}
                } | Write-Output
            }
    }
}

<#
    .SYNOPSIS
        Activates a conda environment, placing its commands and packages at
        the head of $Env:PATH.

    .EXAMPLE
        Enter-CondaEnvironment base

    .EXAMPLE
        etenv base

    .NOTES
        This command does not currently support activating environments stored
        in a non-standard location.
#>
function Enter-CondaEnvironment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$false)][switch]$Stack,
        [Parameter(Position=0)][string]$Name
    )

    begin {
        $condaArgs = @($Env:CONDA_EXE, $Env:_CE_M, $Env:_CE_CONDA, "shell.powershell", "activate") | Where-Object { $_ -ne $null -and $_ -ne '' }
        
        if ($Stack) {
            $condaArgs += "--stack"
        }
        
        $condaArgs += $Name
        $activateCommand = & $condaArgs[0] $condaArgs[1..($condaArgs.Length-1)] | Out-String

        Write-Verbose "[conda shell.powershell activate $Name]`n$activateCommand"
        if (-not [string]::IsNullOrWhiteSpace($activateCommand)) {
            Invoke-Expression -Command $activateCommand
        } else {
            Write-Host "Failed to activate environment. The activate command returned empty."
        }
    }
}

<#
    .SYNOPSIS
        Deactivates the current conda environment, if any.

    .EXAMPLE
        Exit-CondaEnvironment

    .EXAMPLE
        exenv
#>
function Exit-CondaEnvironment {
    [CmdletBinding()]
    param()

    begin {
        $condaArgs = @($Env:CONDA_EXE, $Env:_CE_M, $Env:_CE_CONDA, "shell.powershell", "deactivate") | Where-Object { $_ -ne $null -and $_ -ne '' }
        $deactivateCommand = (& $condaArgs[0] $condaArgs[1..($condaArgs.Length-1)] | Out-String)

        if ($deactivateCommand.Trim().Length -eq 0) {
            return
        }
        Write-Verbose "[conda shell.powershell deactivate]`n$deactivateCommand"
        Invoke-Expression -Command $deactivateCommand
    }
}

## CONDA WRAPPER ###############################################################

<#
    .SYNOPSIS
        conda is a tool for managing and deploying applications, environments
        and packages.

    .PARAMETER Command
        Subcommand to invoke.

    .EXAMPLE
        conda install toolz
#>
function Invoke-Conda() {
    if ($Args.Count -eq 0) {
        $condaArgs = @($Env:CONDA_EXE, $Env:_CE_M, $Env:_CE_CONDA) | Where-Object { $_ -ne $null -and $_ -ne '' }
        & $condaArgs[0] $condaArgs[1..($condaArgs.Length-1)]
    }
    else {
        $Command = $Args[0]
        $OtherArgs = $Args[1..($Args.Count - 1)]
        switch ($Command) {
            "activate" {
                Enter-CondaEnvironment @OtherArgs
            }
            "deactivate" {
                Exit-CondaEnvironment
            }
            default {
                $condaArgs = @($Env:CONDA_EXE, $Env:_CE_M, $Env:_CE_CONDA, $Command) + $OtherArgs | Where-Object { $_ -ne $null -and $_ -ne '' }
                & $condaArgs[0] $condaArgs[1..($condaArgs.Length-1)]
            }
        }
    }
}

## TAB COMPLETION ##############################################################
# We borrow the approach used by posh-git, in which we override any existing
# functions named TabExpansion, look for commands we can complete on, and then
# default to the previously defined TabExpansion function for everything else.

if (Test-Path Function:\TabExpansion) {
    # Since this technique is common, we encounter an infinite loop if it's
    # used more than once unless we give our backup a unique name.
    Rename-Item Function:\TabExpansion CondaTabExpansionBackup
}

function Expand-CondaEnv() {
    param(
        [string]
        $Filter
    )

    $ValidEnvs = Get-CondaEnvironment
    $ValidEnvs |
        Where-Object { $_.Name -like "$filter*" } |
        ForEach-Object { $_.Name } |
        Write-Output
    $ValidEnvs |
        Where-Object { $_.Path -like "$filter*" } |
        ForEach-Object { $_.Path } |
        Write-Output
}

function Expand-CondaSubcommands() {
    param(
        [string]
        $Filter
    )

    $condaArgs = @($Env:CONDA_EXE, $Env:_CE_M, $Env:_CE_CONDA, "shell.powershell", "commands") | Where-Object { $_ -ne $null -and $_ -ne '' }
    & $condaArgs[0] $condaArgs[1..($condaArgs.Length-1)] | Where-Object { $_ -like "$Filter*" } | Write-Output
}

function TabExpansion($line, $lastWord) {
    $lastBlock = [regex]::Split($line, '[|;]')[-1].TrimStart()

    switch -regex ($lastBlock) {
        # Pull out conda commands we recognize first before falling through
        # to the general patterns for conda itself.
        "^conda activate (.*)" { Expand-CondaEnv $lastWord; break }
        "^etenv (.*)" { Expand-CondaEnv $lastWord; break }

        # If we got down to here, check arguments to conda itself.
        "^conda (.*)" { Expand-CondaSubcommands $lastWord; break }

        # Finally, fall back on existing tab expansion.
        default {
            if (Test-Path Function:\CondaTabExpansionBackup) {
                CondaTabExpansionBackup $line $lastWord
            }
        }
    }
}

## PROMPT MANAGEMENT ###########################################################

<#
    .SYNOPSIS
        Modifies the current prompt to show the currently activated conda
        environment, if any.
    .EXAMPLE
        Add-CondaEnvironmentToPrompt

        Causes the current session's prompt to display the currently activated
        conda environment.
#>
if ($CondaModuleArgs.ChangePs1) {
    # We use the same procedure to nest prompts as we did for nested tab completion.
    if (Test-Path Function:\prompt) {
        Rename-Item Function:\prompt CondaPromptBackup
    } else {
        function CondaPromptBackup() {
            # Restore a basic prompt if the definition is missing.
            "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
        }
    }

    function global:prompt() {
        if ($Env:CONDA_PROMPT_MODIFIER) {
            $Env:CONDA_PROMPT_MODIFIER | Write-Host -NoNewline
        }
        CondaPromptBackup
    }
}

## ALIASES #####################################################################

New-Alias conda Invoke-Conda -Force
New-Alias genv Get-CondaEnvironment -Force
New-Alias etenv Enter-CondaEnvironment -Force
New-Alias exenv Exit-CondaEnvironment -Force

## EXPORTS ###################################################################

Export-ModuleMember `
    -Alias * `
    -Function `
        Invoke-Conda, `
        Get-CondaEnvironment, `
        Enter-CondaEnvironment, Exit-CondaEnvironment, `
        TabExpansion, prompt
