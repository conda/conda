
# Recommended way to make the conda command available in csh is
#   $ sudo ln -s <CONDA_ROOT>/etc/csh/login.d/conda.sh /etc/csh/login.d/conda.sh
# or in ~/.cshrc add the line
#   source <CONDA_ROOT>/etc/csh/login.d/conda.csh

# This block should only be for dev work. Under normal installs, _CONDA_EXE will be templated
# in at the top of this file.
if (! $?_CONDA_EXE) then
  set _CONDA_EXE="${PWD}/shell/bin/conda"
else
  if ("$_CONDA_EXE" == "") then
      set _CONDA_EXE="${PWD}/shell/bin/conda"
  endif
endif

if (`alias conda` == "") then
    if ($?_CONDA_ROOT) then
        alias conda source $_CONDA_ROOT/etc/csh/login.d/conda.csh
    else
        alias conda source $PWD/shell/etc/csh/login.d/conda.csh
    endif
    setenv CONDA_SHLVL 0
    if (! $?prompt) then
        set prompt=""
    endif
else
    switch ( $1 )
        case "activate":
            eval `$_CONDA_EXE shell.csh activate "$2" $argv[3-]`
            rehash
            breaksw
        case "deactivate":
            eval `$_CONDA_EXE shell.csh deactivate "$2" $argv[3-]`
            rehash
            breaksw
        case "install" | "update" | "uninstall" | "remove":
            $_CONDA_EXE $argv[1-]
            eval `$_CONDA_EXE shell.csh reactivate`
            rehash
            breaksw
        default:
            echo "$prompt"
            $_CONDA_EXE $argv[1-]
            breaksw
    endsw
endif
