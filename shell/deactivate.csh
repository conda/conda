#!/bin/csh

#
# `source deactivate` for csh
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
        setenv MSYS2_ENV_CONV_EXCL CONDA_PATH
        # ignore any windows backup paths from bat-based activation
        if ( `echo "${CONDA_PATH_BACKUP}" | awk '{exit(match($0,/\/.*/) != 0)}'` ) then
           unset CONDA_PATH_BACKUP
        endif
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

###############################################################################
# parse command line, perform command line error checking
###############################################################################
set num=0
while ( $num != -1 )
    @ num = ($num + 1)
    set arg=`eval eval echo '\$$num'`

    if ( `echo "${arg}" | sed 's| ||g'` == "" ) then
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
                if ( "${UNKNOWN}" == "" ) then
                    set UNKNOWN="${arg}"
                else
                    set UNKNOWN="${UNKNOWN} ${arg}"
                endif
                set CONDA_HELP=true
                breaksw
        endsw
    endif
end
unset num
unset arg

if ( `echo "${CONDA_HELP}" | sed 's| ||g'` == "" ) set CONDA_HELP=false
if ( `echo "${CONDA_VERBOSE}" | sed 's| ||g'` == "" ) set CONDA_VERBOSE=false

######################################################################
# help dialog
######################################################################
if ( "${CONDA_HELP}" == true ) then
    if ( "${UNKNOWN}" != "" ) then
        sh -c "echo '[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter (${UNKNOWN})' 1>&2"
    endif
    conda ..deactivate ${_SHELL}${EXT} -h

    unset _SHELL
    unset EXT
    unset CONDA_HELP
    unset CONDA_VERBOSE
    if ( "${UNKNOWN}" != "" ) then
        unset UNKNOWN
        exit 1
    else
        unset UNKNOWN
        exit 0
    endif
endif
unset _SHELL
unset EXT
unset CONDA_HELP
unset UNKNOWN

######################################################################
# determine if there is anything to deactivate and deactivate
# accordingly
######################################################################
if ( $?CONDA_PATH_BACKUP ) then
    if ( "${CONDA_PATH_BACKUP}" != "" ) then
        # unload post-activate scripts
        # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
        set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
        if ( -d "${_CONDA_DIR}" ) then
            foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
                if ( "${CONDA_VERBOSE}" == true ) echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
                source "${_CONDA_DIR}/${f}"
            end
        endif
        unset _CONDA_DIR

        # restore PROMPT
        set prompt="${CONDA_PS1_BACKUP}"

        # remove CONDA_DEFAULT_ENV
        unsetenv CONDA_DEFAULT_ENV

        # remove CONDA_PREFIX
        unsetenv CONDA_PREFIX

        # restore PATH
        set path=(${CONDA_path_BACKUP})
        set PATH=(${CONDA_PATH_BACKUP})

        # remove CONDA_PATH_BACKUP,CONDA_PS1_BACKUP
        unsetenv CONDA_PS1_BACKUP
        unsetenv CONDA_path_BACKUP
        unsetenv CONDA_PATH_BACKUP

        # csh/tcsh both use rehash
        rehash
    endif
endif

unset CONDA_VERBOSE

exit 0
