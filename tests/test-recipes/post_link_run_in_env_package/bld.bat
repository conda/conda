mkdir %PREFIX%\etc\conda\activate.d
copy %RECIPE_DIR%\activate_d_test.bat %PREFIX%\etc\conda\activate.d\test.bat

mkdir %PREFIX%\etc\conda\deactivate.d
echo "echo setting TEST_VAR" > %PREFIX%\etc\conda\deactivate.d\test.bat
echo set TEST_VAR= > %PREFIX%\etc\conda\deactivate.d\test.bat
