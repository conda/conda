@ECHO ON
pushd %TEMP% || goto :error
cd \conda_src || goto :error
CALL dev-init.bat || goto :error
CALL conda info || goto :error
CALL mamba --version || goto :error
set CONDA_SOLVER_LOGIC=libmamba2
CALL pytest -m "not integration" -k "not TestClassicSolver" -v tests/core/solve/test_solve.py tests/test_solvers.py || goto :error
goto :EOF

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
