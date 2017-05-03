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
        # https://unix.stackexchange.com/a/120138/92065
        local _q="$(ps -p$$ -o cmd="",comm="",fname="" 2>/dev/null | sed 's/^-//' | grep -oE '\w+' | head -n1)"
        if [ "$_q" = dash ]; then
            _CONDA_SHELL_FLAVOR=dash
        else
            (>&2 echo "Unrecognized shell.")
            return 1
        fi
    fi

    # https://unix.stackexchange.com/questions/4650/determining-path-to-sourced-shell-script/
    local script_dir
    case "$_CONDA_SHELL_FLAVOR" in
        bash) script_dir="$(dirname "${BASH_SOURCE[0]}")";;
        zsh) script_dir="$(dirname "${(%):-%x}")";;  # http://stackoverflow.com/a/28336473/2127762
        dash) x=$(lsof -p $$ -Fn0 | tail -1); script_dir="$(dirname "${x#n}")";;
        *) script_dir="$(cd "$(dirname "$_")" && echo "$PWD")";;
    esac

    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*)
            local bin_dir="Scripts"
            local exe_ext=".exe"
            ;;
        *)
            local bin_dir="bin"
            local exe_ext=""
            ;;
    esac

    local _conda_root="$script_dir/../.."

    _CONDA_EXE="$_conda_root/$bin_dir/conda$exe_ext"

}


_conda_hashr() {
    case "$_CONDA_SHELL_FLAVOR" in
        zsh) rehash;;
        posh) ;;
        *) hash -r;;
    esac
}


_conda_activate() {
    local ask_conda
    ask_conda="$("$_CONDA_EXE" shell.posix activate "$@")" || return $?
    eval "$ask_conda"

    case "$_CONDA_SHELL_FLAVOR" in
        dash)
            if [ "$(echo "$PS1" | awk '{ string=substr($0, 1, 22); print string; }')" != '$CONDA_PROMPT_MODIFIER' ]; then
                PS1='$CONDA_PROMPT_MODIFIER'"$PS1"
            fi
            ;;
        *)
            if [ "${PS1:0:22}" != '$CONDA_PROMPT_MODIFIER' ]; then
                PS1='$CONDA_PROMPT_MODIFIER'"$PS1"
            fi
            ;;
    esac

    _conda_hashr
}

_conda_deactivate() {
    local ask_conda
    ask_conda="$("$_CONDA_EXE" shell.posix deactivate "$@")" || return $?
    eval "$ask_conda"

    if [ -z "$CONDA_PREFIX" ]; then
        case "$_CONDA_SHELL_FLAVOR" in
            dash) PS1=$(echo "$PS1" | awk '{ string=substr($0, 23); print string; }') ;;
            *) PS1=${PS1:22} ;;
        esac
    fi

    _conda_hashr
}

_conda_reactivate() {
    local ask_conda
    ask_conda="$("$_CONDA_EXE" shell.posix reactivate "$@")" || return $?
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


_conda_set_vars

if [ -z "$CONDA_SHLVL" ]; then
    export CONDA_SHLVL=0
fi

