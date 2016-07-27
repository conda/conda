#!/bin/sh

#
# `source deactivate` for sh
#

######################################################################
# test if script is sourced
######################################################################
if [[ $(basename -- "$0") =~ .*"deactivate".* ]]; then
    # we are not being sourced
    echo '[DEACTIVATE]: ERROR: Must be sourced. Run `source deactivate`.'
    exit 1
fi

###############################################################################
# local vars
###############################################################################
HELP=false
UNKNOWN=""

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
            if [[ "$UNKNOWN" == "" ]]; then
                UNKNOWN="$arg"
            else
                UNKNOWN="$UNKNOWN $arg"
            fi
            HELP=true
            ;;
    esac
done
unset args
unset arg

######################################################################
# help dialog
######################################################################
if [[ "$HELP" == true ]]; then
    if [[ "$UNKNOWN" != "" ]]; then
        echo "[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter ($UNKNOWN)"
    fi
    conda ..deactivate ${_SHELL}${EXT} -h

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
# determine if there is anything to deactivate and deactivate
# accordingly
######################################################################
if [[ -n $CONDA_PATH_BACKUP ]]; then
    # unload post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
    _CONDA_DIR="$CONDA_PREFIX/etc/conda/deactivate.d"
    if [[ -d "${_CONDA_DIR}" ]]; then
        for f in $(find "${_CONDA_DIR}" -iname "*.sh"); do
            source "$f"
        done
    fi
    unset _CONDA_DIR

    # restore PROMPT
    export PS1="$CONDA_PS1_BACKUP"

    # remove CONDA_DEFAULT_ENV
    unset CONDA_DEFAULT_ENV

    # remove CONDA_PREFIX
    unset CONDA_PREFIX

    # restore PATH
    export PATH="$CONDA_PATH_BACKUP"

    # remove CONDA_PATH_BACKUP,CONDA_PROMPT_BACKUP
    unset CONDA_PROMPT_BACKUP
    unset CONDA_PATH_BACKUP

    if [[ -n $BASH_VERSION ]]; then
        # sh/bash uses hash
        hash -r
    else
        # most others uses rehash
        rehash
    fi
fi

return 0
