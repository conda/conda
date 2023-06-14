@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
CALL conda-build tests\test-recipes\activate_deactivate_package tests\test-recipes\pre_link_messages_package || goto :error
:: TODO --store-durations --durations-path=.\tools\durations\Windows.json
:: --splitting-algorithm=least_duration (causes tests to fail)
CALL pytest --cov=conda -m "integration" --basetemp=C:\tmp -v --splits=%TEST_SPLITS% --group=%TEST_GROUP% || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
