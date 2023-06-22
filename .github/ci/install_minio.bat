@ECHO ON

:: Download minio server needed for S3 tests and place it in our conda environment so is in PATH
:: You can pin to an older release by setting MINIO_RELEASE to 'archive/XXXX'

if "%MINIO_RELEASE%x" == "x" set "MINIO_RELEASE=minio.exe"
powershell.exe -Command "If (-Not (Test-Path 'minio.exe')) { Invoke-WebRequest -Uri 'https://dl.min.io/server/minio/release/windows-amd64/%MINIO_RELEASE%' -OutFile 'minio.exe' | Out-Null }" || goto :error
copy minio.exe %CONDA_PREFIX%\minio.exe || goto :error

goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
