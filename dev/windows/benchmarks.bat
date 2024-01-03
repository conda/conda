@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
:: installing the needed pytest plugin for codspeed.io
CALL pip install pytest-codspeed || goto :error
CALL python -m pytest -m "benchmark" --codspeed || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
