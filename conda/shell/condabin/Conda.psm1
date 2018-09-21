
## DYNAMIC PARAMETERS ##########################################################

function New-ParameterAttribute {
    param(
        [switch] $Mandatory,
        [int] $Position
    );

    $ParameterAttribute = New-Object System.Management.Automation.ParameterAttribute;
    $ParameterAttribute.Mandatory = $Mandatory.IsPresent;
    $ParameterAttribute.Position = $Position;
    $ParameterAttribute | Write-Output;
}

function New-RuntimeParameter {
    [CmdletBinding()]
    param(
        [string]
        $ParameterName,

        [Parameter(ValueFromPipeline=$true)]
        [System.Attribute]
        $Attribute
    );

    begin {
        $AttributeCollection = New-Object System.Collections.ObjectModel.Collection[System.Attribute];
    }

    process {
        $AttributeCollection.Add($Attribute);
    }

    end {
        $RuntimeParameter = New-Object System.Management.Automation.RuntimeDefinedParameter($ParameterName, [string], $AttributeCollection);

        return $RuntimeParameter;
    }
}


function New-EnvironmentNameParameter() {
    param(
        [string]
        $ParameterName,

        [int]
        $Position = 0
    );


    $AttributeCollection = New-Object System.Collections.ObjectModel.Collection[System.Attribute];

    $AttributeCollection.Add((New-ParameterAttribute -Position $Position));

    $ValidEnvs = Get-CondaEnvironment | ForEach-Object { $_.Name } | Where-Object { $_.Length -ne 0 };
    $ValidateSetAttribute = New-Object System.Management.Automation.ValidateSetAttribute($ValidEnvs);
    $AttributeCollection.Add($ValidateSetAttribute);

    $RuntimeParameter = New-Object System.Management.Automation.RuntimeDefinedParameter($ParameterName, [string], $AttributeCollection);

    return $RuntimeParameter;
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
    param();

    begin {}

    process {
        # NB: the JSON output of conda env list does not include the names
        #     of each env, so we need to parse the fragile output instead.
        & $Env:CONDA_EXE env list | `
            Where-Object { -not $_.StartsWith("#") } | `
            Where-Object { -not $_.Trim().Length -eq 0 } | `
            ForEach-Object {
                $envLine = $_ -split "\s+";
                $Active = $envLine[1] -eq "*";
                [PSCustomObject] @{
                    Name = $envLine[0];
                    Active = $Active;
                    Path = if ($Active) {$envLine[2]} else {$envLine[1]};
                } | Write-Output;
            }
    }

    end {}
}

<#
    .SYNOPSIS
        Activates a conda enviroment, placing its commands and packages at
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
    );

    DynamicParam {
        $ParameterName = "Name";

        $RuntimeParameterDictionary = New-Object System.Management.Automation.RuntimeDefinedParameterDictionary;
        $RuntimeParameterDictionary.Add($ParameterName, (New-EnvironmentNameParameter $ParameterName -Position 0));
        return $RuntimeParameterDictionary;
    }

    begin {
        $Name = $PSBoundParameters[$ParameterName];

        $activateCommand = (& $Env:CONDA_EXE shell.powershell activate $Name | Out-String);
        Write-Verbose "[conda shell.powershell activate $Name]`n$activateCommand";
        Invoke-Expression -Command $activateCommand;
    }

    process {}

    end {}

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
    param();

    begin {
        $deactivateCommand = (& $Env:CONDA_EXE shell.powershell deactivate | Out-String);
        # If deactivate returns an empty string, we have nothing more to do,
        # so return early.
        if ($deactivateCommand.Trim().Length -eq 0) {
            return;
        }
        # NB: This is an utter hack.
        #     As of conda 4.5.9, the PowershellActivator class incorrectly emits
        #     Remove-Variable instead of Remove-Item Env:/, so we replace here.
        $deactivateCommand = $deactivateCommand.Replace(
            "Remove-Variable ", # NOTE THE SPACE. We want to eat the whole thing.
            "Remove-Item Env:/"
        );
        Write-Verbose "[conda shell.powershell deactivate]`n$deactivateCommand";
        Invoke-Expression -Command $deactivateCommand;
    }
    process {}
    end {}
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
function Invoke-Conda {
    [CmdletBinding()]
    param (
        [Parameter(
            Position=0, Mandatory=$false
        )]
        [string]
        $Command
    );

    DynamicParam {
        $RuntimeParameterDictionary = New-Object System.Management.Automation.RuntimeDefinedParameterDictionary;

        switch ($Command) {
            "activate" {
                $ParameterName = "Name";
                $RuntimeParameterDictionary.Add($ParameterName, (New-EnvironmentNameParameter $ParameterName -Position 1));
            }

            "deactivate" {
                # No dynamic parameters to add here.
            }

            default {
                # We want to be able to pass through unknown parameters.
                # To do so without having access to $Args, we make a whole bunch of
                # parameters with the [Parameter(Mandatory=$false, Position=$idx)]
                # attribute set for different values of $idx.
                # This effectively lets us make our own $Args.
                0..100 | `
                    ForEach-Object {
                        $param = New-ParameterAttribute -Position $_ | New-RuntimeParameter "Arg$_"
                        $RuntimeParameterDictionary.Add("Arg$_", $param);
                    }
            }
        }

        return $RuntimeParameterDictionary;
    }

    begin {
        switch ($Command) {
            "activate" {
                if ($PSBoundParameters.ContainsKey($ParameterName)) {
                    Enter-CondaEnvironment $PSBoundParameters[$ParameterName];
                } else {
                    Enter-CondaEnvironment
                }
            }
            "deactivate" {
                Exit-CondaEnvironment;
            }

            default {
                # There may be a command we don't know about, pass it through
                # verbatim.
                # Ideally, each such command would get added to the $Command
                # parameter as time goes on.
                $OtherArgs = 0..100 | `
                    ForEach-Object {
                        $PSBoundParameters["Arg$_"]
                    };
                & $Env:CONDA_EXE $Command $OtherArgs;
            }
        }
    }

    process {
    }

    end {
    }
}


## PROMPT MANAGEMENT ###########################################################

function Get-CurrentPrompt {
    $currentDefinition = (Get-Command prompt -ErrorAction SilentlyContinue).Definition;
    if (-not $currentDefinition) {
        # Make sure that a global prompt exists.
        function global:prompt {
            'PS> '
        }
    }
}

<#
    .SYNOPSIS
        Modifies the current prompt to show the currently activated conda
        environment, if any.
    .EXAMPLE
        Add-CondaEnvironmentToPrompt

        Causes the current session's prompt to display the currently activated
        conda environment.
#>
function Add-CondaEnvironmentToPrompt {
    [CmdletBinding()]
    param(
        [switch]
        $NewLine
    );

    $oldPrompt = Get-CurrentPrompt;

    if ($NewLine) {
        Set-Content Function:\prompt -Value {
            if ($Env:CONDA_PROMPT_MODIFIER) {
                $Env:CONDA_PROMPT_MODIFIER | Write-Host
            }
            & $oldPrompt;
        }
    } else {
        Set-Content Function:\prompt -Value {
            $Env:CONDA_PROMPT_MODIFIER | Write-Host -NoNewline;
            & $oldPrompt;
        }
    }

}

Add-CondaEnvironmentToPrompt

## ALIASES #####################################################################

New-Alias conda Invoke-Conda -Force
New-Alias genv Get-CondaEnvironment -Force
New-Alias etenv Enter-CondaEnvironment -Force
New-Alias exenv Exit-CondaEnvironment -Force
