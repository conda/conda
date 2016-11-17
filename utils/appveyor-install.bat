@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # #                                                               # #
@REM # # APPVEYOR INSTALL                                              # #
@REM # #                                                               # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

@REM entering a LOCAL scope, this effectively means that we do not
@REM need to explicitly unset anything but we do need to explicitly
@REM declare variables that need to be preserved
@SETLOCAL EnableDelayedExpansion

@REM #####################################################################
@REM # MAIN FUNCTION                                                     #
@ECHO "START INSTALLING"

@REM # set globals                                                       #
@SET "HOME=%HOMEDRIVE%%HOMEPATH%"
@SET "MINICONDA_URL=https://repo.continuum.io/miniconda"
@SET "CYGWIN_BIN=C:\cygwin64\bin"
@SET "MINGW_BIN=C:\MinGW\msys\1.0\bin"
@SET "MSYS2_BIN=C:\msys64\usr\bin"

@REM # show basic environment details                                    #
@WHERE python
@SET

@REM # remove any stray CONDARC                                          #
@IF EXIST "!HOME!/.condarc" (
    @DEL "!HOME!/.condarc"
)

@REM # perform the appropriate install                                   #
@CALL :miniconda_install
@CALL :test_extras

@ECHO "DONE INSTALLING"
@ENDLOCAL && (
    @SET "PATH=%PATH%"
)
@GOTO :EOF
@REM # END MAIN FUNCTION                                                 #
@REM #####################################################################

@REM #####################################################################
@REM # HELPER FUNCTIONS                                                  #
:test_extras (
    @ECHO "TEST EXTRAS"

    @WHERE conda
    @REM # this causes issues with Miniconda3 4.0.5
    @REM # python -m conda info
    @REM # this does not cause issues with Miniconda3 4.0.5
    @CALL conda info

    @REM # install and verify pip
    @CALL conda install -y -q pip
    @WHERE pip

    @REM # verify python
    @WHERE python

    @REM # disable automatic updates
    @CALL conda config --set auto_update_conda false
    @CALL conda config --set always_yes yes
    @CALL conda update conda

    @REM # install/upgrade basic dependencies
    @CALL python -m pip install -U pycosat pycrypto
    @CALL conda install -q psutil ruamel_yaml requests
    @IF /I "%PYTHON_VERSION:~0,2%"=="2." (
        @CALL python -m pip install -U enum34 futures
    )

    @REM # install/upgrade unittest dependencies
    @CALL python -m pip install -U mock pytest pytest-cov pytest-timeout radon
    @CALL python -m pip install -U responses anaconda-client nbformat

    @REM # make sure all of the desired shells exist
    @IF EXIST "!CYGWIN_BIN!" (
        @REM # install other Cygwin shells
    )
    @IF EXIST "!MINGW_BIN!" (
        @REM # install other MinGW shells
    )
    @IF EXIST "!MSYS2_BIN!" (
        @REM # install other MSYS2 shells
        @CALL "!MSYS2_BIN!\bash.exe" -c 'export PATH="/usr/bin:$PATH" ; pacman -Sy --noconfirm dash zsh ksh csh tcsh'
    )

    @ECHO "END TEST EXTRAS"
)
@(
    @ENDLOCAL
    @EXIT /B
)


@REM # this install shares similarities to Travis CI installation's       #
@REM # python_install and miniconda_install functions                     #
:miniconda_install (
    @ECHO "MINICONDA INSTALL"

    @REM # get, install, and verify miniconda
    @IF NOT EXIST "!HOME!\miniconda" (
        @IF NOT EXIST "!HOME!\miniconda_installer.exe" (
            @REM # build download url
            @SET "filename=x86_64"
            @IF /I "%PYTHON_ARCH%"=="32" (
                @SET "filename=x86"
            )
            @IF /I "%PYTHON_VERSION:~0,2%"=="2." (
                @SET "filename=Miniconda2-latest-Windows-!filename!.exe"
            ) ELSE (
                @IF /I "%PYTHON_VERSION:~0,2%"=="3." (
                    @SET "filename=Miniconda3-latest-Windows-!filename!.exe"
                ) ELSE (
                    @SET "filename=Miniconda-latest-Windows-!filename!.exe"
                )
            )

            @CALL "powershell.exe" ".\utils\appveyor-downloader.ps1" "!MINICONDA_URL!/!filename!" "!HOME!\miniconda_installer.exe"
        )

        @REM # run install
        @CALL !HOME!\miniconda_installer.exe /S /D=%PYTHON%
    )
    @REM # check for success
    @IF NOT EXIST "%PYTHON%" (
        @ECHO "MINICONDA INSTALL FAILED"
        @MORE "%PYTHON%.log"
        @EXIT /B 1
    )

    @REM update PATH
    @SET "ANACONDA_PATH=%PYTHON%"
    @REM @SET "ANACONDA_PATH=!ANACONDA_PATH!;%PYTHON%\Library\mingw-64\bin"
    @SET "ANACONDA_PATH=!ANACONDA_PATH!;%PYTHON%\Library\usr\bin"
    @SET "ANACONDA_PATH=!ANACONDA_PATH!;%PYTHON%\Library\bin"
    @SET "ANACONDA_PATH=!ANACONDA_PATH!;%PYTHON%\Scripts"

    @REM remove duplicates from the %PATH%
    @REM Windows in general does poorly with long PATHs so just as a sanity
    @REM check remove any duplicates
    @FOR /F "delims=" %%i IN ('@CALL "./shell/envvar_cleanup.bat" "!ANACONDA_PATH!;%PATH%" /delim=";" /d') DO @SET "PATH=%%i"

    @ECHO "END MINICONDA INSTALL"
)
@(
    @ENDLOCAL
    @EXIT /B
)
@REM # END HELPER FUNCTIONS                                              #
@REM #####################################################################

@REM # - conda install -q python=%PYTHON_VERSION%
@REM # - conda install -q pyflakes
@REM # - conda install -q git menuinst
@REM # - pip install flake8
