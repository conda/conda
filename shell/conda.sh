# This file should be sourced by bash or zsh.  It should not itself be executed.

# This file is WIP
# For now, to test, try something like `source shell/conda.sh && conda activate /my/env`

_conda_hashr() {
    [[ -z $BASH_VERSION ]] || hash -r
    [[ -z $ZSH_VERSION ]] || rehash
}


_conda_activate() {
    while read -r line; do
        eval "$line"
    done < <(python -m conda.activate activate posix "$@")

    if [ "${PS1:0:22}" != '$CONDA_PROMPT_MODIFIER' ]; then
        PS1='$CONDA_PROMPT_MODIFIER'"$PS1"
    fi

    _conda_hashr
}

_conda_deactivate() {
    while read -r line; do
        eval "$line"
    done < <(python -m conda.activate deactivate posix "$@")

    if [ -z "$CONDA_PREFIX" ]; then
        PS1=${PS1:22}
    fi

    _conda_hashr
}

_conda_reactivate() {
    while read -r line; do
        eval "$line"
    done < <(python -m conda.activate reactivate posix "$@")

    _conda_hashr
}


conda() {
    local cmd="$1" && shift
    case "$cmd" in
        activate)
            _conda_activate "$@"
            ;;
        deactivate)
            _conda_deactivate
            ;;
        install | update | uninstall | remove)
            CONDA="$(which conda)"
            "$CONDA" "$cmd" "$@"
            _conda_reactivate
            ;;
        *)
            CONDA="$(which conda)"
            "$CONDA" "$cmd" "$@"
            ;;
    esac
}
