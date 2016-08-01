#!/bin/csh

#
# `source activate` for csh
#

######################################################################
# test if script is sourced
######################################################################
if ( `basename -- "$0"` =~ "*activate*" ) then
    # we are not being sourced
    sh -c 'echo "[ACTIVATE]: ERROR: Must be sourced. Run \`source activate\`." 1>&2'
    if ( -x "/usr/bin/false" ) then
        exec /usr/bin/false
    else
        exec /bin/false
    endif
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
set envname=""

###############################################################################
# parse command line, perform command line error checking
###############################################################################
if ( "$*" != "" ) then
    set num=0
    while ( $num != -1 )
        @ num=($num + 1)
        set arg=`eval eval echo '\$$num'`

        if ( "$arg" == "" ) then
            set num=-1
        else
            switch ( "$arg" )
                case "-h":
                case "--help":
                    set HELP=true
                    breaksw
                default:
                    if ( "$envname" == "" ) then
                        set envname="$arg"
                    else
                        if ( "$UNKNOWN" == "" ) then
                            set UNKNOWN="$arg"
                        else
                            set UNKNOWN="$UNKNOWN $arg"
                        endif
                        set HELP=true
                    endif
                    breaksw
            endsw
        endif
    end
    unset num
    unset arg
endif

if ( "$envname" == "" ) set envname="root"

######################################################################
# help dialog
######################################################################
if ( "$HELP" == true ) then
    if ( "$UNKNOWN" != "" ) then
        sh -c "echo '[ACTIVATE]: ERROR: Unknown/Invalid flag/parameter ($UNKNOWN)' 1>&2"
    endif
    conda ..activate ${_SHELL}${EXT} -h

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
unset HELP
unset UNKNOWN

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${_SHELL}${EXT} "$envname"
if ( $status != 0 ) then
    unset _SHELL
    unset EXT
    exit 1
endif

# store the _SHELL+EXT since it may get cleared by deactivate
set _CONDA_BIN="${_SHELL}${EXT}"

# Ensure we deactivate any scripts from the old env
# be careful since deactivate will unset certain values (like $_SHELL and $EXT)
# beware of csh's `which` checking $PATH and aliases for matches
# by using \deactivate we will refer to the "root" deactivate not the aliased deactivate if it exists
source "`which \deactivate`" ""

set _CONDA_BIN=`conda ..activate ${_CONDA_BIN} "${envname}" | sed 's| |\ |g'`
if ( $status == 0 ) then
    # CONDA_PATH_BACKUP,CONDA_PROMPT_BACKUP
    # export these to restore upon deactivation
    setenv CONDA_PATH_BACKUP "${PATH}"
    setenv CONDA_path_BACKUP "${path}"
    setenv CONDA_PROMPT_BACKUP "${prompt}"

    # PATH
    # update path with the new conda environment
    # csh/tcsh are fun since they have two path variables,
    # in theory they are supposed to reflect each other at
    # all times but due to the CONDA_BIN possibly containing
    # a space in the pathname then the paths aren't properly
    # updated when one is changed and instead we must manually
    # update both, yes this may cause issues for the user if
    # they decide to alter the path while inside a conda
    # environment

    set path=(${_CONDA_BIN} ${path})
    set PATH=(${_CONDA_BIN}:${PATH})

    # CONDA_PREFIX
    # always the full path to the activated environment
    # is not set when no environment is active
    setenv CONDA_PREFIX `echo "${_CONDA_BIN}" | sed 's|/bin$||' | sed 's| |\ |g'`

    # CONDA_DEFAULT_ENV
    # the shortest representation of how conda recognizes your env
    # can be an env name, or a full path (if the string contains / it's a path)
    if ( "$envname" =~ "*/*" ) then
        set d=`dirname "${envname}"`
        set d=`cd "${d}" && pwd`
        set f=`basename "${envname}"`
        setenv CONDA_DEFAULT_ENV "${d}/${f}"
        unset d
        unset f
    else
        setenv CONDA_DEFAULT_ENV "$envname"
    endif

    # PROMPT
    # customize the prompt to show what environment has been activated
    if ( `conda ..changeps1` == "1" ) then
        set prompt="(${CONDA_DEFAULT_ENV}) $prompt"
    endif

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/activate.d"
    if ( -d "${_CONDA_DIR}" ) then
        foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
            source "${_CONDA_DIR}/${f}"
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
