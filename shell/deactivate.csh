#!/usr/bin/env csh

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # DEACTIVATE FOR C-SHELL                                              # #
# #                                                                     # #
# # use == "" instead of -z test (and != "" for -n) for robust support  # #
# # across different platforms (especially Ubuntu)                      # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# DEFINE BASIC VARS                                                       #
set TRUE=1
set FALSE=0
set WHAT_SHELL_AM_I="csh"
switch ( `uname -s` )
    case "CYGWIN*":
    case "MINGW*":
    case "MSYS*":
        set WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}.exe"
        setenv MSYS2_ENV_CONV_EXCL "CONDA_PATH"
        breaksw
endsw

# note whether or not the CONDA_* variables are exported, if so we need   #
# to preserve that status                                                 #
set IS_ENV_CONDA_HELP="${FALSE}"
set IS_ENV_CONDA_VERBOSE="${FALSE}"
if ( `env | grep CONDA_HELP` != "" ) then
    set IS_ENV_CONDA_HELP="${TRUE}"
endif
if ( `env | grep CONDA_VERBOSE` != "" ) then
    set IS_ENV_CONDA_VERBOSE="${TRUE}"
endif

# inherit whatever the user set                                           #
# this is important for dash (and other shells) where you cannot pass     #
# parameters to sourced scripts                                           #
if ( ! $?CONDA_HELP ) then
    set CONDA_HELP="${FALSE}"
else if ( "${CONDA_HELP}" == "${FALSE}" || "${CONDA_HELP}" == "false" || "${CONDA_HELP}" == "FALSE" || "${CONDA_HELP}" == "False") then
    set CONDA_HELP="${FALSE}"
else if ( "${CONDA_HELP}" == "${TRUE}" || "${CONDA_HELP}" == "true" || "${CONDA_HELP}" == "TRUE" || "${CONDA_HELP}" == "True" ) then
    set CONDA_HELP="${TRUE}"
endif
set UNKNOWN=""
if ( ! $?CONDA_VERBOSE ) then
    set CONDA_VERBOSE="${FALSE}"
else if ( "${CONDA_VERBOSE}" == "${FALSE}" || "${CONDA_VERBOSE}" == "false" || "${CONDA_VERBOSE}" == "FALSE" || "${CONDA_VERBOSE}" == "False") then
    set CONDA_VERBOSE="${FALSE}"
else if ( "${CONDA_VERBOSE}" == "${TRUE}" || "${CONDA_VERBOSE}" == "true" || "${CONDA_VERBOSE}" == "TRUE" || "${CONDA_VERBOSE}" == "True" ) then
    set CONDA_VERBOSE="${TRUE}"
endif
# at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and CONDA_ENVNAME are #
# defined and do not need to be checked for unbounded again               #
# END DEFINE BASIC VARS                                                   #
###########################################################################

###########################################################################
# PARSE COMMAND LINE                                                      #
set num=0
while ( $num != -1 )
    @ num = ($num + 1)
    set arg=`eval eval echo '\$$num'`

    # check if variable is blank, if so stop parsing
    if ( $status != 0 || "`echo ${arg} | sed 's| ||g'`" == "" ) then
        set num=-1
    else
        switch ( "${arg}" )
            case "-h":
            case "--help":
                set CONDA_HELP="${TRUE}"
                breaksw
            case "-v":
            case "--verbose":
                set CONDA_VERBOSE="${TRUE}"
                breaksw
            default:
                if ( "${UNKNOWN}" == "" ) then
                    set UNKNOWN="${arg}"
                else
                    set UNKNOWN="${UNKNOWN} ${arg}"
                endif
                set CONDA_HELP="${TRUE}"
                breaksw
        endsw
    endif
end
unset num
unset arg

# if any of these variables are undefined set them to a default           #
if ( "`echo ${CONDA_HELP} | sed 's| ||g'`" == "" ) then
    set CONDA_HELP="${FALSE}"
endif
if ( "`echo ${CONDA_VERBOSE} | sed 's| ||g'`" == "" ) then
    set CONDA_VERBOSE="${FALSE}"
endif

# export CONDA_* variables as necessary                                   #
if ( "${IS_ENV_CONDA_HELP}" == "${TRUE}" ) then
    setenv CONDA_HELP "${CONDA_HELP}"
endif
if ( "${IS_ENV_CONDA_VERBOSE}" == "${TRUE}" ) then
    setenv CONDA_VERBOSE "${CONDA_VERBOSE}"
endif
# END PARSE COMMAND LINE                                                  #
###########################################################################

###########################################################################
# HELP DIALOG                                                             #
if ( "${CONDA_HELP}" == "${TRUE}" ) then
    conda "..deactivate" "${WHAT_SHELL_AM_I}" "-h" ${UNKNOWN}

    unset WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_HELP}" == "${FALSE}" ) then
        unset CONDA_HELP
    endif
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
    unset IS_ENV_CONDA_HELP
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    # check if UNKNOWN is blank, error accordingly
    if ( "${UNKNOWN}" != "" ) then
        unset UNKNOWN
        exit 1
    else
        unset UNKNOWN
        exit 0
    endif
endif
unset WHAT_SHELL_AM_I
if ( "${IS_ENV_CONDA_HELP}" == "${FALSE}" ) then
    unset CONDA_HELP
endif
unset IS_ENV_CONDA_HELP
unset UNKNOWN
# END HELP DIALOG                                                         #
###########################################################################

###########################################################################
# CHECK IF CAN DEACTIVATE                                                 #
set BAD_DEACTIVATE="${FALSE}"
if ( $?CONDA_DEFAULT_ENV ) then
    if ( "${CONDA_DEFAULT_ENV}" == "" ) then
        set BAD_DEACTIVATE="${TRUE}"
    endif
else
    set BAD_DEACTIVATE="${TRUE}"
endif
if ( "${BAD_DEACTIVATE}" == "${TRUE}" ) then
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    exit 1
endif
# END CHECK IF CAN DEACTIVATE                                             #
###########################################################################

###########################################################################
# RESTORE PATH                                                            #
# remove only first instance of $CONDA_PREFIX from $PATH, use $tmp_PATH   #
# to avoid cases when path setting succeeds and is parsed correctly from  #
# one to the other                                                        #
set tmp_PATH="${PATH}"
set PATH=(`envvar_cleanup.bash "${tmp_PATH}" --delim=":" -u -f "${CONDA_PREFIX}"`)
set path=(`echo "${PATH}" | sed s'|:| |g'`)
unset tmp_PATH
# END RESTORE PATH                                                        #
###########################################################################

###########################################################################
# REMOVE CONDA_PREFIX                                                     #
# set $_CONDA_DIR for post-deactivate loading                             #
set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
unsetenv CONDA_PREFIX
# END REMOVE CONDA_PREFIX                                                 #
###########################################################################

###########################################################################
# REMOVE CONDA_DEFAULT_ENV                                                #
unsetenv CONDA_DEFAULT_ENV
# END REMOVE CONDA_DEFAULT_ENV                                            #
###########################################################################

###########################################################################
# RESTORE PS1 & REMOVE CONDA_PS1_BACKUP                                   #
if ( $?CONDA_PS1_BACKUP && $?prompt ) then
    set prompt="${CONDA_PS1_BACKUP}"
    unsetenv CONDA_PS1_BACKUP
endif
# END RESTORE PS1 & REMOVE CONDA_PS1_BACKUP                               #
###########################################################################

###########################################################################
# LOAD POST-DEACTIVATE SCRIPTS                                            #
if ( -d "${_CONDA_DIR}" ) then
    foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
        if ( "${CONDA_VERBOSE}" == "${TRUE}" ) then
            echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
        endif
        source "${_CONDA_DIR}/${f}"
    end
endif
unset _CONDA_DIR
if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
    unset CONDA_VERBOSE
endif
unset IS_ENV_CONDA_VERBOSE
# END LOAD POST-DEACTIVATE SCRIPTS                                        #
###########################################################################

###########################################################################
# REHASH                                                                  #
# CSH/TCSH both use rehash
rehash
# END REHASH                                                              #
###########################################################################

###########################################################################
# CLEANUP VARS FOR THIS SCOPE                                             #
unset TRUE
unset FALSE
exit 0
# END CLEANUP VARS FOR THIS SCOPE                                         #
###########################################################################
