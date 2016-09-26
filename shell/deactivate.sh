#!/usr/bin/env bash

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # DEACTIVATE FOR BOURNE-SHELL                                         # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# DEFINE BASIC VARS                                                       #
TRUE=1
FALSE=0
if [ -n "${ZSH_VERSION+x}" ]; then
    WHAT_SHELL_AM_I="zsh"
elif [ -n "${BASH_VERSION+x}" ]; then
    WHAT_SHELL_AM_I="bash"
elif [ -n "${POSH_VERSION+x}" ]; then
    WHAT_SHELL_AM_I="posh"
else
    WHAT_SHELL_AM_I="dash"
fi
case "$(uname -s)" in
    CYGWIN*|MINGW*|MSYS*)
        WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}.exe"
        MSYS2_ENV_CONV_EXCL="CONDA_PATH"
        export MSYS2_ENV_CONV_EXCL
        ;;
esac

# note whether or not the CONDA_* variables are exported, if so we need   #
# to preserve that status                                                 #
IS_ENV_CONDA_HELP="${FALSE}"
IS_ENV_CONDA_VERBOSE="${FALSE}"
[ "$(env | grep -q CONDA_HELP)" ]    && IS_ENV_CONDA_HELP="${TRUE}"
[ "$(env | grep -q CONDA_VERBOSE)" ] && IS_ENV_CONDA_VERBOSE="${TRUE}"

# inherit whatever the user set                                           #
# this is important for dash (and other shells) where you cannot pass     #
# parameters to sourced scripts                                           #
if [ -z "${CONDA_HELP+x}" ] || [ "${CONDA_HELP}" = "${FALSE}" ] || [ "${CONDA_HELP}" = "false" ] || [ "${CONDA_HELP}" = "FALSE" ] || [ "${CONDA_HELP}" = "False" ]; then
    CONDA_HELP="${FALSE}"
elif [ "${CONDA_HELP}" = "${TRUE}" ] || [ "${CONDA_HELP}" = "true" ] || [ "${CONDA_HELP}" = "TRUE" ] || [ "${CONDA_HELP}" = "True" ]; then
    CONDA_HELP="${TRUE}"
fi
UNKNOWN=""
if [ -z "${CONDA_VERBOSE+x}" ] || [ "${CONDA_VERBOSE}" = "${FALSE}" ] || [ "${CONDA_VERBOSE}" = "false" ] || [ "${CONDA_VERBOSE}" = "FALSE" ] || [ "${CONDA_VERBOSE}" = "False" ]; then
    CONDA_VERBOSE="${FALSE}"
elif [ "${CONDA_VERBOSE}" = "${TRUE}" ] || [ "${CONDA_VERBOSE}" = "true" ] || [ "${CONDA_VERBOSE}" = "TRUE" ] || [ "${CONDA_VERBOSE}" = "True" ]; then
    CONDA_VERBOSE="${TRUE}"
fi

# at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and CONDA_ENVNAME are #
# defined and do not need to be checked for unbounded again               #
# END DEFINE BASIC VARS                                                   #
###########################################################################

###########################################################################
# PARSE COMMAND LINE                                                      #
num=0
while [ $num != -1 ]; do
    num=$((num + 1))
    arg=$(eval eval echo '\${$num}') >/dev/null 2>&1

    # check if variable is blank, if so stop parsing
    if [ $? != 0 ] || [ -z "$(echo ${arg} | sed 's| ||g')" ]; then
        num=-1
    else
        case "${arg}" in
            -h|--help)
                CONDA_HELP="${TRUE}"
                ;;
            -v|--verbose)
                CONDA_VERBOSE="${TRUE}"
                ;;
            *)
                # check if variable is blank, append unknown accordingly
                if [ -z "${UNKNOWN}" ]; then
                    UNKNOWN="${arg}"
                else
                    UNKNOWN="${UNKNOWN} ${arg}"
                fi
                CONDA_HELP="${TRUE}"
                ;;
        esac
    fi
done
unset num
unset arg

# if any of these variables are undefined set them to a default           #
[ -z "${CONDA_HELP}" ]    && CONDA_HELP="${FALSE}"
[ -z "${CONDA_VERBOSE}" ] && CONDA_VERBOSE="${FALSE}"

# export CONDA_* variables as necessary                                   #
[ "${IS_ENV_CONDA_HELP}" = "${TRUE}" ]    && export CONDA_HELP
[ "${IS_ENV_CONDA_VERBOSE}" = "${TRUE}" ] && export CONDA_VERBOSE
# END PARSE COMMAND LINE                                                  #
###########################################################################

###########################################################################
# HELP DIALOG                                                             #
if [ "${CONDA_HELP}" = "${TRUE}" ]; then
    conda "..deactivate" "${WHAT_SHELL_AM_I}" "-h" ${UNKNOWN}

    unset WHAT_SHELL_AM_I
    [ "${IS_ENV_CONDA_HELP}" = "${FALSE}" ]    && unset CONDA_HELP
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_HELP
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    # check if UNKNOWN is blank, error accordingly
    if [ -n "${UNKNOWN}" ]; then
        unset UNKNOWN
        return 1
    else
        unset UNKNOWN
        return 0
    fi
fi
unset WHAT_SHELL_AM_I
[ "${IS_ENV_CONDA_HELP}" = "${FALSE}" ] && unset CONDA_HELP
unset IS_ENV_CONDA_HELP
unset UNKNOWN
# END HELP DIALOG                                                         #
###########################################################################

###########################################################################
# CHECK IF CAN DEACTIVATE                                                 #
if [ -z "${CONDA_DEFAULT_ENV}" ]; then
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    return 1
fi
# END CHECK IF CAN DEACTIVATE                                             #
###########################################################################

###########################################################################
# RESTORE PATH                                                            #
# remove only first instance of $CONDA_PREFIX from $PATH, since this is   #
# Unix we will only expect a single path that need to be removed, for     #
# simplicity and consistency with the Windows *.bat scripts we will use   #
# fuzzy matching (/f) to get all of the relevant removals                 #
PATH=$(envvar_cleanup.bash "${PATH}" --delim=":" -u -f "${CONDA_PREFIX}")
export PATH
# END RESTORE PATH                                                        #
###########################################################################

###########################################################################
# REMOVE CONDA_PREFIX                                                     #
# set $_CONDA_DIR for post-deactivate loading                             #
_CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
unset CONDA_PREFIX
# END REMOVE CONDA_PREFIX                                                 #
###########################################################################

###########################################################################
# REMOVE CONDA_DEFAULT_ENV                                                #
unset CONDA_DEFAULT_ENV
# END REMOVE CONDA_DEFAULT_ENV                                            #
###########################################################################

###########################################################################
# RESTORE PS1 & REMOVE CONDA_PS1_BACKUP                                   #
if [ -n "${CONDA_PS1_BACKUP+x}" ] && [ -n "${PS1+x}" ]; then
    PS1="${CONDA_PS1_BACKUP}"
    export PS1
    unset CONDA_PS1_BACKUP
fi
# END RESTORE PS1 & REMOVE CONDA_PS1_BACKUP                               #
###########################################################################

###########################################################################
# LOAD POST-DEACTIVATE SCRIPTS                                            #
if [ -d "${_CONDA_DIR}" ]; then
    # use ls | grep instead of in place globbing to support POSH
    for f in $(ls "${_CONDA_DIR}" | grep "\\.sh$"); do
        if [ "${CONDA_VERBOSE}" = "${TRUE}" ]; then
            echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
        fi
        . "${_CONDA_DIR}/${f}"
    done
fi
unset _CONDA_DIR
[ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
unset IS_ENV_CONDA_VERBOSE
# END LOAD POST-DEACTIVATE SCRIPTS                                        #
###########################################################################

###########################################################################
# REHASH                                                                  #
if [ -n "${ZSH_VERSION+x}" ]; then
    # ZSH
    rehash
elif [ -n "${BASH_VERSION+x}" ]; then
    # BASH
    hash -r
elif [ -n "${POSH_VERSION+x}" ]; then
    # no rehash for POSH
    :
else
    # DASH, default
    hash -r
fi
# END REHASH                                                              #
###########################################################################

###########################################################################
# CLEANUP VARS FOR THIS SCOPE                                             #
unset TRUE
unset FALSE
return 0
# END CLEANUP VARS FOR THIS SCOPE                                         #
###########################################################################
