$PYTHON_EXE = Resolve-Path "$PSScriptRoot\..\python.exe"
Write-Debug "PYTHON_EXE : $PYTHON_EXE"

$env:CONDA_EXE = Resolve-Path "$PSScriptRoot\..\Scripts\conda.exe"
Write-Debug "env:CONDA_EXE : $env:CONDA_EXE"

. $env:CONDA_EXE ..activate cmd.exe root

if ($env:PATH_OLD -ne $null) {
    $env:PATH = $env:PATH_OLD    
}

Function global:prompt 
{
    return "PS $($pwd.Path)>"
}