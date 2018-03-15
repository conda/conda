_conda_set_vars() {
    # set _CONDA_SHELL_FLAVOR
    if [ -n "${BASH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=bash
    elif [ -n "${ZSH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=zsh
    elif [ -n "${KSH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=ksh
    elif [ -n "${POSH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=posh
    else
        # default to dash; if we run into a problem here, please raise an issue
        _CONDA_SHELL_FLAVOR=dash
    fi

    if [ -z "${_CONDA_EXE+x}" ]; then
        if [ -n "${_CONDA_ROOT:+x}" ]; then
            # typically this should be for dev only; _CONDA_EXE should be written at top of file
            # for normal installs
            _CONDA_EXE="$_CONDA_ROOT/conda/shell/bin/conda"
        fi
        if ! [ -f "${_CONDA_EXE-x}" ]; then
            _CONDA_EXE="$PWD/conda/shell/bin/conda"
        fi
    fi

    # We're not allowing PS1 to be unbound. It must at least be set.
    # However, we're not exporting it, which can cause problems when starting a second shell
    # via a first shell (i.e. starting zsh from bash).
    if [ -z "${PS1+x}" ]; then
        PS1=
    fi

}


_conda_hashr() {
    case "$_CONDA_SHELL_FLAVOR" in
        zsh) \rehash;;
        posh) ;;
        *) \hash -r;;
    esac
}


_conda_activate() {
    if [ -n "${CONDA_PS1_BACKUP:+x}" ]; then
        # Handle transition from shell activated with conda <= 4.3 to a subsequent activation
        # after conda updated to >= 4.4. See issue #6173.
        PS1="$CONDA_PS1_BACKUP"
        \unset CONDA_PS1_BACKUP
    fi

    \local ask_conda
    ask_conda="$(PS1="$PS1" $_CONDA_EXE shell.posix activate "$@")" || \return $?
    \eval "$ask_conda"

    _conda_hashr
}

_conda_deactivate() {
    \local ask_conda
    ask_conda="$(PS1="$PS1" $_CONDA_EXE shell.posix deactivate "$@")" || \return $?
    \eval "$ask_conda"

    _conda_hashr
}

_conda_reactivate() {
    \local ask_conda
    ask_conda="$(PS1="$PS1" $_CONDA_EXE shell.posix reactivate)" || \return $?
    \eval "$ask_conda"

    _conda_hashr
}


conda() {
    if [ "$#" -lt 1 ]; then
        $_CONDA_EXE
    else
        \local cmd="$1"
        shift
        case "$cmd" in
            activate)
                _conda_activate "$@"
                ;;
            deactivate)
                _conda_deactivate "$@"
                ;;
            install|update|uninstall|remove)
                $_CONDA_EXE "$cmd" "$@" && _conda_reactivate
                ;;
            *)
                $_CONDA_EXE "$cmd" "$@"
                ;;
        esac
    fi
}


_conda_set_vars

if [ -z "${CONDA_SHLVL+x}" ]; then
    \export CONDA_SHLVL=0
fi

