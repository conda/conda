setlocal enabledelayedexpansion
set CONDA_DEFAULT_ENV=
%PYTHON% setup.py install
if errorlevel 1 exit 1

%PYTHON% setup.py --version > __conda_version__.txt

mkdir %PREFIX%\etc\fish\conf.d
if errorlevel 1 exit 1

copy %SRC_DIR%\shell\conda.fish %PREFIX%\etc\fish\conf.d
if errorlevel 1 exit 1
