
# Recommended way to make the conda command available in csh is
# $ sudo ln -s <CONDA_ROOT>/etc/csh/login.d/conda.sh /etc/csh/login.d/conda.sh

# This block should only be for dev work. Under normal installs, _CONDA_EXE will be templated
# in at the top of this file.
if (! $?var) then
  setenv _CONDA_EXE "${PWD}/shell/bin/conda"
else
  if ("$var" == "")  then
      setenv _CONDA_EXE "${PWD}/shell/bin/conda"
  endif
endif

set _CONDA_EXE="${PWD}/shell/bin/conda"

if ( $0 == "conda" ) then
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
else
  alias conda source $PWD/shell/etc/csh/login.d/conda.csh
endif
