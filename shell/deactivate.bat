@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # #                                                               # #
@REM # # DEACTIVATE FOR WINDOWS CMD.EXE                                # #
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
@IF /I NOT "%CONDA_HELP%"=="" (
	@SET "IS_ENV_CONDA_HELP=%TRUE%"
)
@IF /I NOT "%CONDA_VERBOSE%"=="" (
	@SET "IS_ENV_CONDA_VERBOSE=%TRUE%"
)

@REM # inherit whatever the user set                                     #
@IF /I "%CONDA_HELP%"=="" (
	@SET "CONDA_HELP=%FALSE%"
) ELSE (
	@IF /I "%CONDA_HELP%"=="%FASLE%" (
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

@REM # at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and             #
@REM # CONDA_ENVNAME are defined and do not need to be checked for       #
@REM # unbounded again                                                   #
@REM # END DEFINE BASIC VARS                                             #
@REM #####################################################################

@REM #####################################################################
@REM # PARSE COMMAND LINE                                                #
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

	@SHIFT
	@GOTO while_argparse_start
:while_argparse_end

@REM # if any of these variables are undefined [i.e. unbounded] set them #
@REM # to a default                                                      #
@IF /I "%CONDA_HELP%"==""    @SET "CONDA_HELP=%FALSE%"
@IF /I "%CONDA_VERBOSE%"=="" @SET "CONDA_VERBOSE=%FALSE%"
@REM # END PARSE COMMAND LINE                                            #
@REM #####################################################################

@REM #####################################################################
@REM # HELP DIALOG                                                       #
@IF /I "%CONDA_HELP%"=="%TRUE%" (
	@CALL "conda" "..deactivate" "%WHAT_SHELL_AM_I%" "-h" "%UNKNOWN%"

	@ENDLOCAL && (
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
@REM # CHECK IF CAN DEACTIVATE                                           #
@IF /I "%CONDA_PREFIX%"=="" (
	@ENDLOCAL && (
		@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%TRUE%" (
			@SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
		)
		@IF /I "%IS_ENV_CONDA_HELP%"=="%TRUE%" (
			@SET "CONDA_HELP=%CONDA_HELP%"
		)
		@EXIT /B 0
	)
)
@REM # END CHECK IF CAN DEACTIVATE                                       #
@REM #####################################################################

@REM #####################################################################
@REM # RESTORE PATH                                                      #
@REM # remove only first instance of %CONDA_PREFIX% from %PATH%, since   #
@REM # this is Windows there will be several paths that need to be       #
@REM # removed but they will all start with the same %CONDA_PREFIX%,     #
@REM # consequently we will use fuzzy matching [/f] to get all of the    #
@REM # relevant removals                                                 #
@FOR /F "delims=" %%i IN ('@CALL "envvar_cleanup.bat" "%PATH%" /delim=";" /u /f "%CONDA_PREFIX%"') DO @SET "PATH=%%i"
@IF NOT errorlevel 0 (
	@ENDLOCAL && (
		@IF /I "%IS_ENV_CONDA_VERBOSE%"=="%TRUE%" (
			@SET "CONDA_VERBOSE=%CONDA_VERBOSE%"
		)
		@IF /I "%IS_ENV_CONDA_HELP%"=="%TRUE%" (
			@SET "CONDA_HELP=%CONDA_HELP%"
		)
		@EXIT /B 1
	)
)
@REM # END RESTORE PATH                                                  #
@REM #####################################################################

@REM #####################################################################
@REM # RESTORE PROMPT                                                    #
@IF /I NOT "%CONDA_PS1_BACKUP%"=="" (
	@SET "PROMPT=%CONDA_PS1_BACKUP%"
)
@REM # END RESTORE PROMPT                                                #
@REM #####################################################################

@REM #####################################################################
@REM # LOAD POST-DEACTIVATE SCRIPTS & ENDLOCAL SCOPE                     #
@REM # create %_CONDA_DIR% path before exiting EnableDelayedExpansion    #
@REM # scope                                                             #
@SET "_CONDA_DIR=%CONDA_PREFIX%\etc\conda\deactivate.d"
@ENDLOCAL && (
	@REM load post-deactivate scripts
	@REM scripts found in %CONDA_PREFIX%\etc\conda\deactivate.d
	@IF EXIST "%_CONDA_DIR%" (
		@PUSHD "%_CONDA_DIR%"
		@FOR %%f IN (*.bat) DO @(
			@IF "%CONDA_VERBOSE%"=="%TRUE%" (
				@ECHO [DEACTIVATE]: Sourcing %_CONDA_DIR%\%%f.
			)
			@CALL "%%f"
		)
		@POPD
	)

	@SET "PATH=%PATH%"
	@SET "PROMPT=%PROMPT%"

	@REM remove CONDA_PREFIX, CONDA_DEFAULT_ENV, CONDA_PS1_BACKUP
	@SET CONDA_PREFIX=
	@SET CONDA_DEFAULT_ENV=
	@SET CONDA_PS1_BACKUP=

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
@REM # END LOAD POST-DEACTIVATE SCRIPTS & ENDLOCAL SCOPE                 #
@REM #####################################################################
