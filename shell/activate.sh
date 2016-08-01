#!/bin/sh

#
# `source activate` for sh
#

######################################################################
# test if script is sourced (zsh cannot be reliably checked)
######################################################################
if [[ -n $BASH_VERSION && $(basename -- "$0") =~ .*"activate".* ]]; then
    # we are not being sourced
    echo '[ACTIVATE]: ERROR: Must be sourced. Run `source activate`.' 1>&2
    exit 1
fi

###############################################################################
# local vars
###############################################################################
_SHELL="bash"
[[ -n $ZSH_VERSION ]] && _SHELL="zsh"
case "$(uname -s)" in
    CYGWIN*|MINGW*|MSYS*)
        EXT=".exe"
        export MSYS2_ENV_CONV_EXCL=CONDA_PATH
        # ignore any windows backup paths from bat-based activation
        if [[ "$CONDA_PATH_BACKUP" =~ "/".*  ]]; then
           unset CONDA_PATH_BACKUP
        fi
        ;;
    *)
        EXT=""
        ;;
esac

HELP=false
UNKNOWN=""
envname=""

###############################################################################
# parse command line, perform command line error checking
###############################################################################
if [[ "$@" != "" ]]; then
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                HELP=true
                ;;
            *)
                if [[ "$envname" == "" ]]; then
                    envname="$arg"
                else
                    if [[ "$UNKNOWN" == "" ]]; then
                        UNKNOWN="$arg"
                    else
                        UNKNOWN="$UNKNOWN $arg"
                    fi
                    HELP=true
                fi
                ;;
        esac
    done
    unset args
    unset arg
fi

[[ "$envname" == "" ]] && envname="root"

######################################################################
# help dialog
######################################################################
if [[ "$HELP" == true ]]; then
    if [[ "$UNKNOWN" != "" ]]; then
        echo "[ACTIVATE]: ERROR: Unknown/Invalid flag/parameter ($UNKNOWN)" 1>&2
    fi
    conda ..activate ${_SHELL}${EXT} -h

    unset _SHELL
    unset EXT
    unset HELP
    if [[ "$UNKNOWN" != "" ]]; then
        unset UNKNOWN
        return 1
    else
        unset UNKNOWN
        return 0
    fi
fi
unset HELP
unset UNKNOWN

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${_SHELL}${EXT} "${envname}"
if [[ $? != 0 ]]; then
    unset _SHELL
    unset EXT
    return 1
fi

# store the _SHELL+EXT since it may get cleared by deactivate
_CONDA_BIN="${_SHELL}${EXT}"

# Ensure we deactivate any scripts from the old env
# be careful since deactivate will unset certain values (like $_SHELL and $EXT)
source "deactivate" ""

_CONDA_BIN=$(conda ..activate ${_CONDA_BIN} "${envname}" | sed 's| |\ |')
if [[ $? == 0 ]]; then
    # CONDA_PATH_BACKUP,CONDA_PS1_BACKUP
    # export these to restore upon deactivation
    export CONDA_PATH_BACKUP="${PATH}"
    export CONDA_PS1_BACKUP="${PS1}"

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
    if [[ "$envname" =~ .*"/".* ]]; then
        d=$(dirname "${envname}")
        d=$(cd "${d}" && pwd)
        f=$(basename "${envname}")
        export CONDA_DEFAULT_ENV="${d}/${f}"
        unset d
        unset f
    else
        export CONDA_DEFAULT_ENV="$envname"
    fi

    # PS1
    # customize the PS1 to show what environment has been activated
    if [[ $(conda ..changeps1) == "1" ]]; then
        export PS1="(${CONDA_DEFAULT_ENV}) $PS1"
    fi

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    _CONDA_DIR="$CONDA_PREFIX/etc/conda/activate.d"
    if [[ -d "${_CONDA_DIR}" ]]; then
        for f in $(ls "${_CONDA_DIR}" | grep \\.sh$); do
            source "${_CONDA_DIR}/${f}"
        done
    fi

    if [[ -n $BASH_VERSION ]]; then
        # sh/bash uses hash
        hash -r
    else
        # most others uses rehash
        rehash
    fi

    unset _SHELL
    unset EXT
    unset envname
    unset _CONDA_BIN
    unset _CONDA_DIR

    return 0
else
    unset _SHELL
    unset EXT
    unset envname
    unset _CONDA_BIN
    return 1
fi
