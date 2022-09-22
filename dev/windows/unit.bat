@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
REM TODO:  Remove before merge, temporary:
CALL conda install "jaimergp/label/menuinst_dev::menuinst=2" --no-deps || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
CALL pytest -m "not integration" -v --splits=%TEST_SPLITS% --group=%TEST_GROUP% || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
