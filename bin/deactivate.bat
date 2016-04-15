@REM @ symbols in this file indicate that output should not be printed.
@REM   Setting it this way allows us to not touch the user's echo setting.
@REM   For debugging, remove the @ on the section you need to study.
@SETLOCAL

@IF NOT "%1" == "--help" @GOTO skipusage
    (
    @ECHO Usage: deactivate
    @ECHO.
    @ECHO Deactivates previously activated Conda
    @ECHO environment.
    @ECHO.
    @ECHO Additional arguments are ignored.
    ) 1>&2
    @EXIT /b 1
:skipusage

@REM Deactivate a previous activation if it is live
@IF "%CONDA_PATH_BACKUP%"=="" @GOTO NOPATH
   @SET "PATH=%CONDA_PATH_BACKUP%"
   @SET CONDA_PATH_BACKUP=
   :NOPATH

@IF "%CONDA_OLD_PS1%"=="" @GOTO NOPROMPT
   @SET "PROMPT=%CONDA_OLD_PS1%"
   @SET CONDA_OLD_PS1=
   :NOPROMPT

@ENDLOCAL & (
            REM Run any deactivate scripts
            @IF EXIST "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d" (
                @PUSHD "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d"
                @FOR %%g IN (*.bat) DO @CALL "%%g"
                @POPD
            )

            @SET "CONDA_DEFAULT_ENV="
            @SET "PATH=%PATH%"
            @SET "PROMPT=%PROMPT%"
           )
