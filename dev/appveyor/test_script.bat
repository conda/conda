echo on
IF DEFINED SHELL_INTEGRATION GOTO :SHELL_INTEGRATION_TESTS

CALL dev-init.bat || GOTO :ERROR
py.test %ADD_COV% -m "not integration and not installed" -v || GOTO :ERROR
py.test %ADD_COV% --cov-append -m "integration and not installed" -v || GOTO :ERROR
codecov --env PYTHON_VERSION --required || GOTO :ERROR
python -m conda.common.io || GOTO :ERROR
GOTO :EOF


:ERROR
@echo Failed with error #%errorlevel%.
exit /b %errorlevel%


:SHELL_INTEGRATION_TESTS
REM this hard-codes __version__ in conda/__init__.py to speed up tests
%PYTHON_ROOT%\python -m conda._vendor.auxlib.packaging conda || GOTO :ERROR
%PYTHON_ROOT%\Scripts\py.test %ADD_COV% -m "installed" --shell=bash.exe --shell=cmd.exe || GOTO :ERROR

