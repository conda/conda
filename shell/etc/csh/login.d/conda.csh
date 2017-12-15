# alias conda source $PWD/shell/etc/csh/login.d/conda.csh

set _CONDA_EXE="${PWD}/shell/bin/conda"

switch ( $1 )
    case "activate":
        eval `$_CONDA_EXE shell.csh activate $argv[2-]`
        rehash
        breaksw
    case "deactivate":
        eval `$_CONDA_EXE shell.csh deactivate $argv[2-]`
        rehash
        breaksw
    case "install" | "update" | "uninstall" | "remove":
        $_CONDA_EXE $argv[1-]
        eval `$_CONDA_EXE shell.csh reactivate`
        rehash
        breaksw
    default:
        $_CONDA_EXE $argv[1-]
        breaksw
endsw
