echo on
IF DEFINED SHELL_INTEGRATION GOTO :SHELL_INTEGRATION_TESTS

CALL dev-init.bat
if %errorlevel% neq 0 exit /b %errorlevel%

py.test %ADD_COV% -m "not integration and not installed" -v
if %errorlevel% neq 0 exit /b %errorlevel%

py.test %ADD_COV% --cov-append -m "integration and not installed" -v
if %errorlevel% neq 0 exit /b %errorlevel%

codecov --env PYTHON_VERSION --required
if %errorlevel% neq 0 exit /b %errorlevel%

python -m conda.common.io
if %errorlevel% neq 0 exit /b %errorlevel%

GOTO :EOF


:SHELL_INTEGRATION_TESTS
REM this hard-codes __version__ in conda/__init__.py to speed up tests
%PYTHON_ROOT%\python -m conda._vendor.auxlib.packaging conda
if %errorlevel% neq 0 exit /b %errorlevel%

%PYTHON_ROOT%\Scripts\py.test %ADD_COV% -m "installed" --shell=bash.exe --shell=cmd.exe
if %errorlevel% neq 0 exit /b %errorlevel%

