# Ensure that this script is sourced, not executed
if [ "$_" = "$0" ]; then
    (>&2 echo "This script must be sourced, not executed.")
    exit 1
fi

if [ -n "$BASH_VERSION" ]; then
    _SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
elif [ -n "$ZSH_VERSION" ]; then
    _SCRIPT_DIR="$(dirname "${funcstack[1]}")"
elif [ -n "$KSH_VERSION" ]; then
    _SCRIPT_DIR="$(cd "$(dirname "$_")" && echo "$PWD")"
else
    echo "Only bash and zsh are supported"
    return 1
fi
_CONDA_EXE="$_SCRIPT_DIR/../../bin/conda"


_conda_hashr() {
    [ -z "$BASH_VERSION" ] || hash -r
    [ -z "$ZSH_VERSION" ] || rehash
}


_conda_activate() {
    local ask_conda
    ask_conda="$($_CONDA_EXE shell.activate posix "$@")"
    if not $?; then
        return $?
    fi
    eval "$ask_conda"

    if [ "$(echo "$PS1" | awk '{ string=substr($0, 1, 22); print string; }')" != '$CONDA_PROMPT_MODIFIER' ]; then
        PS1='$CONDA_PROMPT_MODIFIER'"$PS1"
    fi

    _conda_hashr
}

_conda_deactivate() {
    eval "$($_CONDA_EXE shell.deactivate posix "$@")"

    if [ -z "$CONDA_PREFIX" ]; then
        PS1=$(echo "$PS1" | awk '{ string=substr($0, 23); print string; }')
    fi

    _conda_hashr
}

_conda_reactivate() {
    eval "$($_CONDA_EXE shell.reactivate posix)"

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
