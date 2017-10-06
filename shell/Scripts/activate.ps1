[CmdletBinding()]
param (
    [parameter(Mandatory = $true)]
    [string]$CONDA_ENV_NAME
)

$PYTHON_EXE = Resolve-Path "$PSScriptRoot\..\python.exe"
Write-Debug "PYTHON_EXE : $PYTHON_EXE"

$env:PYTHONIOENCODING = (. "$PYTHON_EXE" -c "import ctypes; print(ctypes.cdll.kernel32.GetACP())")
Write-Debug "env:PYTHONIOENCODING : $env:PYTHONIOENCODING"

chcp $env:PYTHONIOENCODING

$env:CONDA_NEW_ENV = $CONDA_ENV_NAME
Write-Debug "env:CONDA_NEW_ENV : $env:CONDA_NEW_ENV"

$env:CONDA_EXE = Resolve-Path "$PSScriptRoot\..\Scripts\conda.exe"
Write-Debug "env:CONDA_EXE : $env:CONDA_EXE"

$env:NEW_PATH = (. $env:CONDA_EXE ..activate cmd.exe $CONDA_ENV_NAME)

if ($env:NEW_PATH -eq $null) 
{
    Write-Error "$CONDA_ENV_NAME not found !!!"
}
else 
{
    $env:PATH_OLD = $env:PATH
    $env:PATH = "$env:NEW_PATH;$env:PATH"
    
    Function global:prompt 
    {
        return "PS ($env:CONDA_NEW_ENV) $($pwd.Path)>"
    }
}