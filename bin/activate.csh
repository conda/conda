#!/bin/csh

#
# `source activate` for csh
#

######################################################################
# test if script is sourced
######################################################################
if ( `basename -- "$0"` =~ "*activate*" ) then
    # we are not being sourced
    echo '[ACTIVATE]: ERROR: Must be sourced. Run `source activate`.'
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
set envname="root"

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
            set envname="$arg"
            breaksw
    endsw
end
unset args
unset arg

######################################################################
# help dialog
######################################################################
if ( "$HELP" == true ) then
    conda ..activate ${_SHELL}${EXT} -h

    unset _SHELL
    unset EXT
    unset HELP
    exit 0
endif
unset HELP

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${_SHELL}${EXT} "$envname"
if ( $status != 0 ) then
    unset _SHELL
    unset EXT
    exit 1
endif

# configure the command to run to get the conda bin
set _CONDA_BIN="conda ..activate ${_SHELL}${EXT} ${envname}"

# Ensure we deactivate any scripts from the old env
# be careful since deactivate will unset certain values (like $_SHELL and $EXT)
# beware of csh's `which` checking $PATH and aliases for matches
source `which \deactivate` ""

set _CONDA_BIN=`${_CONDA_BIN}`
if ( $status == 0 ) then
    # CONDA_PATH_BACKUP,CONDA_PROMPT_BACKUP
    # export these to restore upon deactivation
    setenv CONDA_PATH_BACKUP "${PATH}"
    setenv CONDA_PROMPT_BACKUP "${prompt}"

    # PATH
    # update path with the new conda environment
    setenv PATH "${_CONDA_BIN}:${PATH}"

    # CONDA_PREFIX
    # always the full path to the activated environment
    # is not set when no environment is active
    setenv CONDA_PREFIX `echo ${_CONDA_BIN} | sed 's|/bin$||' >& /dev/null`

    # CONDA_DEFAULT_ENV
    # the shortest representation of how conda recognizes your env
    # can be an env name, or a full path (if the string contains / it's a path)
    if ( "$envname" =~ "*/*" ) then
        setenv CONDA_DEFAULT_ENV `get_abs_filename "$envname"`
    else
        setenv CONDA_DEFAULT_ENV "$envname"
    endif

    # PROMPT
    # customize the prompt to show what environment has been activated
    if ( `conda ..changeps1` == "1" ) then
        echo "$prompt" | grep -q CONDA_DEFAULT_ENV >& /dev/null
        if ( $status != 0 ) then
            set prompt="(${CONDA_DEFAULT_ENV}) $prompt"
        endif
    endif

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    set _CONDA_DIR="$CONDA_PREFIX/etc/conda/activate.d"
    if ( -d "${_CONDA_DIR}" ) then
        foreach f ( `find "${_CONDA_DIR}" -iname "*.sh"` )
            source "$f"
        end
    endif

    # csh/tcsh both use rehash
    rehash

    unset _SHELL
    unset EXT
    unset envname
    unset _CONDA_BIN
    unset _CONDA_DIR

    exit 0
else
    unset _SHELL
    unset EXT
    unset envname
    unset _CONDA_BIN
    exit 1
endif
