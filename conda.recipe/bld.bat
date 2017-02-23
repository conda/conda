setlocal enabledelayedexpansion
%PYTHON% conda.recipe\setup.py install
if errorlevel 1 exit 1

%PYTHON% conda.recipe\setup.py --version > __conda_version__.txt

mkdir %PREFIX%\etc\fish\conf.d
if errorlevel 1 exit 1

copy %SRC_DIR%\shell\conda.fish %PREFIX%\etc\fish\conf.d
if errorlevel 1 exit 1

mkdir %SP_DIR%\conda\resources
if errorlevel 1 exit 1

copy %SRC_DIR%\conda\resources\* %SP_DIR%\conda\resources
if errorlevel 1 exit 1
