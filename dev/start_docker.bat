@echo off
set "SCRIPT_DIR=%~dp0"
set "STARTFILE=%SCRIPT_DIR%docker.bashrc"

echo.echo "Initializing conda in dev mode..." > "%STARTFILE%"
echo.echo "Factory config is:" >> "%STARTFILE%"
echo.grep -e "conda location" -e "conda version" -e "python version" ^<(conda info -a) ^| sed 's/^^\s*/  /' >> "%STARTFILE%"
echo.eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)" >> "%STARTFILE%"
echo.echo "Done! Now running:" >> "%STARTFILE%"
echo.grep -e "conda location" -e "conda version" -e "python version" ^<(conda info -a) ^| sed 's/^^\s*/  /' >> "%STARTFILE%"

set "PY=%CONDA_DOCKER_PYTHON%"
if "%PY%"=="" set "PY=3.9"

docker.exe run -it -v "%SCRIPT_DIR%..":/opt/conda-src ghcr.io/conda/conda-ci:master-linux-python%PY% bash --rcfile /opt/conda-src/dev/docker.bashrc

rm "%STARTFILE%"
