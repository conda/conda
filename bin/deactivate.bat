@echo off
for /f "delims=" %%a in ('conda info --root') do @set root=%%a

if exists "%root%\Scripts\env-deactivate.bat" goto deactivate
    echo You must install conda-env before using environments. Please
    echo run the following command before proceeding:
    echo.
    echo     conda install -c conda conda-env
    echo.
    goto done

:deactivate
    set args=%*
    call %root%\Scripts\env-deactivate.bat %args%

:done
