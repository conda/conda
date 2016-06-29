@REM @ symbols in this file indicate that output should not be printed.
@REM   Setting it this way allows us to not touch the user's echo setting.
@REM   For debugging, remove the @ on the section you need to study.
@SETLOCAL enabledelayedexpansion

@SET "CONDA_EXE=%~dp0\..\Scripts\conda.exe"

:: this finds either --help or -h and shows the help text
@CALL ECHO "%~1"| @%SystemRoot%\System32\find.exe /I "-h" 1>NUL
@IF NOT ERRORLEVEL 1 (
    @call "%~dp0\..\Scripts\conda.exe" ..deactivate "cmd.exe" -h
) else (
    :: reset errorlevel to 0
    cmd /c "exit /b 0"
)

@REM doesn't matter what the arg is, just that there is one.  Ideally, only the activate.bat script is ever
@REM     passing this.
@set "HOLD=%~1"

@REM Deactivate a previous activation if it is live
@IF "%CONDA_PREFIX%"=="" @GOTO NOPATH
   @REM get the activation path that would have been provided for this prefix
   @FOR /F "delims=" %%i IN ('@call "%CONDA_EXE%" ..activate "cmd.exe" "%CONDA_PREFIX%"') DO @SET "NEW_PATH=%%i"
   @REM in activate.bat, we replace a placeholder so that conda keeps its place in the PATH order
   @REM The activate.bat script passes an argument here to activate that behavior - otherwise, PATH
   @REM    is simply removed.
   @REM In both cases, we have to used delayed expansion to have the value of NEW_PATH in the replacement.
   @IF "%HOLD%" == "" (
       @CALL SET "PATH=%%PATH:!NEW_PATH!;=%%"
   ) ELSE (
       @CALL SET "PATH=%%PATH:!NEW_PATH!=CONDA_PATH_PLACEHOLDER%%"
   )
   :NOPATH

@IF "%CONDA_PS1_BACKUP%"=="" @GOTO NOPROMPT
   @SET "PROMPT=%CONDA_PS1_BACKUP%"
   @SET CONDA_PS1_BACKUP=
   :NOPROMPT

@ENDLOCAL & (
            REM Run any deactivate scripts
            @IF EXIST "%CONDA_PREFIX%\etc\conda\deactivate.d" (
                @PUSHD "%CONDA_PREFIX%\etc\conda\deactivate.d"
                @FOR %%g IN (*.bat) DO @CALL "%%g"
                @POPD
            )

            @SET "CONDA_DEFAULT_ENV="
            @SET "CONDA_PREFIX="
            @SET "PATH=%PATH%"
            @SET "PROMPT=%PROMPT%"
           )
