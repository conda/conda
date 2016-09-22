#!/bin/sh

#
# . deactivate for bourne-shell
#

###############################################################################
# local vars
###############################################################################
TRUE=0
FALSE=1
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
        export MSYS2_ENV_CONV_EXCL="CONDA_PATH"
        ;;
esac

# note whether or not the CONDA_* variables are exported, if so we need to
# preserve that status
[ $(env | grep CONDA_HELP) ]    && IS_ENV_CONDA_HELP="${TRUE}"    || IS_ENV_CONDA_HELP="${FALSE}"
[ $(env | grep CONDA_VERBOSE) ] && IS_ENV_CONDA_VERBOSE="${TRUE}" || IS_ENV_CONDA_VERBOSE="${FALSE}"

# inherit whatever the user set
# this is important for dash where you cannot pass parameters to sourced scripts
if [ -z "${CONDA_HELP+x}" ] || [ "${CONDA_HELP}" = "false" ] || [ "${CONDA_HELP}" = "FALSE" ] || [ "${CONDA_HELP}" = "False" ]; then
    CONDA_HELP="${FALSE}"
elif [ "${CONDA_HELP}" = "true" ] || [ "${CONDA_HELP}" = "TRUE" ] || [ "${CONDA_HELP}" = "True" ]; then
    CONDA_HELP="${TRUE}"
fi
UNKNOWN=""
if [ -z "${CONDA_VERBOSE+x}" ] || [ "${CONDA_VERBOSE}" = "false" ] || [ "${CONDA_VERBOSE}" = "FALSE" ] || [ "${CONDA_VERBOSE}" = "False" ]; then
    CONDA_VERBOSE="${FALSE}"
elif [ "${CONDA_VERBOSE}" = "true" ] || [ "${CONDA_VERBOSE}" = "TRUE" ] || [ "${CONDA_VERBOSE}" = "True" ]; then
    CONDA_VERBOSE="${TRUE}"
fi

# at this point CONDA_HELP, UNKNOWN, and CONDA_VERBOSE are
# defined and do not need to be checked for unbounded again

###############################################################################
# parse command line, perform command line error checking
###############################################################################
num=0
while [ $num != -1 ]; do
    num=$(($num + 1))
    arg=$(eval eval echo '\$$num')

    if [ -z $(echo "${arg}" | sed 's| ||g') ]; then
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
                # if it is undefined (check if unbounded) and if it is zero
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

# if any of these variables are undefined (i.e. unbounded) set them to a default
[ -z "${CONDA_HELP}" ]    && CONDA_HELP="${FALSE}"
[ -z "${CONDA_VERBOSE}" ] && CONDA_VERBOSE="${FALSE}"

# export CONDA_* variables as necessary
[ "${IS_ENV_CONDA_HELP}" = "${TRUE}" ]    && export CONDA_HELP="${CONDA_HELP}"
[ "${IS_ENV_CONDA_VERBOSE}" = "${TRUE}" ] && export CONDA_VERBOSE="${CONDA_VERBOSE}"

######################################################################
# help dialog
######################################################################
if [ "${CONDA_HELP}" = "${TRUE}" ]; then
    conda ..deactivate ${WHAT_SHELL_AM_I} -h ${UNKNOWN}

    unset WHAT_SHELL_AM_I
    [ "${IS_ENV_CONDA_HELP}" = "${FALSE}" ]    && unset CONDA_HELP
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_HELP
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    # if it is defined (check if unbounded) and if it is non-zero
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

######################################################################
# determine if there is anything to deactivate and deactivate
# accordingly
######################################################################
if [ -n "${CONDA_DEFAULT_ENV}" ]; then
    # unload post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
    _CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
    if [ -d "${_CONDA_DIR}" ]; then
        for f in $(ls "${_CONDA_DIR}" | grep \\.sh$); do
            [ "${CONDA_VERBOSE}" = "${TRUE}" ] && echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            . "${_CONDA_DIR}/${f}"
        done
    fi
    unset _CONDA_DIR

    # restore PROMPT
    if [ -n "${CONDA_PS1_BACKUP+x}" ] && [ -n "${PS1+x}" ]; then
        export PS1="${CONDA_PS1_BACKUP}"
        unset CONDA_PS1_BACKUP
    fi

    # remove CONDA_DEFAULT_ENV
    unset CONDA_DEFAULT_ENV

    # remove only first instance of CONDA_PREFIX from PATH
    export PATH=$(envvar_cleanup.sh "${PATH}" -r "${CONDA_PREFIX}/bin")

    # remove CONDA_PREFIX
    unset CONDA_PREFIX

    if [ -n "${ZSH_VERSION+x}" ]; then
        # zsh uses rehash
        rehash
    elif [ -n "${BASH_VERSION+x}" ]; then
        # bash
        hash -r
    elif [ -n "${POSH_VERSION+x}" ]; then
        # posh
        # no hash command for posh
        :
    else
        # dash uses hash, default
        hash -r
    fi
fi

[ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
unset IS_ENV_CONDA_VERBOSE
unset TRUE
unset FALSE
return 0
