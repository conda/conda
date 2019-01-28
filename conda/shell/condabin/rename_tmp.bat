@pushd "%1"
@REM Remove existing destination file
@IF EXIST "%3" del "%3"
@REM Rename src to dest
@ren "%2" "%3"