#!/bin/sh

#
# . deactivate for bourne-shell
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
                # if it is undefined (check if unbounded) and if it is zero
                if [ -z "${UNKNOWN+x}" ] || [ -z "${UNKNOWN}" ]; then
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

# if any of these variables are undefined (i.e. unbounded) set them to a default
[ -z "${CONDA_HELP+x}" ] && CONDA_HELP=false
[ -z "${CONDA_VERBOSE+x}" ] && CONDA_VERBOSE=false

######################################################################
# help dialog
######################################################################
if [ "${CONDA_HELP}" = true ]; then
    # if it is defined (check if unbounded) and if it is non-zero
    if [ -n "${UNKNOWN+x}" ] && [ -n "${UNKNOWN}" ]; then
        echo "[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter (${UNKNOWN})" 1>&2
    fi
    conda ..deactivate ${WHAT_SHELL_AM_I} -h

    unset WHAT_SHELL_AM_I
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
unset WHAT_SHELL_AM_I
unset CONDA_HELP
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
            [ "${CONDA_VERBOSE}" = "true" ] && echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            . "${_CONDA_DIR}/${f}"
        done
    fi
    unset _CONDA_DIR

    # restore PROMPT
    [ -n "${PS1+x}" ] && export PS1="${CONDA_PS1_BACKUP}"

    # remove CONDA_DEFAULT_ENV
    unset CONDA_DEFAULT_ENV

    # remove only first instance of CONDA_PREFIX from PATH
    export PATH=$(envvar_cleanup.sh "${PATH}" -r "${CONDA_PREFIX}/bin")

    # remove CONDA_PREFIX
    unset CONDA_PREFIX

    # remove CONDA_PS1_BACKUP
    unset CONDA_PS1_BACKUP

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

unset CONDA_VERBOSE

return 0
