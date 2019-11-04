# In dev-mode CONDA_EXE is python.exe and on Windows
# it is in a different relative location to condabin.
if [ -n "${_CE_CONDA}" -a -n "${WINDIR-}" ]; then
    CONDA_ETC=$(\dirname "${CONDA_EXE}")/etc
else
    CONDA_ETC=$(\dirname "${CONDA_EXE}")
    CONDA_ETC=$(\dirname "${CONDA_ETC}")/etc
fi

# Load the POSIX setup
. $CONDA_ETC/profile.d/conda.sh

# Load bash-completion library if installed in the base environment by conda.
# (Note: This is a no-op if the system level library has already been loaded).
if [ -r $CONDA_ETC/profile.d/bash_completion.sh -o true ]; then
    . $CONDA_ETC/profile.d/bash_completion.sh

    # Ensure conda share dir is in XDG_DATA_DIRS so completions can get dynamically
    # loaded
    _conda_share_dir=$(\dirname "${CONDA_ETC}")/share
    if ! expr match ":${XDG_DATA_DIRS-}:" ".*:$_conda_share_dir:.*" >/dev/null; then
        XDG_DATA_DIRS=${XDG_DATA_DIRS-}:$_conda_share_dir
    fi
    unset _conda_share_dir
fi

# Check for interactive bash with the bash-completion library loaded
if [ -n "${BASH_VERSION-}" -a -n "${PS1-}" -a -n "${BASH_COMPLETION_VERSINFO-}" ]; then

    # Check for recent enough version of bash.
    if [ ${BASH_VERSINFO[0]} -gt 4 ] || \
       [ ${BASH_VERSINFO[0]} -eq 4 -a ${BASH_VERSINFO[1]} -ge 1 ]; then
        if shopt -q progcomp; then
            . $CONDA_ETC/bash_completion.d/conda
        fi
    fi
fi
