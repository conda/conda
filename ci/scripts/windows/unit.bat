@ECHO ON
pushd %TEMP%
cd \conda_src
CALL dev-init.bat
CALL pytest -m "not integration" -v
