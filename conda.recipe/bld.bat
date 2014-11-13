cd %RECIPE_DIR%\..
"%PYTHON%" setup.py install
if errorlevel 1 exit 1
