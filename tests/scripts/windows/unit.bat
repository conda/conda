@ECHO ON
pushd %TEMP%
cd %GITHUB_WORKSPACE%
CALL dev-init.bat
CALL pytest -m "not integration and not installed" -v --splits=%GROUP_COUNT% --group=%TEST_GROUP%
