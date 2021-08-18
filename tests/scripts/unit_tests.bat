@ECHO ON
pushd %TEMP%
cd \conda_src
CALL dev-init.bat
CALL pytest -m "not integration and not installed" -v --splits=%GROUP_COUNT% --group=%TEST_GROUP%
