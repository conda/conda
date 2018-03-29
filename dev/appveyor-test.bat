echo on
IF DEFINED SHELL_INTEGRATION GOTO :SHELL_INTEGRATION_TESTS

.\dev-init
py.test %ADD_COV% -m "not integration and not installed" -v
py.test %ADD_COV% --cov-append -m "integration and not installed" -v
codecov --env PYTHON_VERSION --required
python -m conda.common.io
GOTO :EOF


:SHELL_INTEGRATION_TESTS
REM this hard-codes __version__ in conda/__init__.py to speed up tests
%PYTHON_ROOT%\python -m conda._vendor.auxlib.packaging conda
%PYTHON_ROOT%\Scripts\py.test %ADD_COV% -m "installed" --shell=bash.exe --shell=cmd.exe
