# Load the POSIX setup
. $_CONDA_ROOT/shell/etc/profile.d/conda.sh

# Check for interactive bash with bash_completion setup
if [ -n "${BASH_VERSION-}" -a -n "${PS1-}" -a -n "${BASH_COMPLETION_VERSINFO-}" ]; then

    # Check for recent enough version of bash.
    if [ ${BASH_VERSINFO[0]} -gt 4 ] || \
       [ ${BASH_VERSINFO[0]} -eq 4 -a ${BASH_VERSINFO[1]} -ge 1 ]; then

        . $_CONDA_ROOT/shell/etc/bash_completion.d/conda
    fi
fi
