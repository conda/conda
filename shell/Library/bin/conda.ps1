
# shell setup would be something like adding
#    . [CONDA_ROOT]/Library/bin/conda.ps1
# or
#    Get-ChildItem "[CONDA_ROOT]\Library\bin\conda.ps1" | %{.$_}

if ( "${_CONDA_EXE}" -eq "" ) {
  $scriptPath = split-path -parent $MyInvocation.MyCommand.Definition
  $_CONDA_EXE = "$scriptPath/../../bin/conda"
}


function conda {
    switch -r ($args[1]) {
        "^activate$" {
            Invoke-Expression -Command ($_CONDA_EXE shell.powershell activate $args[2..-1] | Out-String)
            break
        }
        "^deactivate$" {
            Invoke-Expression -Command ($_CONDA_EXE shell.powershell deactivate $args[2..-1] | Out-String)
            break
        }
        "^(install|update|remove|uninstall)$" {
            $_CONDA_EXE $args[1..-1]
            Invoke-Expression -Command ($_CONDA_EXE shell.powershell reactivate | Out-String)
            break
        }
        default {
            $_CONDA_EXE $args[1..-1]
            break
        }
    }
}


if ( $MyInvocation.InvocationName -ne '.' ) {
    conda $args[1..-1]
}
