@REM shebang not supported

@REM
@REM call deactivate for windows cmd.exe-shell
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
@SET "ENVVAR_CLEANUP_EXE=%~dp0envvar_cleanup.bat"

@REM note whether or not the CONDA_* variables are exported, if so we need to
@REM preserve that status
@SET "IS_ENV_CONDA_HELP=%FALSE%"
@SET "IS_ENV_CONDA_VERBOSE=%FALSE%"
@IF /I NOT "%CONDA_HELP%"=="" (
    @SET "IS_ENV_CONDA_HELP=%TRUE%"
)
@IF /I NOT "%IS_ENV_CONDA_VERBOSE%"=="" (
    @SET "IS_ENV_CONDA_VERBOSE=%TRUE%"
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

@REM ##########################################################################
@REM parse command line, perform command line error checking
@REM ##########################################################################
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
                                    @REM if it is undefined (check if unbounded) and if it is zero
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

    @SHIFT
    @GOTO while_argparse_start
:while_argparse_end
@SET arg=

@REM if any of these variables are undefined (i.e. unbounded) set them to a default
@IF /I "%CONDA_HELP%"==""    @SET "CONDA_HELP=%FALSE%"
@IF /I "%CONDA_VERBOSE%"=="" @SET "CONDA_VERBOSE=%FALSE%"

@REM export CONDA_* variables as necessary
@REM since this is Windows Batch all values are already "exported"

@REM ##########################################################################
@REM help dialog
@REM ##########################################################################
@IF /I "%CONDA_HELP%"=="%TRUE%" (
    @CALL "%CONDA_EXE%" "..deactivate" "%WHAT_SHELL_AM_I%" "-h" "%UNKNOWN%"

    @SET WHAT_SHELL_AM_I=
    @IF /I "%IS_ENV_CONDA_HELP%"=="%FALSE%"    @SET CONDA_HELP=
    @IF /I "%IS_ENV_CONDA_VERBOSE%"=="%FALSE%" @SET CONDA_VERBOSE=
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
@SET WHAT_SHELL_AM_I=
@IF /I "%IS_ENV_CONDA_HELP%"=="%FALSE%" @SET CONDA_HELP=
@SET IS_ENV_CONDA_HELP=
@SET UNKNOWN=

@REM ##########################################################################
@REM determine if there is anything to deactivate and deactivate
@REM accordingly
@REM ##########################################################################
@IF /I NOT "%CONDA_DEFAULT_ENV%"=="" (
    @REM restore PROMPT
    @IF /I NOT "%CONDA_PS1_BACKUP%"=="" (
        @SET "PROMPT=%CONDA_PS1_BACKUP%"
        @SET CONDA_PS1_BACKUP=
    )

    @REM remove CONDA_DEFAULT_ENV
    @SET CONDA_DEFAULT_ENV=

    @REM remove only first instance of %CONDA_PREFIX% from %PATH%, since this is
    @REM Windows there will be several paths that need to be removed but they will
    @REM all start with the same %CONDA_PREFIX%, consequently we will use fuzzy
    @REM matching (/f) to get all of the relevant removals
    @FOR /F "delims=" %%i IN ('@CALL "%ENVVAR_CLEANUP_EXE%" "%PATH%" /delim=";" /g "%CONDA_PREFIX%" /f') DO @SET "PATH=%%i"

    @REM remove CONDA_PREFIX
    @SET CONDA_PREFIX=

    @REM no rehash for .bat
)

@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%FALSE%" @SET CONDA_VERBOSE=
@SET IS_ENV_CONDA_VERBOSE=
@SET TRUE=
@SET FALSE=

@ENDLOCAL && (
    @REM unload post-activate scripts
    @REM scripts found in %CONDA_PREFIX%\etc\conda\deactivate.d
    @SET "_CONDA_DIR=%CONDA_PREFIX%\etc\conda\deactivate.d"
    @IF EXIST "%_CONDA_DIR%" (
        @PUSHD "%_CONDA_DIR%"
        @FOR %%f IN (*.bat) DO (
            @IF "%CONDA_VERBOSE%"=="%TRUE%" @ECHO "[ACTIVATE]: Sourcing %_CONDA_DIR%\%%f."
            @CALL "%%f"
        )
        @POPD
    )
    @SET _CONDA_DIR=

    @SET "CONDA_PREFIX=%CONDA_PREFIX%"
    @SET "CONDA_DEFAULT_ENV=%CONDA_DEFAULT_ENV%"
    @SET "CONDA_PS1_BACKUP=%CONDA_PS1_BACKUP%"
    @SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
    @SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
    @SET "CONDA_HELP=%CONDA_HELP%"
    @SET "PATH=%PATH%"
    @SET "PROMPT=%PROMPT%"
)

@EXIT /B 0
