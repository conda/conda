@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
CALL pytest ^
    --cov=conda ^
    --durations-path=.\tools\durations\Windows.json ^
    -m "not integration" ^
    --splits=%TEST_SPLITS% ^
    --group=%TEST_GROUP% || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
