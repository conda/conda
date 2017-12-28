:: Delegate to the Unixy script. We need to translate the key path variables
:: to be Unix-y rather than Windows-y, though.
set "saved_recipe_dir=%RECIPE_DIR%"
set "WIN_PREFIX=%PREFIX%"
FOR /F "delims=" %%i IN ('cygpath.exe -u -p "%PATH%"') DO set "PATH_OVERRIDE=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%LIBRARY_PREFIX%"') DO set "LIBRARY_PREFIX=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%PREFIX%"') DO set "PREFIX=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%PYTHON%"') DO set "PYTHON=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%RECIPE_DIR%"') DO set "RECIPE_DIR=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%SP_DIR%"') DO set "SP_DIR=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%SRC_DIR%"') DO set "SRC_DIR=%%i"
FOR /F "delims=" %%i IN ('cygpath.exe -u "%STDLIB_DIR%"') DO set "STDLIB_DIR=%%i"
set MSYSTEM=MINGW%ARCH%
set MSYS2_PATH_TYPE=inherit
set CHERE_INVOKING=1
bash -lc ". utils/functions.sh && install_conda_full"
if errorlevel 1 exit 1
