# This file should be sourced by bash or zsh.  It should not itself be executed.


_conda_hashr() {
    [[ -z $BASH_VERSION ]] || hash -r
    [[ -z $ZSH_VERSION ]] || rehash
}


_conda_env_exists() {
    _env_location="$(conda-env-helper find_env_location $1)"
    test -n "$_env_location"
}


_conda_currently_in_env() {
    test -n "$CONDA_DEFAULT_ENV"
}


_conda_activate() {
    if _conda_currently_in_env; then
        _conda_deactivate
    fi
    if _conda_env_exists "$1"; then
        echo "found $_env_location"
        echo "activating"
        source activate "$_env_location"
    else
        echo "creating"
        # create
    fi
    _conda_hashr
}


_conda_deactivate() {
    echo "deactivating $CONDA_DEFAULT_ENV"
    source deactivate
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
        *)
            CONDA="$(which conda)"
            $CONDA "$cmd" "$@"
            ;;
    esac
}
