@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
@REM # #                                                               # #
@REM # # CLEANUP DELIMITED STRING [TYPICALLY THE %PATH%]               # #
@REM # #                                                               # #
@REM # # usage: envvar_cleanup.bat "%ENV_VAR%"                         # #
@REM # #        [/d OR [/u OR /r OR /g] "STR_TO_REMOVE" ...]           # #
@REM # #        [/delim=DELIM]                                         # #
@REM # #        [/f]                                                   # #
@REM # #                                                               # #
@REM # # where:                                                        # #
@REM # #    "%ENV_VAR%"                 is the variable name to        # #
@REM # #                                cleanup                        # #
@REM # #    /d,-d                       remove duplicates              # #
@REM # #    /u,-u "STR_TO_REMOVE" ...   remove first UNIQUE match of   # #
@REM # #                                provided strings [with fuzzy   # #
@REM # #                                match, /f, this may remove     # #
@REM # #                                multiple elements]             # #
@REM # #    /r,-r "STR_TO_REMOVE" ...   remove first match of provided # #
@REM # #                                strings [even with fuzzy       # #
@REM # #                                match, /f, this will only      # #
@REM # #                                remove the first match]        # #
@REM # #    /g,-g "STR_TO_REMOVE" ...   remove all instances of        # #
@REM # #                                provided strings               # #
@REM # #    /delim=DELIM,--delim=DELIM  specify what the delimit       # #
@REM # #    /f,-f                       fuzzy matching in conjunction  # #
@REM # #                                with /u, /r, and /g [not       # #
@REM # #                                compatible with /d]            # #
@REM # #                                                               # #
@REM # # reference:                                                    # #
@REM # # http://stackoverflow.com/questions/5837418/                   # #
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
@SET "SETTING=2"
@SET VARIABLE=
@SET "MODE=duplicate"
@SET "DELIM=:"
@SET "FUZZY=%FALSE%"
@SET STR_TO_REMOVE=
@SET STR_TO_REMOVE_I=-1
@SET UNIQUE_MATCHES=
@SET UNIQUE_MATCHES_I=-1

@REM # at this point VARIABLE, MODE, DELIM, and STR_TO_REMOVE are        #
@REM # defined and do not need to be checked for unbounded again         #
@REM # END DEFINE BASIC VARS                                             #
@REM #####################################################################

@REM #####################################################################
@REM # PARSE COMMAND LINE                                                #
@SET "is_mode_set=%FALSE%"
@SET "is_delim_set=%FALSE%"
@SET "is_fuzzy_set=%FALSE%"
:while_argparse_start
	@SET "arg=%~1"

	@REM check if variable is blank, if so no need to check any further
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
				@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
				@EXIT /B 1
			)
		) ELSE (
			@IF /I "%arg%"=="-d" (
				@IF /I "%is_mode_set%"=="%FALSE%" (
					@SET "MODE=duplicate"
					@SET "is_mode_set=%TRUE%"
				) ELSE (
					@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
					@EXIT /B 1
				)
			) ELSE (
				@IF /I "%arg%"=="/u" (
					@IF /I "%is_mode_set%"=="%FALSE%" (
						@SET "MODE=unique"
						@SET "is_mode_set=%TRUE%"
					) ELSE (
						@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
						@EXIT /B 1
					)
				) ELSE (
					@IF /I "%arg%"=="-u" (
						@IF /I "%is_mode_set%"=="%FALSE%" (
							@SET "MODE=unique"
							@SET "is_mode_set=%TRUE%"
						) ELSE (
							@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
							@EXIT /B 1
						)
					) ELSE (
						@IF /I "%arg%"=="/r" (
							@IF /I "%is_mode_set%"=="%FALSE%" (
								@SET "MODE=remove"
								@SET "is_mode_set=%TRUE%"
							) ELSE (
								@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
								@EXIT /B 1
							)
						) ELSE (
							@IF /I "%arg%"=="-r" (
								@IF /I "%is_mode_set%"=="%FALSE%" (
									@SET "MODE=remove"
									@SET "is_mode_set=%TRUE%"
								) ELSE (
									@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
									@EXIT /B 1
								)
							) ELSE (
								@IF /I "%arg%"=="/g" (
									@IF /I "%is_mode_set%"=="%FALSE%" (
										@SET "MODE=global"
										@SET "is_mode_set=%TRUE%"
									) ELSE (
										@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
										@EXIT /B 1
									)
								) ELSE (
									@IF /I "%arg%"=="-g" (
										@IF /I "%is_mode_set%"=="%FALSE%" (
											@SET "MODE=global"
											@SET "is_mode_set=%TRUE%"
										) ELSE (
											@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once ["%arg%"] 1>&2
											@EXIT /B 1
										)
									) ELSE (
										@IF /I "%arg%"=="/f" (
											@IF /I "%is_fuzzy_set%"=="%FALSE%" (
												@SET "FUZZY=%TRUE%"
												@SET "is_fuzzy_set=%TRUE%"
											) ELSE (
												@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set fuzzy more than once ["%arg%"] 1>&2
												@EXIT /B 1
											)
										) ELSE (
											@IF /I "%arg%"=="-f" (
												@IF /I "%is_fuzzy_set%"=="%FALSE%" (
													@SET "FUZZY=%TRUE%"
													@SET "is_fuzzy_set=%TRUE%"
												) ELSE (
													@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set fuzzy more than once ["%arg%"] 1>&2
													@EXIT /B 1
												)
											) ELSE (
												@IF /I "%arg%"=="/delim" (
													@IF /I "%is_delim_set%"=="%FALSE%" (
														@SET "is_delim_set=%SETTING%"
													) ELSE (
														@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set delim more than once ["%arg%"] 1>&2
														@EXIT /B 1
													)
												) ELSE (
													@IF /I "%arg%"=="--delim" (
														@IF /I "%is_delim_set%"=="%FALSE%" (
															@SET "is_delim_set=%SETTING%"
														) ELSE (
															@ECHO [ENVVAR_CLEANUP]: ERROR: Cannot set delim more than once ["%arg%"] 1>&2
															@EXIT /B 1
														)
													) ELSE (
														@IF /I "%arg%"=="/*" (
															@ECHO [ENVVAR_CLEANUP]: ERROR: Unknown/Invalid flag/parameter ["%arg%"] 1>&2
														) ELSE (
															@IF /I "%arg%"=="-*" (
																@ECHO [ENVVAR_CLEANUP]: ERROR: Unknown/Invalid flag/parameter ["%arg%"] 1>&2
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
		)
	)

	@SHIFT
	@GOTO while_argparse_start
:while_argparse_end
@IF /I "%is_delim_set%"=="%SETTING%" (
	@ECHO [ENVVAR_CLEANUP]: ERROR: Delim flag has been provided without any delimiter
	@EXIT /B 1
)

@REM # if any of these variables are undefined set them to a default 	 #
@IF /I "%MODE%"=="" @SET "MODE=duplicate"
@IF /I "%DELIM%"=="" @SET "DELIM=:"

@REM # check that %STR_TO_REMOVE% is allocated correctly for the various #
@REM # %MODE%                                                            #
@IF /I "%MODE%"=="duplicate" (
	@IF /I NOT "%STR_TO_REMOVE_I%"=="-1" (
		@ECHO [ENVVAR_CLEANUP]: ERROR: Unknown/Invalid parameters for mode=%MODE%
		@EXIT /B 1
	)
) ELSE (
	@IF /I "%STR_TO_REMOVE_I%"=="-1" (
		@ECHO [ENVVAR_CLEANUP]: ERROR: Missing arguments to remove for mode=%MODE%
		@EXIT /B 1
	)
)
@REM # END PARSE COMMAND LINE                                            #
@REM #####################################################################

@REM #####################################################################
@REM # HELP DIALOG                                                       #
@REM # TODO
@REM # END HELP DIALOG                                                   #
@REM #####################################################################

@REM #####################################################################
@REM # PROCESS FOR REMOVAL[S]                                            #
@IF /I NOT "%VARIABLE%"=="" (
	@REM remove DELIM from the beginning and append DELIM to the end
	@REM remember if there was a delim at the beginning/end and mimic the
    @REM same pattern upon finish
	@IF /I "%VARIABLE:~0,1%"=="%DELIM%" (
		@SET "HAS_PRE_DELIM=%TRUE%"
		@SET "VARIABLE=%VARIABLE:~1%"
	) ELSE (
		@SET "HAS_PRE_DELIM=%FALSE%"
	)

	@IF /I "%VARIABLE:~-1%"=="%DELIM%" (
		@SET "HAS_POST_DELIM=%TRUE%"
	) ELSE (
		@SET "HAS_POST_DELIM=%FALSE%"
		@SET "VARIABLE=%VARIABLE%%DELIM%"
	)

	@SET "old_VARIABLE=!VARIABLE!"
	@SET "VARIABLE=%DELIM%"

	@CALL :strlen MAX_ITER "!old_VARIABLE!"
	@CALL :strlen NUM_NONDELIMS "!old_VARIABLE:%DELIM%=!"
	@SET /A "MAX_ITER-=!NUM_NONDELIMS!"

	@IF /I "%MODE%"=="duplicate" (
		@REM iterate over all phrases split by delim
		@FOR /L %%i IN (1,1,!MAX_ITER!) DO @(
			@REM chop off the first phrase available
			@FOR /F "tokens=1,* delims=%DELIM%" %%j IN ("!old_VARIABLE!") DO @(
				@SET "x=%%j"
				@SET "old_VARIABLE=%%k"
			)

			@SET "FROM=%DELIM%!x!%DELIM%"

			@FOR /F "delims=" %%j IN ("!FROM!") DO @SET "TMP=!VARIABLE:%%j=%DELIM%!"

			@REM if removing the current phrase from the %VARIABLE% didn't change
			@REM anything that means that it doesn't exist yet in the new unique
			@REM list, consequently append the value
			@IF /I "!TMP!"=="!VARIABLE!" @SET "VARIABLE=!VARIABLE!!x!%DELIM%"
		)
	) ELSE (
		@REM iterate over all phrases split by delim

		@FOR /L %%i IN (1,1,!MAX_ITER!) DO @(
			@REM chop off the first phrase available
			@FOR /F "tokens=1,* delims=%DELIM%" %%j IN ("!old_VARIABLE!") DO @(
				@SET "x=%%j"
				@SET "old_VARIABLE=%%k"
			)

			@SET "MATCH=-1"
			@SET "FUZZY_MATCH=-1"
			@FOR /L %%j IN (0,1,!STR_TO_REMOVE_I!) DO @(
				@IF /I NOT "!STR_TO_REMOVE[%%j]!"=="" (
					@REM check for an exact match
					@IF /I "!STR_TO_REMOVE[%%j]!"=="!x!" (
						@SET "MATCH=%%j"
					) ELSE (
						@REM check for a fuzzy match [if applicable]
						@IF /I "%FUZZY%"=="%TRUE%" (
							@FOR /F "delims=" %%k IN ("!STR_TO_REMOVE[%%j]!") DO @SET "TMP=!x:%%k=!"
							@IF /I NOT "!TMP!"=="!x!" (
								@SET "FUZZY_MATCH=%%j"
							)
						)
					)
				)
			)

			@SET "PRIOR_MATCH=-1"
			@FOR /L %%j IN (0,1,!UNIQUE_MATCHES_I!) DO @(
				@IF /I NOT "!UNIQUE_MATCHES[%%j]!"=="" (
					@REM check if we have matched this before
					@REM
                    @REM ensure we are checking against paths that have been "standardized"
                    @REM on some oddball systems paths with the wrong slash are still valid
                    @REM but may match incorrect as a unique match
                    @REM example:
                    @REM 	envvar_cleanup.bash "/prefix/path:/prefix\path" --delim=":" -u -f "/prefix"
                    @SET "unique_match_std=!UNIQUE_MATCHES[%%j]:/=|!"
                    @SET "unique_match_std=!unique_match_std:\=|!"
                    @SET "x_std=!x:/=|!"
                    @SET "x_std=!x_std:\=|!"
                    @IF /I "!unique_match_std!"=="!x_std!" (
						@SET "PRIOR_MATCH=%%j"
					)
				)
			)

			@SET "KEEPER=%FALSE%"
			@IF /I "!MATCH!"=="-1" @IF /I "!FUZZY_MATCH!"=="-1" (
				@SET "KEEPER=%TRUE%"
			)

			@IF /I "!KEEPER!"=="%TRUE%" (
				@SET "VARIABLE=!VARIABLE!!x!%DELIM%"
			) ELSE (
				@IF /I "%MODE%"=="unique" (
					@REM collect all matches
					@IF /I "!PRIOR_MATCH!"=="-1" (
						@REM this is a unique match
						@SET /A "UNIQUE_MATCHES_I+=1"
						@SET "UNIQUE_MATCHES[!UNIQUE_MATCHES_I!]=!x!"
					) ELSE (
						@REM this is a non-unique match
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
	)

	@REM trim off the first and last DELIM that was added at the start
	@CALL :strlen LENGTH "!VARIABLE!"
	@IF /I NOT "!LENGTH!"=="0" (
		@IF /I "!HAS_PRE_DELIM!"=="%TRUE%" (
			@IF /I NOT "!VARIABLE:~0,1!"=="%DELIM%" (
				@SET "VARIABLE=%DELIM%!VARIABLE!"
			)
		) ELSE (
			@IF /I "!VARIABLE:~0,1!"=="%DELIM%" (
				@SET "VARIABLE=!VARIABLE:~1!"
			)
		)
	)
	@CALL :strlen LENGTH "!VARIABLE!"
	@IF /I NOT "!LENGTH!"=="0" (
		@IF /I "!HAS_POST_DELIM!"=="%TRUE%" (
			@IF /I NOT "!VARIABLE:~-1!"=="%DELIM%" (
				@SET "VARIABLE=!VARIABLE!%DELIM%"
			)
		) ELSE (
			@IF /I "!VARIABLE:~-1!"=="%DELIM%" (
				@SET "VARIABLE=!VARIABLE:~0,-1!"
			)
		)
	)
)
@REM # END PROCESS FOR REMOVAL[S]                                        #
@REM #####################################################################

@REM #####################################################################
@REM # CLEANUP VARS FOR THIS SCOPE                                       #
@ECHO !VARIABLE!
@GOTO:eof
@REM # END CLEANUP VARS FOR THIS SCOPE                                   #
@REM #####################################################################

@REM #####################################################################
@REM # SUBROUTINE STRLEN                                                 #
@REM #                                                                   #
@REM # works to first detect the last index in the string and then       #
@REM # converts that index to the length by adding 1                     #
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
@REM # END SUBROUTINE STRLEN                                             #
@REM #####################################################################
