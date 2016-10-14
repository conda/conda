# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # ACTIVATE FOR WINDOWS POWERSHELL.EXE                                 # #
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
$IS_ENV_CONDA_ENVNAME="${FALSE}"
if ( (Get-ChildItem env:).Name | Select-String -Pattern CONDA_HELP ) {
    $IS_ENV_CONDA_HELP="${TRUE}"
    $CONDA_HELP="${env:CONDA_HELP}"
}
if ( (Get-Variable -Scope Global).Name | Select-String -Pattern CONDA_HELP ) {
    $_CONDA_HELP="${CONDA_HELP}"
    Remove-Variable -Scope Global CONDA_HELP
    $CONDA_HELP="${_CONDA_HELP}"
    Remove-Variable _CONDA_HELP
}
if ( (Get-ChildItem env:).Name | Select-String -Pattern CONDA_VERBOSE ) {
    $IS_ENV_CONDA_VERBOSE="${TRUE}"
    $CONDA_VERBOSE="${env:CONDA_VERBOSE}"
}
if ( (Get-Variable -Scope Global).Name | Select-String -Pattern CONDA_VERBOSE ) {
    $_CONDA_VERBOSE="${CONDA_VERBOSE}"
    Remove-Variable -Scope Global CONDA_VERBOSE
    $CONDA_VERBOSE="${_CONDA_VERBOSE}"
    Remove-Variable _CONDA_VERBOSE
}
if ( (Get-ChildItem env:).Name | Select-String -Pattern CONDA_ENVNAME ) {
    $IS_ENV_CONDA_ENVNAME="${TRUE}"
    $CONDA_ENVNAME="${env:CONDA_ENVNAME}"
}
if ( (Get-Variable -Scope Global).Name | Select-String -Pattern CONDA_ENVNAME ) {
    $_CONDA_ENVNAME="${CONDA_ENVNAME}"
    Remove-Variable -Scope Global CONDA_ENVNAME
    $CONDA_ENVNAME="${_CONDA_ENVNAME}"
    Remove-Variable _CONDA_ENVNAME
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
if ( "${CONDA_ENVNAME}" -eq "" ) {
    $CONDA_ENVNAME=""
}

# at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and CONDA_ENVNAME are #
# defined and do not need to be checked for unbounded again               #
# END DEFINE BASIC VARS                                                   #
###########################################################################

###########################################################################
# PARSE COMMAND LINE                                                      #
$num=0
$is_envname_set="${FALSE}"
while ( "${num}" -ne -1 ) {
    $arg=$args[$num]
    $num=${num} + 1

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
                if ( "${is_envname_set}" -eq "${FALSE}" ) {
                    $CONDA_ENVNAME="${arg}"
                    $is_envname_set="${TRUE}"
                } else {
                    # check if variable is blank, append unknown
                    # accordingly
                    if ( "${UNKNOWN}" -eq "" ) {
                        $UNKNOWN="${arg}"
                    } else {
                        $UNKNOWN="${UNKNOWN} ${arg}"
                    }
                    $CONDA_HELP="${TRUE}"
                }
                break
            }
        }
    }
}
Remove-Variable num
Remove-Variable arg
Remove-Variable is_envname_set

# if any of these variables are undefined set them to a default           #
if ( "${CONDA_HELP}" -eq "" ) { $CONDA_HELP="${FALSE}" }
if ( "${CONDA_VERBOSE}" -eq "" ) { $CONDA_VERBOSE="${FALSE}" }
if ( "${CONDA_ENVNAME}" -eq "" ) { $CONDA_ENVNAME="root" }
# END PARSE COMMAND LINE                                                  #
###########################################################################

###########################################################################
# HELP DIALOG                                                             #
if ( "${CONDA_HELP}" -eq "${TRUE}" ) {
    conda "..activate" "${WHAT_SHELL_AM_I}" "-h" ${UNKNOWN}

    Remove-Variable WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_ENVNAME}" -eq "${TRUE}" ) { $env:CONDA_ENVNAME="${CONDA_ENVNAME}" }
    if ( "${IS_ENV_CONDA_HELP}" -eq "${TRUE}" ) { $env:CONDA_HELP="${CONDA_HELP}" }
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
    Remove-Variable CONDA_ENVNAME
    Remove-Variable CONDA_HELP
    Remove-Variable CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_ENVNAME
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
if ( "${IS_ENV_CONDA_HELP}" -eq "${TRUE}" ) { $env:CONDA_HELP="${CONDA_HELP}" }
Remove-Variable CONDA_HELP
Remove-Variable IS_ENV_CONDA_HELP
Remove-Variable UNKNOWN
# END HELP DIALOG                                                         #
###########################################################################

###########################################################################
# CHECK ENV AND DEACTIVATE OLD ENV                                        #
conda "..checkenv" "${WHAT_SHELL_AM_I}" "${CONDA_ENVNAME}"
if ( $lastexitcode -ne 0 ) {
    Remove-Variable WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_ENVNAME}" -eq "${TRUE}" ) { $env:CONDA_ENVNAME="${CONDA_ENVNAME}" }
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
    Remove-Variable CONDA_ENVNAME
    Remove-Variable CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_ENVNAME
    Remove-Variable IS_ENV_CONDA_VERBOSE
    exit 1
}

# store remaining values that may get cleared by deactivate               #
$_CONDA_WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}"
$_CONDA_VERBOSE="${CONDA_VERBOSE}"
$_IS_ENV_CONDA_VERBOSE="${IS_ENV_CONDA_VERBOSE}"

# ensure we deactivate any scripts from the old env                       #
. (Get-Command deactivate.ps1).path
if ( $lastexitcode -ne 0 ) {
    Remove-Variable _CONDA_WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_ENVNAME}" -eq "${TRUE}" ) { $env:CONDA_ENVNAME="${CONDA_ENVNAME}" }
    Remove-Variable CONDA_ENVNAME
    Remove-Variable _CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_ENVNAME
    Remove-Variable _IS_ENV_CONDA_VERBOSE
    exit 1
}

# restore values                                                          #
$IS_ENV_CONDA_VERBOSE="${_IS_ENV_CONDA_VERBOSE}"
$CONDA_VERBOSE="${_CONDA_VERBOSE}"
$WHAT_SHELL_AM_I="${_CONDA_WHAT_SHELL_AM_I}"
Remove-Variable _IS_ENV_CONDA_VERBOSE
Remove-Variable _CONDA_VERBOSE
Remove-Variable _CONDA_WHAT_SHELL_AM_I

$_CONDA_BIN=conda "..activate" "${WHAT_SHELL_AM_I}" "${CONDA_ENVNAME}"
if ( $lastexitcode -ne 0 ) {
    Remove-Variable WHAT_SHELL_AM_I
    Remove-Variable _CONDA_BIN
    if ( "${IS_ENV_CONDA_ENVNAME}" -eq "${TRUE}" ) { $env:CONDA_ENVNAME="${CONDA_ENVNAME}" }
    if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
    Remove-Variable CONDA_ENVNAME
    Remove-Variable CONDA_VERBOSE
    Remove-Variable IS_ENV_CONDA_ENVNAME
    Remove-Variable IS_ENV_CONDA_VERBOSE
    exit 1
}
Remove-Variable WHAT_SHELL_AM_I
# END CHECK ENV AND DEACTIVATE OLD ENV                                    #
###########################################################################

###########################################################################
# PATH                                                                    #
# update path with the new conda environment                              #
$env:PATH="${_CONDA_BIN};${env:PATH}"
# END PATH                                                                #
###########################################################################

###########################################################################
# CONDA_PREFIX                                                            #
# always the full path to the activated environment                       #
# is not set when no environment is active                                #
$env:CONDA_PREFIX=Split-Path -Path ${_CONDA_BIN}.split(';')[-1]
Remove-Variable _CONDA_BIN
# END CONDA_PREFIX                                                        #
###########################################################################

###########################################################################
# CONDA_DEFAULT_ENV                                                       #
# the shortest representation of how conda recognizes your env            #
# can be an env name, or a full path (if the string contains \ it's a     #
# path)                                                                   #
if ( ${CONDA_ENVNAME} -match '\\' ) {
    # $d=Split-Path -Path "${CONDA_ENVNAME}"
    # $d=Resolve-Path "${d}"
    # $f=Split-Path -Leaf "${CONDA_ENVNAME}"
    # $env:CONDA_DEFAULT_ENV="${d}\${f}"
    # Remove-Variable d
    # Remove-Variable f
    $env:CONDA_DEFAULT_ENV=Resolve-Path "${CONDA_ENVNAME}"
} else {
    $env:CONDA_DEFAULT_ENV="${CONDA_ENVNAME}"
}
if ( "${IS_ENV_CONDA_ENVNAME}" -eq "${TRUE}" ) { $env:CONDA_ENVNAME="${CONDA_ENVNAME}" }
Remove-Variable CONDA_ENVNAME
Remove-Variable IS_ENV_CONDA_ENVNAME
# END CONDA_DEFAULT_ENV                                                   #
###########################################################################

###########################################################################
# PROMPT & CONDA_PS1_BACKUP                                               #
# export PROMPT to restore upon deactivation                              #
# customize the PROMPT to show what environment has been activated        #
#                                                                         #
# TODO: this is much too complex to do here, delegate to Python           #
# TODO: redesign conda ..changeps1 to actually return the new prompt      #
if ( conda ..changeps1 -eq 1 -and (Get-Command Prompt).definition -ne "" ) {
    $env:CONDA_PS1_BACKUP=Get-Content function:\Prompt
    # Set-Content function:\Prompt $env:CONDA_PS1_BACKUP
}
# END PS1 & CONDA_PS1_BACKUP                                              #
###########################################################################

###########################################################################
# LOAD POST-ACTIVATE SCRIPTS                                              #
# scripts found in $env:CONDA_PREFIX\etc\conda\activate.d                 #
$_CONDA_DIR="${env:CONDA_PREFIX}\etc\conda\activate.d"
if ( Test-Path -PathType Container "${_CONDA_DIR}" ) {
    Get-ChildItem -Path "${_CONDA_DIR}" -Filter "*.ps1" | % {
        $f="$_"
        if ( "${CONDA_VERBOSE}" -eq "${TRUE}" ) {
            echo "[ACTIVATE]: Sourcing ${_CONDA_DIR}\${f}."
        }
        . "${_CONDA_DIR}\${f}"
    }

}
Remove-Variable _CONDA_DIR
if ( "${IS_ENV_CONDA_VERBOSE}" -eq "${TRUE}" ) { $env:CONDA_VERBOSE="${CONDA_VERBOSE}" }
Remove-Variable CONDA_VERBOSE
Remove-Variable IS_ENV_CONDA_VERBOSE
# END LOAD POST-ACTIVATE SCRIPTS                                          #
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
