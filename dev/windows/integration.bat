@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
REM TODO:  Remove before merge, temporary:
CALL conda install "jaimergp/label/menuinst_dev::menuinst=2" --no-deps || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
CALL conda-build tests\test-recipes\activate_deactivate_package tests\test-recipes\pre_link_messages_package || goto :error
CALL pytest -m "integration" --basetemp=C:\tmp -v --splits=%TEST_SPLITS% --group=%TEST_GROUP% || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
