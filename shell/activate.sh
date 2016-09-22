#!/bin/sh

#
# . activate for bourne-shell
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
IS_ENV_CONDA_HELP="${FALSE}"
IS_ENV_CONDA_VERBOSE="${FALSE}"
IS_ENV_CONDA_ENVNAME="${FALSE}"
[ $(env | grep CONDA_HELP) ]    && IS_ENV_CONDA_HELP="${TRUE}"
[ $(env | grep CONDA_VERBOSE) ] && IS_ENV_CONDA_VERBOSE="${TRUE}"
[ $(env | grep CONDA_ENVNAME) ] && IS_ENV_CONDA_ENVNAME="${TRUE}"

# inherit whatever the user set
# this is important for dash (and other shells) where you cannot pass
# parameters to sourced scripts
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
if [ -z "${CONDA_ENVNAME+x}" ]; then
    CONDA_ENVNAME=""
fi

# at this point CONDA_HELP, UNKNOWN, CONDA_VERBOSE, and CONDA_ENVNAME are
# defined and do not need to be checked for unbounded again

###############################################################################
# parse command line, perform command line error checking
###############################################################################
num=0
is_envname_set="${FALSE}"
while [ $num != -1 ]; do
    num=$(($num + 1))
    arg=$(eval eval echo '\${$num}') >/dev/null 2>&1

    if [ $? != 0 ] || [ -z $(echo "${arg}" | sed 's| ||g') ]; then
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
                if [ "${is_envname_set}" = "${FALSE}" ]; then
                    CONDA_ENVNAME="${arg}"
                    is_envname_set="${TRUE}"
                else
                    if [ -z "${UNKNOWN}" ]; then
                        UNKNOWN="${arg}"
                    else
                        UNKNOWN="${UNKNOWN} ${arg}"
                    fi
                    CONDA_HELP="${TRUE}"
                fi
                ;;
        esac
    fi
done
unset num
unset arg
unset is_envname_set

# if any of these variables are undefined set them to a default
[ -z "${CONDA_HELP}" ]    && CONDA_HELP="${FALSE}"
[ -z "${CONDA_VERBOSE}" ] && CONDA_VERBOSE="${FALSE}"
[ -z "${CONDA_ENVNAME}" ] && CONDA_ENVNAME="root"

# export CONDA_* variables as necessary
[ "${IS_ENV_CONDA_ENVNAME}" = "${TRUE}" ] && export CONDA_ENVNAME="${CONDA_ENVNAME}"
[ "${IS_ENV_CONDA_HELP}" = "${TRUE}" ]    && export CONDA_HELP="${CONDA_HELP}"
[ "${IS_ENV_CONDA_VERBOSE}" = "${TRUE}" ] && export CONDA_VERBOSE="${CONDA_VERBOSE}"

######################################################################
# help dialog
######################################################################
if [ "${CONDA_HELP}" = "${TRUE}" ]; then
    conda ..activate ${WHAT_SHELL_AM_I} -h ${UNKNOWN}

    unset WHAT_SHELL_AM_I
    [ "${IS_ENV_CONDA_ENVNAME}" = "${FALSE}" ] && unset CONDA_ENVNAME
    [ "${IS_ENV_CONDA_HELP}" = "${FALSE}" ]    && unset CONDA_HELP
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_HELP
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    if [ -n "${UNKNOWN}" ]; then
        unset UNKNOWN
        return 1
    else
        unset UNKNOWN
        return 0
    fi
fi
[ "${IS_ENV_CONDA_HELP}" = "${FALSE}" ] && unset CONDA_HELP
unset IS_ENV_CONDA_HELP
unset UNKNOWN

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${WHAT_SHELL_AM_I} "${CONDA_ENVNAME}"
if [ $? != 0 ]; then
    unset WHAT_SHELL_AM_I
    [ "${IS_ENV_CONDA_ENVNAME}" = "${FALSE}" ] && unset CONDA_ENVNAME
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    return 1
fi

# store remaining values that may get cleared by deactivate
_CONDA_WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}"
_CONDA_VERBOSE="${CONDA_VERBOSE}"
_IS_ENV_CONDA_VERBOSE="${IS_ENV_CONDA_VERBOSE}"

# ensure we deactivate any scripts from the old env
. deactivate.sh ""

# restore boolean
TRUE=0
FALSE=1

# restore values
IS_ENV_CONDA_VERBOSE="${_IS_ENV_CONDA_VERBOSE}"
CONDA_VERBOSE="${_CONDA_VERBOSE}"
WHAT_SHELL_AM_I="${_CONDA_WHAT_SHELL_AM_I}"
unset _IS_ENV_CONDA_VERBOSE
unset _CONDA_VERBOSE
unset _CONDA_WHAT_SHELL_AM_I

_CONDA_BIN=$(conda ..activate ${WHAT_SHELL_AM_I} "${CONDA_ENVNAME}" | sed 's| |\ |')
if [ $? = 0 ]; then
    # PATH
    # update path with the new conda environment
    export PATH="${_CONDA_BIN}:${PATH}"

    # CONDA_PREFIX
    # always the full path to the activated environment
    # is not set when no environment is active
    export CONDA_PREFIX="$(echo ${_CONDA_BIN} | sed 's|/bin$||')"

    # CONDA_DEFAULT_ENV
    # the shortest representation of how conda recognizes your env
    # can be an env name, or a full path (if the string contains / it's a path)
    if [ $(echo "${CONDA_ENVNAME}" | awk '{exit(match($0,/.*\/.*/) != 0)}') ]; then
        d=$(dirname "${CONDA_ENVNAME}")
        d=$(cd "${d}" && pwd)
        f=$(basename "${CONDA_ENVNAME}")
        export CONDA_DEFAULT_ENV="${d}/${f}"
        unset d
        unset f
    else
        export CONDA_DEFAULT_ENV="${CONDA_ENVNAME}"
    fi

    # PS1 & CONDA_PS1_BACKUP
    # export PS1 to restore upon deactivation
    # customize the PS1 to show what environment has been activated
    if [ $(conda ..changeps1) = 1 ] && [ -n "${PS1+x}" ]; then
        export CONDA_PS1_BACKUP="${PS1}"
        export PS1="(${CONDA_DEFAULT_ENV}) ${PS1}"
    fi

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    _CONDA_DIR="${CONDA_PREFIX}/etc/conda/activate.d"
    if [ -d "${_CONDA_DIR}" ]; then
        for f in $(ls "${_CONDA_DIR}" | grep \\.sh$); do
            [ "${CONDA_VERBOSE}" = "${TRUE}" ] && echo "[ACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            . "${_CONDA_DIR}/${f}"
        done
    fi
    unset _CONDA_DIR

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

    unset WHAT_SHELL_AM_I
    unset _CONDA_BIN
    [ "${IS_ENV_CONDA_ENVNAME}" = "${FALSE}" ] && unset CONDA_ENVNAME
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    return 0
else
    unset WHAT_SHELL_AM_I
    unset _CONDA_BIN
    [ "${IS_ENV_CONDA_ENVNAME}" = "${FALSE}" ] && unset CONDA_ENVNAME
    [ "${IS_ENV_CONDA_VERBOSE}" = "${FALSE}" ] && unset CONDA_VERBOSE
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    return 1
fi
