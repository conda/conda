@REM
@REM call activate for windows cmd.exe-shell
@REM

@REM @ symbols in this file indicate that output should not be printed
@REM setting it this way allows us to not touch the user's echo setting
@SETLOCAL EnableDelayedExpansion

@REM ##########################################################################
@REM Local vars
@REM ##########################################################################
@SET "TRUE=0"
@SET "FALSE=1"
@SET "WHAT_SHELL_AM_I=cmd.exe"
@SET "CONDA_EXE=%~dp0conda.exe"

@REM note whether or not the CONDA_* variables are exported, if so we need to
@REM preserve that status
@SET "IS_ENV_CONDA_HELP=%FALSE%"
@SET "IS_ENV_CONDA_VERBOSE=%FALSE%"
@SET "IS_ENV_CONDA_ENVNAME=%FALSE%"
@IF /I NOT "%CONDA_HELP%"=="" (
    @SET "IS_ENV_CONDA_HELP=%TRUE%"
)
@IF /I NOT "%IS_ENV_CONDA_VERBOSE%"=="" (
    @SET "IS_ENV_CONDA_VERBOSE=%TRUE%"
)
@IF /I NOT "%IS_ENV_CONDA_ENVNAME%"=="" (
    @SET "IS_ENV_CONDA_ENVNAME=%TRUE%"
)

@REM inherit whatever the user set
@IF /I "%CONDA_HELP%"=="" (
    @SET "CONDA_HELP=%FALSE%"
) ELSE (
    @IF /I "%CONDA_HELP%"=="false" (
        @SET "CONDA_HELP=%FALSE%"
    ) ELSE (
        @IF /I "%CONDA_HELP%"=="FALSE" (
            @SET "CONDA_HELP=%FALSE%"
        ) ELSE (
            @IF /I "%CONDA_HELP%"=="False" (
                @SET "CONDA_HELP=%FALSE%"
            ) ELSE (
                @IF /I "%CONDA_HELP%"=="true" (
                    @SET "CONDA_HELP=%TRUE%"
                ) ELSE (
                    @IF /I "%CONDA_HELP%"=="TRUE" (
                        @SET "CONDA_HELP=%TRUE%"
                    ) ELSE (
                        @IF /I "%CONDA_HELP%"=="True" (
                            @SET "CONDA_HELP=%TRUE%"
                        ) ELSE (
                            @SET "CONDA_HELP=%FALSE%"
                        )
                    )
                )
            )
        )
    )
)
@SET "UNKNOWN="
@IF /I "%CONDA_VERBOSE%"=="" (
    @SET "CONDA_VERBOSE=%FALSE%"
) ELSE (
    @IF /I "%CONDA_VERBOSE%"=="false" (
        @SET "CONDA_VERBOSE=%FALSE%"
    ) ELSE (
        @IF /I "%CONDA_VERBOSE%"=="FALSE" (
            @SET "CONDA_VERBOSE=%FALSE%"
        ) ELSE (
            @IF /I "%CONDA_VERBOSE%"=="False" (
                @SET "CONDA_VERBOSE=%FALSE%"
            ) ELSE (
                @IF /I "%CONDA_VERBOSE%"=="true" (
                    @SET "CONDA_VERBOSE=%TRUE%"
                ) ELSE (
                    @IF /I "%CONDA_VERBOSE%"=="TRUE" (
                        @SET "CONDA_VERBOSE=%TRUE%"
                    ) ELSE (
                        @IF /I "%CONDA_VERBOSE%"=="True" (
                            @SET "CONDA_VERBOSE=%TRUE%"
                        ) ELSE (
                            @SET "CONDA_VERBOSE=%FALSE%"
                        )
                    )
                )
            )
        )
    )
)
@IF /I "%CONDA_ENVNAME%"=="" (
    @SET "CONDA_ENVNAME="
)

@REM ##########################################################################
@REM parse command line, perform command line error checking
@REM ##########################################################################
@SET "is_envname_set=%FALSE%"
:while_argparse_start
    @SET "arg=%~1"

    @REM check if variable is blank, if so no need to check any further
    @IF "%arg%"=="" GOTO while_argparse_end

    @IF /I "%arg%"=="/h" (
        @SET "CONDA_HELP=%TRUE%"
    ) ELSE (
        @IF /I "%arg%"=="/help" (
            @SET "CONDA_HELP=%TRUE%"
        ) ELSE (
            @IF /I "%arg%"=="-h" (
                @SET "CONDA_HELP=%TRUE%"
            ) ELSE (
                @IF /I "%arg%"=="--help" (
                    @SET "CONDA_HELP=%TRUE%"
                ) ELSE (
                    @IF /I "%arg%"=="/v" (
                        @SET "CONDA_VERBOSE=%TRUE%"
                    ) ELSE (
                        @IF /I "%arg%"=="/verbose" (
                            @SET "CONDA_VERBOSE=%TRUE%"
                        ) ELSE (
                            @IF /I "%arg%"=="-v" (
                                @SET "CONDA_VERBOSE=%TRUE%"
                            ) ELSE (
                                @IF /I "%arg%"=="--verbose" (
                                    @SET "CONDA_VERBOSE=%TRUE%"
                                ) ELSE (
                                    @IF /I "%is_envname_set%"=="%FALSE%" (
                                        @SET "CONDA_ENVNAME=%arg%"
                                        @SET "is_envname_set=%TRUE%"
                                    ) ELSE (
                                        @REM check if variable is blank, append unknown accordingly
                                        @IF /I "%UNKNOWN%"=="" (
                                            @SET" UNKNOWN=%arg%"
                                        ) ELSE (
                                            @SET "UNKNOWN=%UNKNOWN% %arg%"
                                        )
                                        @SET "CONDA_HELP=%TRUE%"
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )

    @SHIFT
    @GOTO while_argparse_start
:while_argparse_end
@SET arg=
@SET is_envname_set=

@REM if any of these variables are undefined (i.e. unbounded) set them to a default
@IF /I "%CONDA_HELP%"==""    @SET "CONDA_HELP=%FALSE%"
@IF /I "%CONDA_VERBOSE%"=="" @SET "CONDA_VERBOSE=%FALSE%"
@IF /I "%CONDA_ENVNAME%"=="" @SET "CONDA_ENVNAME=root"

@REM export CONDA_* variables as necessary
@REM since this is Windows Batch all values are already "exported"

@REM ##########################################################################
@REM help dialog
@REM ##########################################################################
@IF /I "%CONDA_HELP%"=="%TRUE%" (
    @CALL "%CONDA_EXE%" "..activate" "%WHAT_SHELL_AM_I%" "-h" "%UNKNOWN%"

    @SET WHAT_SHELL_AM_I=
    @IF /I "%IS_ENV_CONDA_ENVNAME%"=="%FALSE%" @SET CONDA_ENVNAME=
    @IF /I "%IS_ENV_CONDA_HELP%"=="%FALSE%"    @SET CONDA_HELP=
    @IF /I "%IS_ENV_CONDA_VERBOSE%"=="%FALSE%" @SET CONDA_VERBOSE=
    @SET IS_ENV_CONDA_ENVNAME=
    @SET IS_ENV_CONDA_HELP=
    @SET IS_ENV_CONDA_VERBOSE=
    @SET TRUE=
    @SET FALSE=
    @REM check if variable is blank, error accordingly
    @IF /I NOT "%UNKNOWN%"=="" (
        @SET UNKNOWN=
        @EXIT /B 1
    ) ELSE (
        @SET UNKNOWN=
        @EXIT /B 0
    )
)
@IF /I "%IS_ENV_CONDA_HELP%"=="%FALSE%"    @SET CONDA_HELP=
@SET IS_ENV_CONDA_HELP=
@SET UNKNOWN=

@REM ##########################################################################
@REM configure virtual environment
@REM ##########################################################################
@CALL "%CONDA_EXE%" "..checkenv" "%WHAT_SHELL_AM_I%" "%CONDA_ENVNAME%"
@IF errorlevel 1 (
    @SET WHAT_SHELL_AM_I=
    @IF /I "%IS_ENV_CONDA_ENVNAME%"=="%FALSE%" @SET CONDA_ENVNAME=
    @IF /I "%IS_ENV_CONDA_VERBOSE%"=="%FALSE%" @SET CONDA_VERBOSE=
    @SET IS_ENV_CONDA_ENVNAME=
    @SET IS_ENV_CONDA_VERBOSE=
    @SET TRUE=
    @SET FALSE=
    @EXIT /B 1
)

@REM store remaining values that may get cleared by deactivate
@SET "_CONDA_WHAT_SHELL_AM_I=%WHAT_SHELL_AM_I%"
@SET "_CONDA_VERBOSE=%CONDA_VERBOSE%"
@SET "_IS_ENV_CONDA_VERBOSE=%IS_ENV_CONDA_VERBOSE%"

@REM ensure we deactivate any scripts from the old env
@CALL deactivate.bat

@REM restore boolean
@SET "TRUE=0"
@SET "FALSE=1"

@REM restore values
@SET "IS_ENV_CONDA_VERBOSE=%_IS_ENV_CONDA_VERBOSE%"
@SET "CONDA_VERBOSE=%_CONDA_VERBOSE%"
@SET "WHAT_SHELL_AM_I=%_CONDA_WHAT_SHELL_AM_I%"
@SET _IS_ENV_CONDA_VERBOSE=
@SET _CONDA_VERBOSE=
@SET _CONDA_WHAT_SHELL_AM_I=

@FOR /F "delims=" %%i IN ('@CALL "%CONDA_EXE%" "..activate" "%WHAT_SHELL_AM_I%" "%CONDA_ENVNAME%"') DO @SET "_CONDA_BIN=%%i"
@IF errorlevel 0 (
    @REM PATH
    @REM update path with the new conda environment
    @SET "PATH=%_CONDA_BIN%;%PATH%"

    @REM CONDA_PREFIX
    @REM always the full path to the activated environment
    @REM is not set when no environment is active
    FOR /F "delims=;" %%i IN ("%_CONDA_BIN%") DO @SET "CONDA_PREFIX=%%i"

    @REM CONDA_DEFAULT_ENV
    @REM the shortest representation of how conda recognizes your env
    @REM can be an env name, or a full path (if the string contains / it's a path)
    @IF /I NOT "%CONDA_ENVNAME:\=%"=="%CONDA_ENVNAME%" (
        @FOR /F %%i IN ('%CONDA_ENVNAME%') DO @SET "d=%%~dpi"
        @FOR /F %%i IN ('%CONDA_ENVNAME%') DO @SET "f=%%~ni"
        @SET "CONDA_DEFAULT_ENV=!d!\!f!"
        @SET d=
        @SET f=
    ) ELSE (
        @SET "CONDA_DEFAULT_ENV=%CONDA_ENVNAME%"
    )

    @REM PROMPT & CONDA_PS1_BACKUP
    @REM export PROMPT to restore upon deactivation
    @REM customize the PROMPT to show what environment has been activated
    @FOR /F "delims=" %%i IN ('@CALL "%CONDA_EXE%" "..changeps1"') DO @SET "_CONDA_CHANGEPS1=%%i"
    @IF /I "!_CONDA_CHANGEPS1!"=="1" @IF /I NOT "%PROMPT%"=="" (
        @SET "CONDA_PS1_BACKUP=%PROMPT%"
        @SET "PROMPT=(!CONDA_DEFAULT_ENV!) %PROMPT%"
    )
    @SET _CONDA_CHANGEPS1=

    @REM no rehash for .bat

    @SET WHAT_SHELL_AM_I=
    @SET _CONDA_BIN=
    @IF /I "%IS_ENV_CONDA_ENVNAME%"=="%FALSE%" @SET CONDA_ENVNAME=
    @IF /I "%IS_ENV_CONDA_VERBOSE%"=="%FALSE%" @SET CONDA_VERBOSE=
    @SET IS_ENV_CONDA_ENVNAME=
    @SET IS_ENV_CONDA_VERBOSE=
    @SET TRUE=
    @SET FALSE=
) ELSE (
    @SET WHAT_SHELL_AM_I
    @SET _CONDA_BIN
    @IF /I "%IS_ENV_CONDA_ENVNAME%"=="%FALSE%" @SET CONDA_ENVNAME=
    @IF /I "%IS_ENV_CONDA_VERBOSE%"=="%FALSE%" @SET CONDA_VERBOSE=
    @SET IS_ENV_CONDA_ENVNAME=
    @SET IS_ENV_CONDA_VERBOSE=
    @SET TRUE=
    @SET FALSE=

    @ENDLOCAL

    @EXIT /B 1
)

@ENDLOCAL && (
    @SET "PATH=%PATH%"
    @SET "PROMPT=%PROMPT%"
    @SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
    @SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
    @SET "CONDA_HELP=%CONDA_HELP%"
    @SET "CONDA_PREFIX=%CONDA_PREFIX%"
    @SET "CONDA_DEFAULT_ENV=%CONDA_DEFAULT_ENV%"
    @SET "CONDA_PS1_BACKUP=%CONDA_PS1_BACKUP%"

    @REM load post-activate scripts
    @REM scripts found in %CONDA_PREFIX%\etc\conda\activate.d
    @SET "_CONDA_DIR=%CONDA_PREFIX%\etc\conda\activate.d"
    @IF EXIST "%_CONDA_DIR%" (
        @PUSHD "%_CONDA_DIR%"
        @FOR %%f IN (*.bat) DO (
            @IF "%CONDA_VERBOSE%"=="%TRUE%" @ECHO "[ACTIVATE]: Sourcing %_CONDA_DIR%\%%f."
            @CALL "%%f"
        )
        @POPD
    )
    @SET _CONDA_DIR=
)
