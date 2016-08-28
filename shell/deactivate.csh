#!/bin/csh

#
# source "`which deactivate`" for c-shell
#

###############################################################################
# local vars
###############################################################################
set WHAT_SHELL_AM_I="csh"
switch ( `uname -s` )
    case "CYGWIN*":
    case "MINGW*":
    case "MSYS*":
        set WHAT_SHELL_AM_I="${WHAT_SHELL_AM_I}.exe"
        setenv MSYS2_ENV_CONV_EXCL "CONDA_PATH"
        breaksw
endsw

# inherit whatever the user set
# this is important for dash where you cannot pass parameters to sourced scripts
# since this script is exclusively for csh/tcsh this is just for consistency/a bonus feature
if ( ! $?CONDA_HELP ) then
    set CONDA_HELP=false
endif
set UNKNOWN=""
if ( ! $?CONDA_VERBOSE ) then
    set CONDA_VERBOSE=false
endif

###############################################################################
# parse command line, perform command line error checking
###############################################################################
set num=0
while ( $num != -1 )
    @ num = ($num + 1)
    set arg=`eval eval echo '\$$num'`

    # use == "" instead of -z test for robust support across
    # different platforms (especially Ubuntu)
    if ( $status != 0 || "`echo ${arg} | sed 's| ||g'`" == "" ) then
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
                # use == "" instead of -z test for robust support across
                # different platforms (especially Ubuntu)
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

# if any of these variables are undefined (i.e. unbounded) set them to a default
#
# use == "" instead of -z test for robust support across
# different platforms (especially Ubuntu)
if ( "`echo ${CONDA_HELP} | sed 's| ||g'`" == "" ) then
    set CONDA_HELP=false
endif
if ( "`echo ${CONDA_VERBOSE} | sed 's| ||g'`" == "" ) then
    set CONDA_VERBOSE=false
endif

######################################################################
# help dialog
######################################################################
if ( "${CONDA_HELP}" == true ) then
    # use != "" instead of -n test for robust support across
    # different platforms (especially Ubuntu)
    if ( "${UNKNOWN}" != "" ) then
        bash -c "echo '[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter (${UNKNOWN})' 1>&2"
    endif
    conda ..deactivate ${WHAT_SHELL_AM_I} -h

    unset WHAT_SHELL_AM_I
    unset CONDA_HELP
    unset CONDA_VERBOSE
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
unset WHAT_SHELL_AM_I
unset CONDA_HELP
unset UNKNOWN

######################################################################
# determine if there is anything to deactivate and deactivate
# accordingly
######################################################################
if ( $?CONDA_DEFAULT_ENV ) then
    # use != "" instead of -n test for robust support across
    # different platforms (especially Ubuntu)
    if ( "${CONDA_DEFAULT_ENV}" != "" ) then
        # unload post-activate scripts
        # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
        set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
        if ( -d "${_CONDA_DIR}" ) then
            foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
                if ( "${CONDA_VERBOSE}" == true ) then
                    echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
                endif
                source "${_CONDA_DIR}/${f}"
            end
        endif
        unset _CONDA_DIR

        # restore PROMPT
        if ( $?prompt ) then
            set prompt="${CONDA_PS1_BACKUP}"
        endif

        # remove CONDA_DEFAULT_ENV
        unsetenv CONDA_DEFAULT_ENV

        # remove only first instance of CONDA_PREFIX from PATH
        # use tmp_path/tmp_PATH to avoid cases when path setting
        # succeeds and is parsed correctly from one to the other
        # when not using the tmp* values would result in
        # CONDA_PREFIX being added twice to PATH
        set tmp_path="$path"
        set tmp_PATH="$PATH"
        set path=(`envvar_cleanup.sh "${tmp_path}" -r "${CONDA_PREFIX}/bin" --delim=" "`)
        set PATH=(`envvar_cleanup.sh "${tmp_PATH}" -r "${CONDA_PREFIX}/bin"`)
        unset tmp_path tmp_PATH

        # remove CONDA_PREFIX
        unsetenv CONDA_PREFIX

        # remove CONDA_PS1_BACKUP
        unsetenv CONDA_PS1_BACKUP

        # csh/tcsh both use rehash
        rehash
    endif
endif

unset CONDA_VERBOSE

exit 0
