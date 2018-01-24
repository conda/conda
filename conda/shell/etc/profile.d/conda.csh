
# Recommended way to make the conda command available in csh is
#   $ sudo ln -s <CONDA_ROOT>/etc/profile.d/conda.csh /etc/profile.d/conda.csh
# or in ~/.cshrc add the line
#   source <CONDA_ROOT>/etc/profile.d/conda.csh

# This block should only be for dev work. Under normal installs, _CONDA_EXE will be templated
# in at the top of this file.
if (! $?_CONDA_EXE) then
  set _CONDA_EXE="${PWD}/conda/shell/bin/conda"
else
  if ("$_CONDA_EXE" == "") then
      set _CONDA_EXE="${PWD}/conda/shell/bin/conda"
  endif
endif

if (`alias conda` == "") then
    if ($?_CONDA_ROOT) then
        alias conda source $_CONDA_ROOT/etc/profile.d/conda.csh
    else
        alias conda source $PWD/conda/shell/etc/profile.d/conda.csh
    endif
    setenv CONDA_SHLVL 0
    if (! $?prompt) then
        set prompt=""
    endif
else
    switch ( $1 )
        case "activate":
            set noglob
            eval `$_CONDA_EXE shell.csh activate "$2" $argv[3-]`
            unset noglob
            rehash
            if ( -e "$CONDA_PREFIX/etc/activate.d" ) then
                set nonomatch=1
                set conda_autoexec_scripts = ( $CONDA_PREFIX/etc/activate.d/*.csh )
                if ( -e $conda_autoexec_scripts[1] ) then
                    foreach script ( $conda_autoexec_scripts )
                        source "$script"
                    end
                endif
                unset conda_autoexec_scripts
                unset nonomatch
            endif
            breaksw
        case "deactivate":
            set noglob
            eval `$_CONDA_EXE shell.csh deactivate "$2" $argv[3-]`
            unset noglob
            rehash
            if ( -e "$CONDA_PREFIX/etc/deactivate.d" ) then
                set nonomatch=1
                set conda_autoexec_scripts = ( $CONDA_PREFIX/etc/deactivate.d/*.csh )
                if ( -e $conda_autoexec_scripts[1] ) then
                    foreach script ( $conda_autoexec_scripts )
                        source "$script"
                    end
                endif
                unset conda_autoexec_scripts
                unset nonomatch
            endif
            breaksw
        case "install" | "update" | "uninstall" | "remove":
            set noglob
            $_CONDA_EXE $argv[1-]
            eval `$_CONDA_EXE shell.csh reactivate`
            unset noglob
            rehash
            breaksw
        default:
            set noglob
            $_CONDA_EXE $argv[1-]
            unset noglob
            breaksw
    endsw
endif
