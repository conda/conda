@ECHO ON
:: Obtain abs path to the conda source root
pushd "%~dp0"
    set "TWO_DIRS_UP=..\..\"
    set "CONDA_SRC_PATH="
    pushd %TWO_DIRS_UP% || goto :error
        set "CONDA_SRC_PATH=%CD%"
    popd || goto :error
popd || goto :error

pushd %TEMP% || goto :error
set CONDA=C:\Miniconda || goto :error
mklink /J \conda_bin %CONDA% || goto :error
mklink /J \conda_src "%CONDA_SRC_PATH%" || goto :error

cd \conda_src || goto :error
CALL \conda_bin\scripts\activate.bat || goto :error
CALL conda create -n conda-test-env -y python=%PYTHON% pywin32 --file=tests\requirements.txt || goto :error
CALL conda activate conda-test-env || goto :error
python -m conda init --install || goto :error
python -m conda init cmd.exe --dev || goto :error

:: Download minio server needed for S3 tests and place it in our conda environment so is in PATH
:: You can pin to an older release by setting MINIO_RELEASE to 'archive/XXXX'

if "%MINIO_RELEASE%x" == "x" set "MINIO_RELEASE=minio.exe"
powershell.exe -Command "If (-Not (Test-Path 'minio.exe')) { Invoke-WebRequest -Uri 'https://dl.min.io/server/minio/release/windows-amd64/%MINIO_RELEASE%' -OutFile 'minio.exe' | Out-Null }" || goto :error
copy minio.exe %CONDA_PREFIX%\minio.exe || goto :error

goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
