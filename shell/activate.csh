#!/bin/csh

#
# source "`which activate`" for c-shell
#

###############################################################################
# local vars
###############################################################################
# keep track of WHAT_SHELL_AM_I to communicate properly with `conda ..activate`
set TRUE=0
set FALSE=1
set WHAT_SHELL_AM_I="csh"
switch ( `uname -s` )
    case "CYGWIN*":
    case "MINGW*":
    case "MSYS*":
        set WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}.exe"
        setenv MSYS2_ENV_CONV_EXCL "CONDA_PATH"
        breaksw
endsw

# note whether or not the CONDA_* variables are exported, if so we need to
# preserve that status
set IS_ENV_CONDA_HELP="${FALSE}"
set IS_ENV_CONDA_VERBOSE="${FALSE}"
set IS_ENV_CONDA_ENVNAME="${FALSE}"
if ( `env | grep CONDA_HELP` != "" ) then
    set IS_ENV_CONDA_HELP="${TRUE}"
endif
if ( `env | grep CONDA_VERBOSE` != "" ) then
    set IS_ENV_CONDA_VERBOSE="${TRUE}"
endif
if ( `env | grep CONDA_ENVNAME` != "" ) then
    set IS_ENV_CONDA_ENVNAME="${TRUE}"
endif

# inherit whatever the user set
# this is important for dash where you cannot pass parameters to sourced scripts
# since this script is exclusively for csh/tcsh this is just for consistency/a bonus feature
if ( ! "$?CONDA_HELP" ) then
    set CONDA_HELP="${FALSE}"
else if ( "${CONDA_HELP}" == "false" || "${CONDA_HELP}" == "FALSE" || "${CONDA_HELP}" == "False") then
    set CONDA_HELP="${FALSE}"
else if ( "${CONDA_HELP}" == "true" || "${CONDA_HELP}" == "TRUE" || "${CONDA_HELP}" == "True" ) then
    set CONDA_HELP="${TRUE}"
endif
set UNKNOWN=""
if ( ! "$?CONDA_VERBOSE" ) then
    set CONDA_VERBOSE="${FALSE}"
else if ( "${CONDA_VERBOSE}" == "false" || "${CONDA_VERBOSE}" == "FALSE" || "${CONDA_VERBOSE}" == "False") then
    set CONDA_VERBOSE="${FALSE}"
else if ( "${CONDA_VERBOSE}" == "true" || "${CONDA_VERBOSE}" == "TRUE" || "${CONDA_VERBOSE}" == "True" ) then
    set CONDA_VERBOSE="${TRUE}"
endif
if ( ! "$?CONDA_ENVNAME" ) then
    set CONDA_ENVNAME=""
endif

###############################################################################
# parse command line, perform command line error checking
###############################################################################
set num=0
set is_envname_set="${FALSE}"
while ( $num != -1 )
    @ num = ($num + 1)
    set arg=`eval eval echo '\${$num}'`

    # use == "" instead of -z test for robust support across
    # different platforms (especially Ubuntu)
    if ( $status != 0 || "`echo ${arg} | sed 's| ||g'`" == "" ) then
        set num=-1
    else
        switch ( "${arg}" )
            case "-h":
            case "--help":
                set CONDA_HELP="${TRUE}"
                breaksw
            case "-v":
            case "--verbose":
                set CONDA_VERBOSE="${TRUE}"
                breaksw
            default:
                if ( "${is_envname_set}" == "${FALSE}" ) then
                    set CONDA_ENVNAME="${arg}"
                    set is_envname_set="${TRUE}"
                else
                    # use == "" instead of -z test for robust support across
                    # different platforms (especially Ubuntu)
                    if ( "${UNKNOWN}" == "" ) then
                        set UNKNOWN="${arg}"
                    else
                        set UNKNOWN="${UNKNOWN} ${arg}"
                    endif
                    set CONDA_HELP="${TRUE}"
                endif
                breaksw
        endsw
    endif
end
unset num
unset arg
unset is_envname_set

# if any of these variables are undefined (i.e. unbounded) set them to a default
#
# use == "" instead of -z test for robust support across
# different platforms (especially Ubuntu)
if ( "`echo ${CONDA_HELP} | sed 's| ||g'`" == "" ) then
    set CONDA_HELP="${FALSE}"
endif
if ( "`echo ${CONDA_VERBOSE} | sed 's| ||g'`" == "" ) then
    set CONDA_VERBOSE="${FALSE}"
endif
if ( "`echo ${CONDA_ENVNAME} | sed 's| ||g'`" == "" ) then
    set CONDA_ENVNAME="root"
endif

# export CONDA_* variables as necessary
if ( "${IS_ENV_CONDA_ENVNAME}" == "${TRUE}" ) then
    setenv CONDA_ENVNAME "${CONDA_ENVNAME}"
endif
if ( "${IS_ENV_CONDA_HELP}" == "${TRUE}" ) then
    setenv CONDA_HELP "${CONDA_HELP}"
endif
if ( "${IS_ENV_CONDA_VERBOSE}" == "${TRUE}" ) then
    setenv CONDA_VERBOSE "${CONDA_VERBOSE}"
endif

######################################################################
# help dialog
######################################################################
if ( "${CONDA_HELP}" == "${TRUE}" ) then
    conda ..activate ${WHAT_SHELL_AM_I} -h ${UNKNOWN}

    unset WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_ENVNAME}" == "${FALSE}" ) then
        unset CONDA_ENVNAME
    endif
    if ( "${IS_ENV_CONDA_HELP}" == "${FALSE}" ) then
        unset CONDA_HELP
    endif
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_HELP
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    # use != "" instead of -n test for robust support across
    # different platforms (especially Ubuntu)
    if ( "${UNKNOWN}" != "" ) then
        unset UNKNOWN
        exit 1
    else
        unset UNKNOWN
        exit 0
    endif
endif
if ( "${IS_ENV_CONDA_HELP}" == "${FALSE}" ) then
    unset CONDA_HELP
endif
unset IS_ENV_CONDA_HELP
unset UNKNOWN

######################################################################
# configure virtual environment
######################################################################
conda ..checkenv ${WHAT_SHELL_AM_I} "${CONDA_ENVNAME}"
if ( $status != 0 ) then
    unset WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_ENVNAME}" == "${FALSE}" ) then
        unset CONDA_ENVNAME
    endif
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    exit 1
endif

# store remaining values that may get cleared by deactivate
set _CONDA_WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}"
set _CONDA_VERBOSE="${CONDA_VERBOSE}"
set _IS_ENV_CONDA_VERBOSE="${IS_ENV_CONDA_VERBOSE}"

# ensure we deactivate any scripts from the old env
# beware of csh's `which` checking $PATH and aliases for matches
# by using \deactivate we will refer to the "root" deactivate not the aliased deactivate if it exists
source "`which \deactivate.csh`" ""

# restore boolean
set TRUE=0
set FALSE=1

# restore values
set IS_ENV_CONDA_VERBOSE="${_IS_ENV_CONDA_VERBOSE}"
set CONDA_VERBOSE="${_CONDA_VERBOSE}"
set WHAT_SHELL_AM_I="${_CONDA_WHAT_SHELL_AM_I}"
unset _IS_ENV_CONDA_VERBOSE
unset _CONDA_VERBOSE
unset _CONDA_WHAT_SHELL_AM_I

set _CONDA_BIN=`conda ..activate ${WHAT_SHELL_AM_I} "${CONDA_ENVNAME}" | sed 's| |\ |g'`
if ( $status == 0 ) then
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
    unset tmp_path
    unset tmp_PATH

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

    # PROMPT & CONDA_PS1_BACKUP
    # export PROMPT to restore upon deactivation
    # customize the prompt to show what environment has been activated
    if ( `conda ..changeps1` == 1 && $?prompt ) then
        setenv CONDA_PS1_BACKUP "${prompt}"
        set prompt="(${CONDA_DEFAULT_ENV}) ${prompt}"
    endif

    # load post-activate scripts
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/activate.d"
    if ( -d "${_CONDA_DIR}" ) then
        foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
            if ( "${CONDA_VERBOSE}" == "${TRUE}" ) then
                echo "[ACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
            endif
            source "${_CONDA_DIR}/${f}"
        end
    endif
    unset _CONDA_DIR

    # csh/tcsh both use rehash
    rehash

    unset WHAT_SHELL_AM_I
    unset _CONDA_BIN
    if ( "${IS_ENV_CONDA_ENVNAME}" == "${FALSE}" ) then
        unset CONDA_ENVNAME
    endif
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    exit 0
else
    unset WHAT_SHELL_AM_I
    unset _CONDA_BIN
    if ( "${IS_ENV_CONDA_ENVNAME}" == "${FALSE}" ) then
        unset CONDA_ENVNAME
    endif
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
    unset IS_ENV_CONDA_ENVNAME
    unset IS_ENV_CONDA_VERBOSE
    unset TRUE
    unset FALSE
    exit 1
endif
