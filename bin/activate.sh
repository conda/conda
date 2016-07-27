#!/bin/sh

#
# `source activate` for sh
#

######################################################################
# test if script is sourced
######################################################################
if [[ $(basename -- "$0") =~ .*"activate".* ]]; then
    # we are not being sourced
    echo '[ACTIVATE]: ERROR: Must be sourced. Run `source activate`.'
    exit 1
fi

###############################################################################
# local vars
###############################################################################
_SHELL="bash"
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
envname="root"

###############################################################################
# parse command line, perform command line error checking
###############################################################################
args="$@"
for arg in $args; do
    case "$arg" in
        -h|--help)
            HELP=true
            ;;
        *)
            envname="$arg"
            ;;
    esac
done
unset args
unset arg

######################################################################
# help dialog
######################################################################
if [[ "$HELP" == true ]]; then
    conda ..activate ${_SHELL}${EXT} -h

    unset HELP
    return 0
fi
unset HELP

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${_SHELL}${EXT} "$envname"
[[ $? != 0 ]] && return 1

# Ensure we deactivate any scripts from the old env
source deactivate ""

_CONDA_BIN=$(conda ..activate ${_SHELL}${EXT} "$envname")
if [[ $? == 0 ]]; then
    # CONDA_PATH_BACKUP,CONDA_PROMPT_BACKUP
    # export these to restore upon deactivation
    export CONDA_PATH_BACKUP="${PATH}"
    export CONDA_PS1_BACKUP="${PS1}"

    # PATH
    # update path with the new conda environment
    export PATH="${_CONDA_BIN}:${PATH}"

    # CONDA_PREFIX
    # always the full path to the activated environment
    # is not set when no environment is active
    SED=$(which sed) || SED="sed"
    export CONDA_PREFIX=$(echo ${_CONDA_BIN} | $SED 's|/bin$||' >& /dev/null)
    unset SED

    # CONDA_DEFAULT_ENV
    # the shortest representation of how conda recognizes your env
    # can be an env name, or a full path (if the string contains / it's a path)
    if [[ "$envname" =~ "*/*" ]]; then
        export CONDA_DEFAULT_ENV=$(get_abs_filename "$envname")
    else
        export CONDA_DEFAULT_ENV="$envname"
    fi

    # PS1
    # customize the PS1 to show what environment has been activated
    if [[ $(conda ..changeps1) == "1" ]]; then
        echo "$PS1" | grep -q CONDA_DEFAULT_ENV &> /dev/null
        if [[ $? != 0 ]]; then
            export PS1="(${CONDA_DEFAULT_ENV}) $PS1"
        fi
    fi

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    _CONDA_DIR="$CONDA_PREFIX/etc/conda/activate.d"
    if [[ -d "${_CONDA_DIR}" ]]; then
        for f in $(find "${_CONDA_DIR}" -iname "*.sh"); do
            source "$f"
        done
    fi

    if [[ -n $BASH_VERSION ]]; then
        # sh/bash uses hash
        hash -r
    else
        # most others uses rehash
        rehash
    fi
else
    return 1
fi

unset _SHELL
unset EXT
unset envname
unset _CONDA_BIN
unset _CONDA_DIR

return 0
