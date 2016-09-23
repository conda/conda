@REM
@REM function to cleanup a :-delimited string
@REM
@REM usage: envvar_cleanup.bat "$ENV_VAR" [/d | /r "STR_TO_REMOVE" ... | /g "STR_TO_REMOVE" ...] [/delim=DELIM] [/f]
@REM
@REM where:
@REM    "$ENV_VAR"                  is the variable name to cleanup
@REM    /d,-d                       remove duplicates
@REM    /r,-r "STR_TO_REMOVE" ...   remove first instance of provided strings
@REM    /g,-g "STR_TO_REMOVE" ...   remove all instances of provided strings
@REM    /delim=DELIM,--delim=DELIM  specify what the delimit
@REM    /f,-f                       fuzzy matching in conjunction with /r and /g
@REM                                (not compatible with /d)
@REM
@REM reference:
@REM http://stackoverflow.com/questions/5837418/how-do-you-get-the-string-length-in-a-batch-file
@REM
@REM TODO:
@REM consider adding more path cleanup like symlinking paths that are longer than __
@REM
@REM @ symbols in this file indicate that output should not be printed
@REM setting it this way allows us to not touch the user's echo setting
@REM
@SETLOCAL EnableDelayedExpansion

@REM ##########################################################################
@REM Local vars
@REM ##########################################################################
@SET "TRUE=0"
@SET "FALSE=1"
@SET "SETTING=2"
@SET VARIABLE=
@SET "MODE=duplicate"
@SET "DELIM=:"
@SET "FUZZY=%FALSE%"
@SET STR_TO_REMOVE=
@SET STR_TO_REMOVE_I=-1

@REM at this point VARIABLE, MODE, DELIM, and STR_TO_REMOVE are
@REM defined and do not need to be checked for unbounded again

@REM ##########################################################################
@REM parse command line, perform command line error checking
@REM ##########################################################################
@SET "is_mode_set=%FALSE%"
@SET "is_delim_set=%FALSE%"
@SET "is_fuzzy_set=%FALSE%"
:while_argparse_start
    @SET "arg=%~1"

    :: check if variable is blank, if so no need to check any further
    @IF "%arg%"=="" GOTO while_argparse_end

    @IF /I "%is_delim_set%"=="%SETTING%" (
        @SET "DELIM=%arg%"
        @SET "is_delim_set=%TRUE%"
    ) ELSE (
        @IF /I "%arg%"=="/d" (
            @IF /I "%is_mode_set%"=="%FALSE%" (
                @SET "MODE=duplicate"
                @SET "is_mode_set=%TRUE%"
            ) ELSE (
                @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ^(%arg%^) 1>&2
                @EXIT /B 1
            )
        ) ELSE (
            @IF /I "%arg%"=="-d" (
                @IF /I "%is_mode_set%"=="%FALSE%" (
                    @SET "MODE=duplicate"
                    @SET "is_mode_set=%TRUE%"
                ) ELSE (
                    @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ^(%arg%^) 1>&2
                    @EXIT /B 1
                )
            ) ELSE (
                @IF /I "%arg%"=="/r" (
                    @IF /I "%is_mode_set%"=="%FALSE%" (
                        @SET "MODE=remove"
                        @SET "is_mode_set=%TRUE%"
                    ) ELSE (
                        @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ^(%arg%^) 1>&2
                        @EXIT /B 1
                    )
                ) ELSE (
                    @IF /I "%arg%"=="-r" (
                        @IF /I "%is_mode_set%"=="%FALSE%" (
                            @SET "MODE=remove"
                            @SET "is_mode_set=%TRUE%"
                        ) ELSE (
                            @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ^(%arg%^) 1>&2
                            @EXIT /B 1
                        )
                    ) ELSE (
                        @IF /I "%arg%"=="/g" (
                            @IF /I "%is_mode_set%"=="%FALSE%" (
                                @SET "MODE=global"
                                @SET "is_mode_set=%TRUE%"
                            ) ELSE (
                                @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ^(%arg%^) 1>&2
                                @EXIT /B 1
                            )
                        ) ELSE (
                            @IF /I "%arg%"=="-g" (
                                @IF /I "%is_mode_set%"=="%FALSE%" (
                                    @SET "MODE=global"
                                    @SET "is_mode_set=%TRUE%"
                                ) ELSE (
                                    @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ^(%arg%^) 1>&2
                                    @EXIT /B 1
                                )
                            ) ELSE (
                                @IF /I "%arg%"=="/f" (
                                    @IF /I "%is_fuzzy_set%"=="%FALSE%" (
                                        @SET "FUZZY=%TRUE%"
                                        @SET "is_fuzzy_set=%TRUE%"
                                    ) ELSE (
                                        @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set fuzzy more than once ^(%arg%^) 1>&2
                                        @EXIT /B 1
                                    )
                                ) ELSE (
                                    @IF /I "%arg%"=="-f" (
                                        @IF /I "%is_fuzzy_set%"=="%FALSE%" (
                                            @SET "FUZZY=%TRUE%"
                                            @SET "is_fuzzy_set=%TRUE%"
                                        ) ELSE (
                                            @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set fuzzy more than once ^(%arg%^) 1>&2
                                            @EXIT /B 1
                                        )
                                    ) ELSE (
                                        @IF /I "%arg%"=="/delim" (
                                            @IF /I "%is_delim_set%"=="%FALSE%" (
                                                @SET "is_delim_set=%SETTING%"
                                            ) ELSE (
                                                @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set delim more than once ^(%arg%^) 1>&2
                                                @EXIT /B 1
                                            )
                                        ) ELSE (
                                            @IF /I "%arg%"=="--delim" (
                                                @IF /I "%is_delim_set%"=="%FALSE%" (
                                                    @SET "is_delim_set=%SETTING%"
                                                ) ELSE (
                                                    @ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set delim more than once ^(%arg%^) 1>&2
                                                    @EXIT /B 1
                                                )
                                            ) ELSE (
                                                @IF /I "%arg%"=="/*" (
                                                    @ECHO [ENVVAR_CLEANUP]: ERROR: Unknown/Invalid flag/parameter ^(%arg%^) 1>&2
                                                ) ELSE (
                                                    @IF /I "%arg%"=="-*" (
                                                        @ECHO [ENVVAR_CLEANUP]: ERROR: Unknown/Invalid flag/parameter ^(%arg%^) 1>&2
                                                    ) ELSE (
                                                        @IF /I "%VARIABLE%"=="" (
                                                            @SET "VARIABLE=%arg%"
                                                        ) ELSE (
                                                            @SET /A "STR_TO_REMOVE_I+=1"
                                                            @SET "STR_TO_REMOVE[!STR_TO_REMOVE_I!]=%arg%"
                                                        )
                                                    )
                                                )
                                            )
                                        )
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

@IF /I "%is_delim_set%"=="%SETTING%" (
    @ECHO [ENVVAR_CLEANUP]: ERROR: Delim flag has been provided without any delimiter 1>&2
    @EXIT /B 1
)
@SET arg=
@SET is_mode_set=
@SET is_delim_set=
@SET is_fuzzy_set=

@REM if any of these variables are undefined set them to a default
@IF /I "%MODE%"=="" @SET "MODE=duplicate"
@IF /I "%DELIM%"=="" @SET "DELIM=:"

@REM check that $STR_TO_REMOVE is allocated correctly for the various $MODE
@IF /I "%MODE%"=="duplicate" (
    @IF /I NOT "%STR_TO_REMOVE_I%"=="-1" (
        @ECHO [ENVVAR_CLEANUP]: ERROR: Unknown/Invalid parameters for mode=%MODE% 1>&2
        @EXIT /B 1
    )
) ELSE (
    @IF /I "%STR_TO_REMOVE_I%"=="-1" (
        @ECHO [ENVVAR_CLEANUP]: ERROR: Missing arguments to remove for mode=%MODE% 1>&2
        @EXIT /B 1
    )
)

@REM ##########################################################################
@REM help dialog
@REM ##########################################################################

@REM ##########################################################################
@REM process for removal(s)
@REM ##########################################################################
@IF /I NOT "%VARIABLE%"=="" (
    @REM add DELIM to the beginning and end to simplify the matching process
    @REM but only if the delim hasn't already been added
    @IF /I "%VARIABLE:~0,1%"=="%DELIM%" (
        @SET "RM_PRE_DELIM=%FALSE%"
    ) ELSE (
        @SET "RM_PRE_DELIM=%TRUE%"
        @SET "VARIABLE=%DELIM%%VARIABLE%"
    )

    @IF /I "%VARIABLE:~-1%"=="%DELIM%" (
        @SET "RM_POST_DELIM=%FALSE%"
    ) ELSE (
        @SET "RM_POST_DELIM=%TRUE%"
        @SET "VARIABLE=%VARIABLE%%DELIM%"
    )

    @IF /I "%MODE%"=="duplicate" (
        @SET "old_VARIABLE=!VARIABLE!"
        @SET "VARIABLE=%DELIM%"

        @CALL :strlen MAX_ITER "!old_VARIABLE!"
        @CALL :strlen NUM_NONDELIMS "!old_VARIABLE:%DELIM%=!"
        @SET /A "MAX_ITER-=!NUM_NONDELIMS!"
        @SET /A "MAX_ITER-=1"

        @REM iterate over all phrases split by delim
        @FOR /L %%b IN (1,1,!MAX_ITER!) DO @(
            @REM chop off the first phrase available
            @FOR /F "tokens=1,* delims=%DELIM%" %%c IN ("!old_VARIABLE!") DO @(
                @SET "x=%%c"
                @SET "old_VARIABLE=%%d"
            )

            @SET "FROM=%DELIM%!x!%DELIM%"

            @FOR /F "delims=" %%c IN ("!FROM!") DO @SET "TMP=!VARIABLE:%%c=%DELIM%!"

            @REM if removing the current phrase from the %VARIABLE% didn't change
            @REM anything that means that it doesn't exist yet in the new unique
            @REM list, consequently append the value
            @IF /I "!TMP!"=="!VARIABLE!" @SET "VARIABLE=!VARIABLE!!x!%DELIM%"
        )
    ) ELSE (
        @SET "old_VARIABLE=!VARIABLE!"
        @SET "VARIABLE=%DELIM%"

        @CALL :strlen MAX_ITER "!old_VARIABLE!"
        @CALL :strlen NUM_NONDELIMS "!old_VARIABLE:%DELIM%=!"
        @SET /A "MAX_ITER-=!NUM_NONDELIMS!"
        @SET /A "MAX_ITER-=1"

        @REM iterate over all phrases split by delim
        @FOR /L %%b IN (1,1,!MAX_ITER!) DO @(
            @REM chop off the first phrase available
            @FOR /F "tokens=1,* delims=%DELIM%" %%c IN ("!old_VARIABLE!") DO @(
                @SET "x=%%c"
                @SET "old_VARIABLE=%%d"
            )

            @SET "MATCH=-1"
            @SET "FUZZY_MATCH=-1"
            @FOR /L %%i IN (0,1,!STR_TO_REMOVE_I!) DO @(
                @IF /I NOT "!STR_TO_REMOVE[%%i]!"=="" (
                    @REM check for an exact match
                    @IF /I "!STR_TO_REMOVE[%%i]!"=="!x!" (
                        @SET "MATCH=%%i"
                    ) ELSE (
                        @REM check for a fuzzy match (if applicable)
                        @IF /I "%FUZZY%"=="%TRUE%" (
                            @FOR /F "delims=" %%c IN ("!STR_TO_REMOVE[%%i]!") DO @SET "TMP=!x:%%c=!"
                            @IF /I NOT "!TMP!"=="!x!" (
                                @SET "FUZZY_MATCH=%%i"
                            )
                        )
                    )
                )
            )

            @IF /I "!MATCH!"=="-1" (
                @IF /I "!FUZZY_MATCH!"=="-1" (
                    @SET "VARIABLE=!VARIABLE!!x!%DELIM%"
                )
            ) ELSE (
                @IF /I "%MODE%"=="remove" (
                    @IF /I NOT "!MATCH!"=="-1" (
                        @SET STR_TO_REMOVE[!MATCH!]=
                    ) ELSE (
                        @SET STR_TO_REMOVE[!FUZZY_MATCH!]=
                    )
                )
            )
        )
    )

    @REM trim off the first and last DELIM that was added at the start
    @IF /I "!RM_PRE_DELIM!"=="%TRUE%"  @SET "VARIABLE=!VARIABLE:~1!"
    @IF /I "!RM_POST_DELIM!"=="%TRUE%" @SET "VARIABLE=!VARIABLE:~0,-1!"
)

@ECHO !VARIABLE!

@GOTO:eof

@REM ##########################################################################
@REM subroutine: strlen
@REM
@REM works to first detect the last index in the string and then
@REM converts that index to the length by adding 1
@REM ##########################################################################
:strlen <resultVar> <stringVar>
@(
    @SETLOCAL EnableDelayedExpansion
    @SET "string=%~2"
    @SET "len=0"
    @IF /I NOT "!string!"=="" (
        @REM find last valid index
        @FOR %%p IN (4096 2048 1024 512 256 128 64 32 16 8 4 2 1) DO @(
            @IF /I NOT "!string:~%%p,1!"=="" (
                @SET /A "len+=%%p"
                @SET "string=!string:~%%p!"
            )
        )

        @REM convert index to length
        @SET /A "len+=1"
    )
)
@(
    @ENDLOCAL
    @SET "%~1=%len%"
    @EXIT /B
)
