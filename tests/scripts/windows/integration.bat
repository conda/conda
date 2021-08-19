@ECHO ON
pushd %TEMP%
cd \conda_src
CALL dev-init.bat
CALL conda-build tests\test-recipes\activate_deactivate_package
CALL pytest -m "integration" --basetemp=C:\tmp -v --splits=%TEST_SPLITS% --group=%TEST_GROUP%
