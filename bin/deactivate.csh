#!/bin/csh

#
# `source deactivate` for csh
#

######################################################################
# test if script is sourced
######################################################################
if ( `basename -- "$0"` =~ "*deactivate*" ) then
    # we are not being sourced
    echo '[DEACTIVATE]: ERROR: Must be sourced. Run `source deactivate`.'
    exec /bin/false
endif

###############################################################################
# local vars
###############################################################################
set _SHELL="csh"
switch ( `uname -s` )
    case "CYGWIN*":
    case "MINGW*":
    case "MSYS*":
        set EXT=".exe"
        setenv MSYS2_ENV_CONV_EXCL CONDA_PATH
        # ignore any windows backup paths from bat-based activation
        if ( "$CONDA_PATH_BACKUP" =~ "/*"  ) then
           unset CONDA_PATH_BACKUP
        endif
        breaksw
    default:
        set EXT=""
        breaksw
endsw

set HELP=false
set UNKNOWN=""

###############################################################################
# parse command line, perform command line error checking
###############################################################################
set args="$*"
foreach arg ( $args )
    switch ($arg)
        case "-h":
        case "--help":
            set HELP=true
            breaksw
        default:
            if ( "$UNKNOWN" == "" ) then
                set UNKNOWN="$arg"
            else
                set UNKNOWN="$UNKNOWN $arg"
            endif
            set HELP=true
            breaksw
    endsw
end
unset args
unset arg

######################################################################
# help dialog
######################################################################
if ( "$HELP" == true ) then
    if ( "$UNKNOWN" != "" ) then
        echo "[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter ($UNKNOWN)"
    endif
    conda ..deactivate ${_SHELL}${EXT} -h

    unset _SHELL
    unset EXT
    unset HELP
    if ( "$UNKNOWN" != "" ) then
        unset UNKNOWN
        exit 1
    else
        unset UNKNOWN
        exit 0
    endif
endif
unset _SHELL
unset EXT
unset HELP
unset UNKNOWN

######################################################################
# determine if there is anything to deactivate and deactivate
# accordingly
######################################################################
if ( $?CONDA_PATH_BACKUP ) then
    # unload post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
    set _CONDA_DIR="$CONDA_PREFIX/etc/conda/deactivate.d"
    if ( -d "${_CONDA_DIR}" ) then
        foreach f ( `find "${_CONDA_DIR}" -iname "*.sh"` )
            source "$f"
        end
    endif
    unset _CONDA_DIR

    # restore PROMPT
    set prompt="$CONDA_PROMPT_BACKUP"

    # remove CONDA_DEFAULT_ENV
    unset CONDA_DEFAULT_ENV

    # remove CONDA_PREFIX
    unset CONDA_PREFIX

    # restore PATH
    setenv PATH "$CONDA_PATH_BACKUP"

    # remove CONDA_PATH_BACKUP,CONDA_PROMPT_BACKUP
    unset CONDA_PROMPT_BACKUP
    unset CONDA_PATH_BACKUP

    # csh/tcsh both use rehash
    rehash
endif

exit 0
