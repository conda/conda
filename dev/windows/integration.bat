@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
:: TODO --store-durations --durations-path=.\tools\durations\Windows.json
:: --splitting-algorithm=least_duration (causes tests to fail)
CALL pytest ^
    --cov=conda ^
    -m "integration" ^
    --basetemp=C:\tmp ^
    "tests/test_activate.py::test_cmd_exe_basic_integration" || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
