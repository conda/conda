@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # #                                                               # #
@REM # # APPVEYOR SCRIPT                                               # #
@REM # #                                                               # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

@REM entering a LOCAL scope, this effectively means that we do not
@REM need to explicitly unset anything but we do need to explicitly
@REM declare variables that need to be preserved
@SETLOCAL EnableDelayedExpansion

@REM #####################################################################
@REM # MAIN FUNCTION                                                     #
@ECHO "START SCRIPT"

@REM # set globals                                                       #
@SET "CYGWIN_BIN=C:\cygwin64\bin"
@SET "MINGW_BIN=C:\MinGW\msys\1.0\bin"
@SET "MSYS2_BIN=C:\msys64\usr\bin"

@REM # show basic environment details                                    #
@WHERE python
@SET

@REM remove duplicates from the %PATH%
@REM Windows in general does poorly with long PATHs so just as a sanity
@REM check remove any duplicates
@FOR /F "delims=" %%i IN ('@CALL "./shell/envvar_cleanup.bat" "%PATH%" /delim=";" /d') DO @SET "PATH=%%i"

@REM # perform the appropriate test setup                                #
@CALL :main_test

@ECHO "DONE SCRIPT"
@GOTO :EOF
@REM # END MAIN FUNCTION                                                 #
@REM #####################################################################

@REM #####################################################################
@REM # HELPER FUNCTIONS                                                  #
:main_test
@(
    @ECHO "MAIN TEST"

    @FOR /F "delims=" %%i IN ('@CALL python -c "import random as r; print(r.randint(0,4294967296))"') DO @SET "PYTHONHASHSEED=%%i"
    @ECHO "!PYTHONHASHSEED!"

    @REM # detect what shells are available to test with
    @REM # refer to conda.util.shells for appropriate syntaxes
    @SET shells=
    @WHERE /q "cmd.exe"               && @SET "shells=!shells! --shell=cmd.exe"
    @REM # POWERSHELL has a much more complex prompt than any of the     #
    @REM # other shells this means that we need to rework fundamental    #
    @REM # code before unittests are feasible                            #
    @REM @WHERE /q "powershell.exe"        && @SET "shells=!shells! --shell=powershell.exe"
    @REM # disable all special shell testing as they need more work      #
    @REM @IF EXIST "!CYGWIN_BIN!\bash.exe" [ @SET "shells=!shells! --shell=bash.cygwin"  ]
    @REM @IF EXIST "!MINGW_BIN!\bash.exe"  [ @SET "shells=!shells! --shell=bash.mingw"   ]
    @REM @IF EXIST "!MSYS2_BIN!\bash.exe"  [ @SET "shells=!shells! --shell=bash.msys"    ]
    @REM @IF EXIST "!MSYS2_BIN!\dash.exe"  [ @SET "shells=!shells! --shell=dash.msys"    ]
    @REM @IF EXIST "!MSYS2_BIN!\zsh.exe"   [ @SET "shells=!shells! --shell=zsh.msys"     ]
    @REM @IF EXIST "!MSYS2_BIN!\ksh.exe"   [ @SET "shells=!shells! --shell=ksh.msys"     ]
    @REM # CSH/TCSH has notorious issues with spaces in pathnames, since #
    @REM # the unittests explicitly test for that these tests simply     #
    @REM # cannot succeed                                                #
    @REM @IF EXIST "!MSYS2_BIN!\csh.exe"   [ @SET "shells=!shells! --shell=csh.msys"     ]
    @REM @IF EXIST "!MSYS2_BIN!\tcsh.exe"  [ @SET "shells=!shells! --shell=tcsh.msys"    ]
    @ECHO "TESTING ON SHELLS: !shells!"

    python -m pytest --cov conda --cov-report term-missing --cov-report xml !shells! -m "not installed" tests conda

    @REM # `develop` instead of `install` to avoid coverage issues of
    @REM # tracking two separate "codes"
    python setup.py --version
    python setup.py develop
    @WHERE conda
    python -m conda info

    python -m pytest --cov conda --cov-report xml --cov-report term-missing --cov-append !shells! -m "installed" tests

    @ECHO "END MAIN TEST"
)
@(
    @ENDLOCAL
    @EXIT /B
)
@REM # END HELPER FUNCTIONS                                              #
@REM #####################################################################
