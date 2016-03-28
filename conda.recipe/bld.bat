set CONDA_DEFAULT_ENV=
%PYTHON% setup.py install
if errorlevel 1 exit 1

del %SCRIPTS%\conda-init
if errorlevel 1 exit 1

%PYTHON% setup.py --version > __conda_version__.txt

:: link to exec folder as a more contained proxy.  Idea is that people can add exec folder to PATH
::    instead of bin, and have only activate & conda on PATH - no trampling other stuff.
mkdir %PREFIX%/exec

:: Assumes that you have some kind of bash on Windows active
for %%X in (bash.exe) do (set FOUND=%%~$PATH:X)
if defined FOUND (
   bash -c "ln -s %PREFIX%/Scripts/activate %PREFIX%/exec/activate"
   bash -c "ln -s %PREFIX%/Scripts/conda %PREFIX%/exec/conda"
)

:: bat file redirect
echo """%PREFIX%\Scripts\activate.bat"" %%*" > %PREFIX%\exec\activate.bat
echo """%PREFIX%\Scripts\conda.exe"" %%*" > %PREFIX%\exec\conda.bat

:: TODO: powershell?  Not tested.  Needs PR https://github.com/conda/conda/issues/626
:: echo "& ""%PREFIX%\Scripts\activate.ps1"" $argumentList" > %PREFIX\exec\activate.ps1
:: echo "& ""%PREFIX%\Scripts\conda.exe"" $argumentList" > %PREFIX\exec\conda.ps1
