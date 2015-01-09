python setup.py install
if errorlevel 1 exit 1

del %SCRIPTS%\conda-init
if errorlevel 1 exit 1
