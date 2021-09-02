@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
CALL pytest -m "not integration" -v --splits=%TEST_SPLITS% --group=%TEST_GROUP% || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
