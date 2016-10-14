# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # DEACTIVATE FOR WINDOWS POWERSHELL.EXE                               # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# DEFINE BASIC VARS                                                       #
# powershell has boolean type $TRUE and $FALSE
$WHAT_SHELL_AM_I="powershell.exe"

# note whether or not the CONDA_* variables are exported, if so we need   #
# to preserve that status                                                 #
$IS_ENV_CONDA_HELP="${FALSE}"
$IS_ENV_CONDA_VERBOSE="${FALSE}"
if ( (Get-ChildItem env:).Name | Select-String -Pattern CONDA_HELP ) {
    $IS_ENV_CONDA_HELP="${TRUE}"
    $CONDA_HELP="${env:CONDA_HELP}"
}
if ( (Get-Variable -Scope Global).Name | Select-String -Pattern CONDA_HELP ) {
    $_CONDA_HELP="${CONDA_HELP}"
    Remove-Variable -Scope Global CONDA_HELP
    if ( "${IS_ENV_CONDA_HELP}" -eq "${FALSE}" ) { $CONDA_HELP="${_CONDA_HELP}" }
    Remove-Variable _CONDA_HELP
}
if ( (Get-ChildItem env:).Name | Select-String -Pattern CONDA_VERBOSE ) {
    $IS_ENV_CONDA_VERBOSE="${TRUE}"
    $CONDA_VERBOSE="${env:CONDA_VERBOSE}"
}
if ( (Get-Variable -Scope Global).Name | Select-String -Pattern CONDA_VERBOSE ) {
    $_CONDA_VERBOSE="${CONDA_VERBOSE}"
    Remove-Variable -Scope Global CONDA_VERBOSE
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${FALSE}" ) { $CONDA_VERBOSE="${_CONDA_VERBOSE}" }
    Remove-Variable _CONDA_VERBOSE
}

# inherit whatever the user set                                           #
# this is important for us to match the logic of the unix codes where     #
# exported variables remain as part of the user's environment while       #
# normal variables get cleared, here that means variables stored as part  #
# of $env: are left as is, while those stored in the global scope are     #
# cleared                                                                 #
if ( "${CONDA_HELP}" -eq "" -or "${CONDA_HELP}" -eq "${FALSE}" -or "${CONDA_HELP}" -eq "0" -or "${CONDA_HELP}" -eq "false" -or "${CONDA_HELP}" -eq "FALSE" -or "${CONDA_HELP}" -eq "False" ) {
    $CONDA_HELP="${FALSE}"
} elseif ( "${CONDA_HELP}" -eq "${TRUE}" -or "${CONDA_HELP}" -eq "1" -or "${CONDA_HELP}" -eq "true" -or "${CONDA_HELP}" -eq "TRUE" -or "${CONDA_HELP}" -eq "True" ) {
    $CONDA_HELP="${TRUE}"
}
$UNKNOWN=""
if ( "${CONDA_VERBOSE}" -eq "" -or "${CONDA_VERBOSE}" -eq "${FALSE}" -or "${CONDA_VERBOSE}" -eq "0" -or "${CONDA_VERBOSE}" -eq "false" -or "${CONDA_VERBOSE}" -eq "FALSE" -or "${CONDA_VERBOSE}" -eq "False" ) {
    $CONDA_VERBOSE="${FALSE}"
} elseif ( "${CONDA_VERBOSE}" -eq "${TRUE}" -or "${CONDA_VERBOSE}" -eq "1" -or "${CONDA_VERBOSE}" -eq "true" -or "${CONDA_VERBOSE}" -eq "TRUE" -or "${CONDA_VERBOSE}" -eq "True" ) {
    $CONDA_VERBOSE="${TRUE}"
}

# at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and CONDA_ENVNAME are #
# defined and do not need to be checked for unbounded again               #
# END DEFINE BASIC VARS                                                   #
###########################################################################

###########################################################################
# PARSE COMMAND LINE                                                      #
$num=0
while ( "${num}" -ne -1 ) {
    $arg=$args[$num]
    $num=${num} + 1

    echo "arg is this |$arg|"

    # check if variable is blank, if so stop parsing
    if ( "${arg}" -eq "" ) {
        $num=-1
    } else {
        switch -r ("${arg}") {
            "^(-h|--help)$" {
                $CONDA_HELP="${TRUE}"
                break
            }
            "^(-v|--verbose)$" {
                $CONDA_VERBOSE="${TRUE}"
                break
            }
            default {
                # check if variable is blank, append unknown accordingly
                if ( "${UNKNOWN}" -eq "" ) {
                    $UNKNOWN="${arg}"
                } else {
                    $UNKNOWN="${UNKNOWN} ${arg}"
                }
                $CONDA_HELP="${TRUE}"
                break
            }
        }
    }
}
Remove-Variable num
Remove-Variable arg

# if any of these variables are undefined set them to a default           #
if ( "${CONDA_HELP}" -eq "" ) { $CONDA_HELP="${FALSE}" }
if ( "${CONDA_VERBOSE}" -eq "" ) { $CONDA_VERBOSE="${FALSE}" }
# END PARSE COMMAND LINE                                                  #
###########################################################################

###########################################################################
# HELP DIALOG                                                             #
if ( "${CONDA_HELP}" -eq "${TRUE}" ) {
    conda "..deactivate" "${WHAT_SHELL_AM_I}" "-h" ${UNKNOWN}

    Remove-Variable WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_HELP}" -eq "${TRUE}" ) { $env:CONDA_HELP="${CONDA_HELP}" }
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
    Remove-Variable CONDA_HELP
    Remove-Variable CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_HELP
    Remove-Variable IS_ENV_CONDA_VERBOSE
    # check if UNKNOWN is blank, error accordingly
    if ( "${UNKNOWN}" -ne "" ) {
        Remove-Variable UNKNOWN
        exit 1
    } else {
        Remove-Variable UNKNOWN
        exit 0
    }
}
Remove-Variable WHAT_SHELL_AM_I
if ( "${IS_ENV_CONDA_HELP}" -eq "${TRUE}" ) { $env:CONDA_HELP="${CONDA_HELP}" }
Remove-Variable CONDA_HELP
Remove-Variable IS_ENV_CONDA_HELP
Remove-Variable UNKNOWN
# END HELP DIALOG                                                         #
###########################################################################

###########################################################################
# CHECK IF CAN DEACTIVATE                                                 #
if ( -not ((Get-ChildItem env:).Name | Select-String -pattern CONDA_PREFIX) -or ${env:CONDA_PREFIX} -eq "" ) {
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
    Remove-Variable CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_VERBOSE
    exit 0
}
# END CHECK IF CAN DEACTIVATE                                             #
###########################################################################

###########################################################################
# RESTORE PATH                                                            #
# remove only first instance of %CONDA_PREFIX% from %PATH%, since         #
# this is Windows there will be several paths that need to be             #
# removed but they will all start with the same %CONDA_PREFIX%,           #
# consequently we will use fuzzy matching [/f] to get all of the          #
# relevant removals                                                       #
#                                                                         #
# replace ; with ? before calling batch program since powershell to batch #
# converts ; to linebreaks without explicit escaping \;                   #
$env:Path=(envvar_cleanup.bat ${env:PATH}.replace(";","?") --delim="?" -u -f "${env:CONDA_PREFIX}").replace("?",";")
if ( $lastexitcode -ne 0 ) {
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
    Remove-Variable CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_VERBOSE
    exit 1
}
# END RESTORE PATH                                                        #
###########################################################################

###########################################################################
# REMOVE CONDA_PREFIX                                                     #
# set $_CONDA_DIR for post-deactivate loading                             #
$_CONDA_DIR="${env:CONDA_PREFIX}\etc\conda\deactivate.d"
$env:CONDA_PREFIX=''
# END REMOVE CONDA_PREFIX                                                 #
###########################################################################

###########################################################################
# REMOVE CONDA_DEFAULT_ENV                                                #
$env:CONDA_DEFAULT_ENV=''
# END REMOVE CONDA_DEFAULT_ENV                                            #
###########################################################################

###########################################################################
# RESTORE PS1 & REMOVE CONDA_PS1_BACKUP                                   #
if ( "${env:CONDA_PS1_BACKUP}" -ne "" -and (Get-Command Prompt).definition -ne "" ) {
    Set-Content function:\Prompt $env:CONDA_PS1_BACKUP
    $env:CONDA_PS1_BACKUP=''
}
# END RESTORE PS1 & REMOVE CONDA_PS1_BACKUP                               #
###########################################################################

###########################################################################
# LOAD POST-DEACTIVATE SCRIPTS                                            #
if ( Test-Path -PathType Container "${_CONDA_DIR}" ) {
    Get-ChildItem -Path "${_CONDA_DIR}" -Filter "*.ps1" | % {
        $f="$_"
        if ( "${CONDA_VERBOSE}" -eq "${TRUE}" ) {
            echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}\${f}."
        }
        . "${_CONDA_DIR}\${f}"
    }
}
Remove-Variable _CONDA_DIR
if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
Remove-Variable CONDA_VERBOSE
Remove-Variable IS_ENV_CONDA_VERBOSE
# END LOAD POST-DEACTIVATE SCRIPTS                                        #
###########################################################################

###########################################################################
# REHASH                                                                  #
# no rehash for POWERSHELL.EXE                                            #
# END REHASH                                                              #
###########################################################################

###########################################################################
# CLEANUP VARS FOR THIS SCOPE                                             #
exit 0
# END CLEANUP VARS FOR THIS SCOPE                                         #
###########################################################################
