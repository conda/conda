#!/bin/sh

#
# . activate for bourne-shell
#

###############################################################################
# local vars
###############################################################################
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

# inherit whatever the user set
# this is important for dash (and other shells) where you cannot pass
# parameters to sourced scripts
# CONDA_HELP=false
UNKNOWN=""
# CONDA_VERBOSE=false
# CONDA_ENVNAME=""

###############################################################################
# parse command line, perform command line error checking
###############################################################################
num=0
is_envname_set=false
while [ $num != -1 ]; do
    num=$(($num + 1))
    arg=$(eval eval echo '\${$num}') >/dev/null 2>&1

    if [ $? != 0 ] || [ -z $(echo "${arg}" | sed 's| ||g') ]; then
        num=-1
    else
        case "${arg}" in
            -h|--help)
                CONDA_HELP=true
                ;;
            -v|--verbose)
                CONDA_VERBOSE=true
                ;;
            *)
                if [ "${is_envname_set}" = false ]; then
                    CONDA_ENVNAME="${arg}"
                    is_envname_set=true
                else
                    # if it is undefined (check if unbounded) and if it is zero
                    if [ -z "${UNKNOWN+x}" ] || [ -z "${UNKNOWN}" ]; then
                        UNKNOWN="${arg}"
                    else
                        UNKNOWN="${UNKNOWN} ${arg}"
                    fi
                    CONDA_HELP=true
                fi
                ;;
        esac
    fi
done
unset num
unset arg
unset is_envname_set

# if any of these variables are undefined (i.e. unbounded) set them to a default
[ -z "${CONDA_HELP+x}" ] && CONDA_HELP=false
[ -z "${CONDA_VERBOSE+x}" ] && CONDA_VERBOSE=false
[ -z "${CONDA_ENVNAME+x}" ] && CONDA_ENVNAME="root"

######################################################################
# help dialog
######################################################################
if [ "${CONDA_HELP}" = true ]; then
    # if it is defined (check if unbounded) and if it is non-zero
    if [ -n "${UNKNOWN+x}" ] && [ -n "${UNKNOWN}" ]; then
        echo "[ACTIVATE]: ERROR: Unknown/Invalid flag/parameter (${UNKNOWN})" 1>&2
    fi
    conda ..activate ${WHAT_SHELL_AM_I} -h

    unset WHAT_SHELL_AM_I
    unset CONDA_ENVNAME
    unset CONDA_HELP
    unset CONDA_VERBOSE
    # if it is defined (check if unbounded) and if it is non-zero
    if [ -n "${UNKNOWN+x}" ] && [ -n "${UNKNOWN}" ]; then
        unset UNKNOWN
        return 1
    else
        unset UNKNOWN
        return 0
    fi
fi
unset CONDA_HELP
unset UNKNOWN

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${WHAT_SHELL_AM_I} "${CONDA_ENVNAME}"
if [ $? != 0 ]; then
    unset WHAT_SHELL_AM_I
    unset CONDA_ENVNAME
    unset CONDA_VERBOSE
    return 1
fi

# store the WHAT_SHELL_AM_I since it may get cleared by deactivate
# store the CONDA_VERBOSE since it may get cleared by deactivate
_CONDA_BIN="${WHAT_SHELL_AM_I}"
CONDA_VERBOSE_TMP="${CONDA_VERBOSE}"

# Ensure we deactivate any scripts from the old env
# be careful since deactivate will unset certain values (like WHAT_SHELL_AM_I and CONDA_VERBOSE)
. "`which deactivate.sh`" ""

# restore CONDA_VERBOSE
CONDA_VERBOSE="${CONDA_VERBOSE_TMP}"
unset CONDA_VERBOSE_TMP

_CONDA_BIN=$(conda ..activate ${_CONDA_BIN} "${CONDA_ENVNAME}" | sed 's| |\ |')
if [ $? = 0 ]; then
    # CONDA_PS1_BACKUP
    # export these to restore upon deactivation
    [ -n "${PS1+x}" ] && export CONDA_PS1_BACKUP="${PS1}"

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

    # PS1
    # customize the PS1 to show what environment has been activated
    if [ $(conda ..changeps1) = 1 ] && [ -n "${PS1+x}" ]; then
        export PS1="(${CONDA_DEFAULT_ENV}) ${PS1}"
    fi

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    _CONDA_DIR="${CONDA_PREFIX}/etc/conda/activate.d"
    if [ -d "${_CONDA_DIR}" ]; then
        for f in $(ls "${_CONDA_DIR}" | grep \\.sh$); do
            [ "${CONDA_VERBOSE}" = "true" ] && echo "[ACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            . "${_CONDA_DIR}/${f}"
        done
    fi

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
    unset CONDA_ENVNAME
    unset CONDA_VERBOSE
    unset _CONDA_BIN
    unset _CONDA_DIR

    return 0
else
    unset WHAT_SHELL_AM_I
    unset CONDA_ENVNAME
    unset CONDA_VERBOSE
    unset _CONDA_BIN
    return 1
fi
