@echo off
for /f "delims=" %%a in ('conda info --root') do @set root=%%a

if exist "%root%\Scripts\env-activate.bat" goto activate
    echo You must install conda-env before using environments. Please
    echo run the following command before proceeding:
    echo.
    echo     conda install -c conda conda-env
    echo.
    goto done

:activate
    set args=%*
    call %root%\Scripts\env-activate.bat %args%

:done
