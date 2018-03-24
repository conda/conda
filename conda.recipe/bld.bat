echo %PKG_VERSION% > conda\.version
python setup.py install --single-version-externally-managed --record record.txt
if %errorlevel% neq 0 exit /b %errorlevel%

conda init --install
if %errorlevel% neq 0 exit /b %errorlevel%
