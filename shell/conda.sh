

if [ "$_" = "$0" ]; then
    (>&2 echo "This script must be sourced, not executed.")
    exit 1
fi


if [ -z "${_CONDA_EXE}" ]; then
    # hopefully _SCRIPT_DIR has already been set and we can avoid this whole mess
    # it's useful for testing purposes though
    if [ -n "${BASH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=bash
        _SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
    elif [ -n "${ZSH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=zsh
        _SCRIPT_DIR="$(dirname "${funcstack[1]}")"
    elif [ -n "${KSH_VERSION:+x}" ]; then
        _CONDA_SHELL_FLAVOR=ksh
        _SCRIPT_DIR="$(cd "$(dirname "$_")" && echo "$PWD")"
    else
        # https://unix.stackexchange.com/a/120138/92065
        q="$(ps -p$$ -o cmd="",comm="",fname="" 2>/dev/null | sed 's/^-//' | grep -oE '\w+' | head -n1)"
        if [ q = dash ]; then
            _CONDA_SHELL_FLAVOR=dash
        else
            unset __q
            (>&2 echo "Unrecognized shell.")
            return 1
        fi
        unset __q
    fi
    _CONDA_EXE="$_SCRIPT_DIR/../../bin/conda"
fi


_conda_hashr() {
    if [ -n "${ZSH_VERSION:+x}" ]; then
        rehash
    elif [ -n "${POSH_VERSION+x}" ]; then
        # no rehash for POSH
        :
    else
        hash -r
    fi
}


_conda_activate() {
    local ask_conda
    ask_conda="$($_CONDA_EXE shell.activate posix "$@")" || return $?
    eval "$ask_conda"

    if [ "$(echo "$PS1" | awk '{ string=substr($0, 1, 22); print string; }')" != '$CONDA_PROMPT_MODIFIER' ]; then
        PS1='$CONDA_PROMPT_MODIFIER'"$PS1"
    fi

    _conda_hashr
}

_conda_deactivate() {
    local ask_conda
    ask_conda="$($_CONDA_EXE shell.deactivate posix "$@")" || return $?
    eval "$ask_conda"

    if [ -z "$CONDA_PREFIX" ]; then
        PS1=$(echo "$PS1" | awk '{ string=substr($0, 23); print string; }')
    fi

    _conda_hashr
}

_conda_reactivate() {
    local ask_conda
    ask_conda="$($_CONDA_EXE shell.reactivate posix "$@")" || return $?
    eval "$ask_conda"

    _conda_hashr
}


conda() {
    local cmd="$1" && shift
    case "$cmd" in
        activate)
            _conda_activate "$@"
            ;;
        deactivate)
            _conda_deactivate "$@"
            ;;
        install|update|uninstall|remove)
            "$_CONDA_EXE" "$cmd" "$@"
            _conda_reactivate
            ;;
        *)
            "$_CONDA_EXE" "$cmd" "$@"
            ;;
    esac
}


if [ -z "$CONDA_SHLVL" ]; then
    export CONDA_SHLVL=0
fi

