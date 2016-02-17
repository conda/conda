set CONDA_DEFAULT_ENV=

%PYTHON% setup.py install
if errorlevel 1 exit 1
