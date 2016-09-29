@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # #                                                               # #
@REM # # ACTIVATE FOR WINDOWS CMD.EXE                                  # #
@REM # #                                                               # #
@REM # # @ symbols in this file indicate that output should not be     # #
@REM # # printed setting it this way allows us to not touch the user's # #
@REM # # echo setting                                                  # #
@REM # #                                                               # #
@REM # # this file is also indented using TABS instead of SPACES to    # #
@REM # # avoid very odd syntax errors                                  # #
@REM # #                                                               # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

@REM entering a LOCAL scope, this effectively means that we do not
@REM need to explicitly unset anything but we do need to explicitly
@REM declare variables that need to be preserved
@SETLOCAL EnableDelayedExpansion

@REM #####################################################################
@REM # DEFINE BASIC VARS                                                 #
@SET "TRUE=1"
@SET "FALSE=0"
@SET "WHAT_SHELL_AM_I=cmd.exe"

@REM # note whether or not the CONDA_* variables are exported			 #
@REM # if so we need to preserve that status 							 #
@SET "IS_ENV_CONDA_HELP=%FALSE%"
@SET "IS_ENV_CONDA_VERBOSE=%FALSE%"
@SET "IS_ENV_CONDA_ENVNAME=%FALSE%"
@IF /I NOT "%CONDA_HELP%"=="" (
	@SET "IS_ENV_CONDA_HELP=%TRUE%"
)
@IF /I NOT "%CONDA_VERBOSE%"=="" (
	@SET "IS_ENV_CONDA_VERBOSE=%TRUE%"
)
@IF /I NOT "%CONDA_ENVNAME%"=="" (
	@SET "IS_ENV_CONDA_ENVNAME=%TRUE%"
)

@REM # inherit whatever the user set                                     #
@IF /I "%CONDA_HELP%"=="" (
	@SET "CONDA_HELP=%FALSE%"
) ELSE (
	@IF /I "%CONDA_HELP%"=="%FALSE%" (
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
					@IF /I "%CONDA_HELP%"=="%TRUE%" (
						@SET "CONDA_HELP=%TRUE%"
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
	)
)
@SET UNKNOWN=
@IF /I "%CONDA_VERBOSE%"=="" (
	@SET "CONDA_VERBOSE=%FALSE%"
) ELSE (
	@IF /I "%CONDA_VERBOSE%"=="%FALSE%" (
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
					@IF /I "%CONDA_VERBOSE%"=="%TRUE%" (
						@SET "CONDA_VERBOSE=%TRUE%"
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
	)
)
@IF /I "%CONDA_ENVNAME%"=="" (
	@SET CONDA_ENVNAME=
)

@REM # at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and             #
@REM # CONDA_ENVNAME are defined and do not need to be checked for       #
@REM # unbounded again                                                   #
@REM # END DEFINE BASIC VARS                                             #
@REM #####################################################################

@REM #####################################################################
@REM # PARSE COMMAND LINE                                                #
@SET "is_envname_set=%FALSE%"
:while_argparse_start
	@SET "arg=%~1"

	@REM check if variable is blank, if so stop parsing
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
										@REM check if variable is blank,
										@REM append unknown accordingly
										@IF /I "%UNKNOWN%"=="" (
											@SET "UNKNOWN=%arg%"
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

@REM # if any of these variables are undefined [i.e. unbounded] set them #
@REM # to a default                                                      #
@IF /I "%CONDA_HELP%"==""    @SET "CONDA_HELP=%FALSE%"
@IF /I "%CONDA_VERBOSE%"=="" @SET "CONDA_VERBOSE=%FALSE%"
@IF /I "%CONDA_ENVNAME%"=="" @SET "CONDA_ENVNAME=root"
@REM # END PARSE COMMAND LINE                                            #
@REM #####################################################################

@REM #####################################################################
@REM # HELP DIALOG                                                       #
@IF /I "%CONDA_HELP%"=="%TRUE%" (
	@CALL "conda" "..activate" "%WHAT_SHELL_AM_I%" "-h" "%UNKNOWN%"

	@ENDLOCAL && (
		@IF /I "%IS_ENV_CONDA_ENVNAME%"=="%TRUE%" (
			@SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
		)
		@IF /I "%IS_ENV_CONDA_HELP%"=="%TRUE%" (
			@SET "CONDA_HELP=%CONDA_HELP%"
		)
		@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%TRUE%" (
			@SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
		)
		@REM check if UNKNOWN is blank, error accordingly
		@IF /I NOT "%UNKNOWN%"=="" (
			@EXIT /B 1
		) ELSE (
			@EXIT /B 0
		)
	)
)
@REM # END HELP DIALOG                                                   #
@REM #####################################################################

@REM #####################################################################
@REM # CHECK ENV AND DEACTIVATE OLD ENV                                  #
@CALL "conda" "..checkenv" "%WHAT_SHELL_AM_I%" "%CONDA_ENVNAME%"
@IF errorlevel 1 (
	@ENDLOCAL && (
		@IF /I "%IS_ENV_CONDA_ENVNAME%"=="%TRUE%" (
			@SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
		)
		@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%TRUE%" (
			@SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
		)
		@IF /I "%IS_ENV_CONDA_HELP%"=="%TRUE%" (
			@SET "CONDA_HELP=%CONDA_HELP%"
		)
		@EXIT /B 1
	)
)

@REM # store remaining values that may get cleared by deactivate         #
@SET "_CONDA_WHAT_SHELL_AM_I=%WHAT_SHELL_AM_I%"
@SET "_CONDA_VERBOSE=%CONDA_VERBOSE%"
@SET "_IS_ENV_CONDA_VERBOSE=%IS_ENV_CONDA_VERBOSE%"

@REM # ensure we deactivate any scripts from the old env                 #
@CALL "deactivate.bat"
@IF NOT errorlevel 0 (
	@ENDLOCAL && (
		@IF /I "%IS_ENV_CONDA_ENVNAME%"=="1" (
			@SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
		)
		@IF /I "%_IS_ENV_CONDA_VERBOSE%"=="1" (
			@SET "CONDA_VERBOSE=%_CONDA_VERBOSE%"
		)
		@IF /I "%IS_ENV_CONDA_HELP%"=="1" (
			@SET "CONDA_HELP=%CONDA_HELP%"
		)
		@EXIT /B 1
	)
)

@REM # restore boolean                                                   #
@SET "TRUE=1"
@SET "FALSE=0"

@REM # restore values                                                    #
@SET "IS_ENV_CONDA_VERBOSE=%_IS_ENV_CONDA_VERBOSE%"
@SET "CONDA_VERBOSE=%_CONDA_VERBOSE%"
@SET "WHAT_SHELL_AM_I=%_CONDA_WHAT_SHELL_AM_I%"

@FOR /F "delims=" %%i IN ('@CALL "conda" "..activate" "%WHAT_SHELL_AM_I%" "%CONDA_ENVNAME%"') DO @SET "_CONDA_BIN=%%i"
@IF NOT errorlevel 0 (
	@ENDLOCAL && (
		@IF /I "%IS_ENV_CONDA_ENVNAME%"=="%TRUE%" (
			@SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
		)
		@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%TRUE%" (
			@SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
		)
		@IF /I "%IS_ENV_CONDA_HELP%"=="%TRUE%" (
			@SET "CONDA_HELP=%CONDA_HELP%"
		)
		@EXIT /B 1
	)
)
@REM # END CHECK ENV AND DEACTIVATE OLD ENV                              #
@REM #####################################################################

@REM #####################################################################
@REM # PATH                                                              #
@REM # update path with the new conda environment                        #
@SET "PATH=%_CONDA_BIN%;%PATH%"
@REM # END PATH                                                          #
@REM #####################################################################

@REM #####################################################################
@REM # CONDA_PREFIX                                                      #
@REM always the full path to the activated environment
@REM is not set when no environment is active
@FOR /F "delims=;" %%i IN ("%_CONDA_BIN%") DO @SET "CONDA_PREFIX=%%i"
@REM # END CONDA_PREFIX                                                  #
@REM #####################################################################

@REM #####################################################################
@REM # CONDA_DEFAULT_ENV                                                 #
@REM # the shortest representation of how conda recognizes your env      #
@REM # can be an env name, or a full path [if the string contains \ it's #
@REM # a path]                                                           #
@IF /I NOT "%CONDA_ENVNAME:\=%"=="%CONDA_ENVNAME%" (
	@FOR /F "delims=" %%i IN ("%CONDA_ENVNAME%") DO @SET "d=%%~dpi"
	@FOR /F "delims=" %%i IN ("%CONDA_ENVNAME%") DO @SET "f=%%~ni"
	@SET "CONDA_DEFAULT_ENV=!d!!f!"
) ELSE (
	@SET "CONDA_DEFAULT_ENV=%CONDA_ENVNAME%"
)
@REM # END CONDA_DEFAULT_ENV                                             #
@REM #####################################################################

@REM #####################################################################
@REM # PROMPT & CONDA_PS1_BACKUP                                         #
@REM # export PROMPT to restore upon deactivation                        #
@REM # customize the PROMPT to show what environment has been activated  #
@FOR /F "delims=" %%i IN ('@CALL "conda" "..changeps1"') DO @SET "_CONDA_CHANGEPS1=%%i"
@IF /I "!_CONDA_CHANGEPS1!"=="1" @IF /I NOT "%PROMPT%"=="" (
	@SET "CONDA_PS1_BACKUP=%PROMPT%"
	@SET "PROMPT=(!CONDA_DEFAULT_ENV!) %PROMPT%"
)
@REM # END PROMPT & CONDA_PS1_BACKUP                                     #
@REM #####################################################################

@REM #####################################################################
@REM # LOAD POST-ACTIVATE SCRIPTS & ENDLOCAL SCOPE                       #
@REM # create %_CONDA_DIR% path before exiting EnableDelayedExpansion    #
@REM # scope                                                             #
@SET "_CONDA_DIR=%CONDA_PREFIX%\etc\conda\activate.d"
@ENDLOCAL && (
	@REM load post-activate scripts
	@REM scripts found in %CONDA_PREFIX%\etc\conda\activate.d
	@IF EXIST "%_CONDA_DIR%" (
		@PUSHD "%_CONDA_DIR%"
		@FOR %%f IN (*.bat) DO @(
			@IF "%CONDA_VERBOSE%"=="%TRUE%" (
				@ECHO [ACTIVATE]: Sourcing %_CONDA_DIR%\%%f.
			)
			@CALL "%%f"
		)
		@POPD
	)

	@SET "PATH=%PATH%"
	@SET "PROMPT=%PROMPT%"

	@SET "CONDA_PREFIX=%CONDA_PREFIX%"
	@SET "CONDA_DEFAULT_ENV=%CONDA_DEFAULT_ENV%"
	@SET "CONDA_PS1_BACKUP=%CONDA_PS1_BACKUP%"

	@IF /I "%IS_ENV_CONDA_ENVNAME%"=="%TRUE%" (
		@SET "CONDA_ENVNAME=%CONDA_ENVNAME%"
	)
	@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%TRUE%" (
		@SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
	)
	@IF /I "%IS_ENV_CONDA_HELP%"=="%TRUE%" (
		@SET "CONDA_HELP=%CONDA_HELP%"
	)

	@REM #################################################################
	@REM # REHASH                                                        #
	@REM # no rehash for CMD.EXE                                         #
	@REM # END REHASH                                                    #
	@REM #################################################################

	@EXIT /B 0
)
@REM # END LOAD POST-ACTIVATE SCRIPTS & ENDLOCAL SCOPE                   #
@REM #####################################################################
