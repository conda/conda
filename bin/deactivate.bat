@REM @ symbols in this file indicate that output should not be printed.
@REM   Setting it this way allows us to not touch the user's echo setting.
@REM   For debugging, remove the @ on the section you need to study.
@SETLOCAL

:: this finds either --help or -h and shows the help text
@CALL ECHO "%~1"| @%SystemRoot%\System32\find.exe /I "-h" 1>NUL
@IF NOT ERRORLEVEL 1 (
    @call "%~dp0\..\Scripts\conda.exe" ..deactivate "cmd.exe" -h
) else (
    :: reset errorlevel to 0
    cmd /c "exit /b 0"
)

@REM Deactivate a previous activation if it is live
@IF "%CONDA_PATH_BACKUP%"=="" @GOTO NOPATH
   @SET "PATH=%CONDA_PATH_BACKUP%"
   @SET CONDA_PATH_BACKUP=
   :NOPATH

@IF "%CONDA_PS1_BACKUP%"=="" @GOTO NOPROMPT
   @SET "PROMPT=%CONDA_PS1_BACKUP%"
   @SET CONDA_PS1_BACKUP=
   :NOPROMPT

@ENDLOCAL & (
            REM Run any deactivate scripts
            @IF EXIST "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d" (
                @PUSHD "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d"
                @FOR %%g IN (*.bat) DO @CALL "%%g"
                @POPD
            )

            @SET "CONDA_DEFAULT_ENV="
            @SET "CONDA_PREFIX="
            @SET "PATH=%PATH%"
            @SET "PROMPT=%PROMPT%"
           )
