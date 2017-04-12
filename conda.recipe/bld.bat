setlocal enabledelayedexpansion
%PYTHON% conda.recipe\setup.py install
if errorlevel 1 exit 1

%PYTHON% conda.recipe\setup.py --version > __conda_version__.txt

mkdir %PREFIX%\etc\fish\conf.d
if errorlevel 1 exit 1

copy %SRC_DIR%\shell\conda.fish %PREFIX%\etc\fish\conf.d
if errorlevel 1 exit 1

mkdir %PREFIX%\etc\profile.d
if errorlevel 1 exit 1

copy %SRC_DIR%\shell\conda.sh %PREFIX%\etc\profile.d\conda.sh
if errorlevel 1 exit 1
