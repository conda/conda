@echo off
for /f "delims=" %%a in ('conda info --root') do @set root=%%a

if exist "%root%\Scripts\env-activate.bat" goto activate

    echo We're making conda environments even better!  Part of this process
    echo is changing the way environment activation works.  You need to
    echo install the new conda-env package before you can use these features:
    echo .
    echo     conda install -c conda conda-env
    echo .
    echo For more information, please visit: https://github.com/conda/conda-env
    echo .
    goto done

:activate
    set args=%*
    call "%root%\Scripts\env-activate.bat" %args%

:done
