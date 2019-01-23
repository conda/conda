@pushd "%1"
@IF EXIST "%2.trash" del "%2.trash"
@ren "%2" "%2.trash"