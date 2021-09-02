@ECHO ON
pushd %TEMP% || goto :error

set CONDA=C:\Miniconda || goto :error
mklink /J \conda_bin %CONDA% || goto :error
mklink /J \conda_src %GITHUB_WORKSPACE% || goto :error

cd \conda_src || goto :error
CALL \conda_bin\scripts\activate.bat || goto :error
CALL conda create -n conda-test-env -y python=%PYTHON% pywin32 --file=tests\requirements.txt || goto :error
CALL conda activate conda-test-env || goto :error
CALL conda install -yq pip conda-build conda-verify || goto :error
CALL conda update openssl ca-certificates certifi || goto :error
python -m conda init cmd.exe --dev || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
