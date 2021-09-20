@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
set CONDA_SOLVER_LOGIC=libsolv
CALL pytest -m "not integration" -v tests/core/test_solve.py || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
