#!/bin/csh

#
# source "`which activate`" for c-shell
#

###############################################################################
# local vars
###############################################################################
set _SHELL="csh"
switch ( `uname -s` )
    case "CYGWIN*":
    case "MINGW*":
    case "MSYS*":
        set EXT=".exe"
        setenv MSYS2_ENV_CONV_EXCL "CONDA_PATH"
        breaksw
    default:
        set EXT=""
        breaksw
endsw

# inherit whatever the user set
# this is important for dash where you cannot pass parameters to sourced scripts
# since this script is exclusively for csh/tcsh this is just for consistency/a bonus feature
if ( ! $?CONDA_HELP ) set CONDA_HELP=false
set UNKNOWN=""
if ( ! $?CONDA_VERBOSE ) set CONDA_VERBOSE=false
if ( ! $?CONDA_ENVNAME ) set CONDA_ENVNAME=""

###############################################################################
# parse command line, perform command line error checking
###############################################################################
set num=0
set is_envname_set=false
while ( $num != -1 )
    @ num = ($num + 1)
    set arg=`eval eval echo '\${$num}'`

    if ( -z `echo "${arg}" | sed 's| ||g'` ) then
        set num=-1
    else
        switch ( "${arg}" )
            case "-h":
            case "--help":
                set CONDA_HELP=true
                breaksw
            case "-v":
            case "--verbose":
                set CONDA_VERBOSE=true
                breaksw
            default:
                if ( "${is_envname_set}" == false ) then
                    set CONDA_ENVNAME="${arg}"
                    set is_envname_set=true
                else
                    if ( -z "${UNKNOWN}" ) then
                        set UNKNOWN="${arg}"
                    else
                        set UNKNOWN="${UNKNOWN} ${arg}"
                    endif
                    set CONDA_HELP=true
                endif
                breaksw
        endsw
    endif
end
unset num
unset arg
unset is_envname_set

# if any of these variables are undefined (i.e. unbounded) set them to a default
if ( -z `echo "${CONDA_HELP}" | sed 's| ||g'` ) set CONDA_HELP=false
if ( -z `echo "${CONDA_VERBOSE}" | sed 's| ||g'` ) set CONDA_VERBOSE=false
if ( -z `echo "${CONDA_ENVNAME}" | sed 's| ||g'` ) set CONDA_ENVNAME="root"

######################################################################
# help dialog
######################################################################
if ( "${CONDA_HELP}" == true ) then
    if ( -n "${UNKNOWN}" ) then
        sh -c "echo '[ACTIVATE]: ERROR: Unknown/Invalid flag/parameter (${UNKNOWN})' 1>&2"
    endif
    conda ..activate ${_SHELL}${EXT} -h

    unset _SHELL
    unset EXT
    unset CONDA_ENVNAME
    unset CONDA_HELP
    unset CONDA_VERBOSE
    if ( -n "${UNKNOWN}" ) then
        unset UNKNOWN
        exit 1
    else
        unset UNKNOWN
        exit 0
    endif
endif
unset CONDA_HELP
unset UNKNOWN

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${_SHELL}${EXT} "${CONDA_ENVNAME}"
if ( $status != 0 ) then
    unset _SHELL
    unset EXT
    unset CONDA_ENVNAME
    unset CONDA_VERBOSE
    exit 1
endif

# store the _SHELL+EXT since it may get cleared by deactivate
# store the CONDA_VERBOSE since it may get cleared by deactivate
set _CONDA_BIN="${_SHELL}${EXT}"
set CONDA_VERBOSE_TMP="${CONDA_VERBOSE}"

# Ensure we deactivate any scripts from the old env
# be careful since deactivate will unset certain values (like $_SHELL and $EXT)
# beware of csh's `which` checking $PATH and aliases for matches
# by using \deactivate we will refer to the "root" deactivate not the aliased deactivate if it exists
source "`which \deactivate.csh`" ""

# restore CONDA_VERBOSE
set CONDA_VERBOSE="${CONDA_VERBOSE_TMP}"
unset CONDA_VERBOSE_TMP

set _CONDA_BIN=`conda ..activate ${_CONDA_BIN} "${CONDA_ENVNAME}" | sed 's| |\ |g'`
if ( $status == 0 ) then
    # CONDA_PS1_BACKUP
    # export these to restore upon deactivation
    if ( $?prompt ) setenv CONDA_PS1_BACKUP "${prompt}"

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
    #
    # use tmp_path/tmp_PATH to avoid cases when path setting
    # succeeds and is parsed correctly from one to the other
    # when not using the tmp* values would result in
    # CONDA_PREFIX being added twice to PATH
    set tmp_path="$path"
    set tmp_PATH="$PATH"
    set path=(${_CONDA_BIN} ${tmp_path})
    set PATH=(${_CONDA_BIN}:${tmp_PATH})
    unset tmp_path tmp_PATH

    # CONDA_PREFIX
    # always the full path to the activated environment
    # is not set when no environment is active
    setenv CONDA_PREFIX `echo "${_CONDA_BIN}" | sed 's|/bin$||' | sed 's| |\ |g'`

    # CONDA_DEFAULT_ENV
    # the shortest representation of how conda recognizes your env
    # can be an env name, or a full path (if the string contains / it's a path)
    if ( `echo "${CONDA_ENVNAME}" | awk '{exit(match($0,/.*\/.*/) != 0)}'` ) then
        set d=`dirname "${CONDA_ENVNAME}"`
        set d=`cd "${d}" && pwd`
        set f=`basename "${CONDA_ENVNAME}"`
        setenv CONDA_DEFAULT_ENV "${d}/${f}"
        unset d
        unset f
    else
        setenv CONDA_DEFAULT_ENV "${CONDA_ENVNAME}"
    endif

    # PROMPT
    # customize the prompt to show what environment has been activated
    if ( `conda ..changeps1` == 1 && $?prompt ) then
        set prompt="(${CONDA_DEFAULT_ENV}) ${prompt}"
    endif

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/activate.d"
    if ( -d "${_CONDA_DIR}" ) then
        foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
            if ( "${CONDA_VERBOSE}" == true ) echo "[ACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            source "${_CONDA_DIR}/${f}"
        end
    endif

    # csh/tcsh both use rehash
    rehash

    unset _SHELL
    unset EXT
    unset CONDA_ENVNAME
    unset CONDA_VERBOSE
    unset _CONDA_BIN
    unset _CONDA_DIR
    exit 0
else
    unset _SHELL
    unset EXT
    unset CONDA_ENVNAME
    unset CONDA_VERBOSE
    unset _CONDA_BIN
    exit 1
endif
