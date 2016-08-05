#!/bin/sh

#
# `source deactivate` for sh
#

###############################################################################
# local vars
###############################################################################
if [ -n "${ZSH_VERSION}" ]; then
    _SHELL="zsh"
elif [ -n "${BASH_VERSION}" ]; then
    _SHELL="bash"
else
    _SHELL="dash"
fi
case "$(uname -s)" in
    CYGWIN*|MINGW*|MSYS*)
        EXT=".exe"
        export MSYS2_ENV_CONV_EXCL=CONDA_PATH
        # ignore any windows backup paths from bat-based activation
        if [ $(echo "${CONDA_PATH_BACKUP}" | awk '{exit(match($0,/\/.*/) != 0)}') ]; then
           unset CONDA_PATH_BACKUP
        fi
        ;;
    *)
        EXT=""
        ;;
esac

# inherit whatever the user set
# this is important for dash where you cannot pass parameters to sourced scripts
# CONDA_HELP=false
UNKNOWN=""
# CONDA_VERBOSE=false

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
                CONDA_HELP=true
                ;;
            -v|--verbose)
                CONDA_VERBOSE=true
                ;;
            *)
                if [ "${UNKNOWN}" = "" ]; then
                    UNKNOWN="${arg}"
                else
                    UNKNOWN="${UNKNOWN} ${arg}"
                fi
                CONDA_HELP=true
                ;;
        esac
    fi
done
unset num
unset arg

[ -z "${CONDA_HELP}" ] && CONDA_HELP=false
[ -z "${CONDA_VERBOSE}" ] && CONDA_VERBOSE=false

######################################################################
# help dialog
######################################################################
if [ "${CONDA_HELP}" = true ]; then
    if [ "${UNKNOWN}" != "" ]; then
        echo "[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter (${UNKNOWN})" 1>&2
    fi
    conda ..deactivate ${_SHELL}${EXT} -h

    unset _SHELL
    unset EXT
    unset CONDA_HELP
    unset CONDA_VERBOSE
    if [ "${UNKNOWN}" != "" ]; then
        unset UNKNOWN
        return 1
    else
        unset UNKNOWN
        return 0
    fi
fi
unset _SHELL
unset EXT
unset CONDA_HELP
unset UNKNOWN

######################################################################
# determine if there is anything to deactivate and deactivate
# accordingly
######################################################################
if [ -n "${CONDA_PATH_BACKUP}" ]; then
    # unload post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
    _CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
    if [ -d "${_CONDA_DIR}" ]; then
        for f in $(ls "${_CONDA_DIR}" | grep \\.sh$); do
            [ "${CONDA_VERBOSE}" = "true" ] && echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            . "${_CONDA_DIR}/${f}"
        done
    fi
    unset _CONDA_DIR

    # restore PROMPT
    export PS1="${CONDA_PS1_BACKUP}"

    # remove CONDA_DEFAULT_ENV
    unset CONDA_DEFAULT_ENV

    # remove CONDA_PREFIX
    unset CONDA_PREFIX

    # restore PATH
    export PATH="${CONDA_PATH_BACKUP}"

    # remove CONDA_PATH_BACKUP,CONDA_PS1_BACKUP
    unset CONDA_PS1_BACKUP
    unset CONDA_PATH_BACKUP

    if [ -n "${ZSH_VERSION}" ]; then
        # zsh uses rehash
        rehash
    elif [ -n "${BASH_VERSION}" ]; then
        # bash
        hash -r
    else
        # dash uses hash, default
        hash -r
    fi
fi

unset CONDA_VERBOSE

return 0
