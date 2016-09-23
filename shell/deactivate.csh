#!/bin/csh

#
# source "`which deactivate`" for c-shell
#

###############################################################################
# local vars
###############################################################################
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
if ( `env | grep CONDA_HELP` != "" ) then
    set IS_ENV_CONDA_HELP="${TRUE}"
endif
if ( `env | grep CONDA_VERBOSE` != "" ) then
    set IS_ENV_CONDA_VERBOSE="${TRUE}"
endif

# inherit whatever the user set
# this is important for dash where you cannot pass parameters to sourced scripts
# since this script is exclusively for csh/tcsh this is just for consistency/a bonus feature
if ( ! $?CONDA_HELP ) then
    set CONDA_HELP="${FALSE}"
else if ( "${CONDA_HELP}" == "false" || "${CONDA_HELP}" == "FALSE" || "${CONDA_HELP}" == "False") then
    set CONDA_HELP="${FALSE}"
else if ( "${CONDA_HELP}" == "true" || "${CONDA_HELP}" == "TRUE" || "${CONDA_HELP}" == "True" ) then
    set CONDA_HELP="${TRUE}"
endif
set UNKNOWN=""
if ( ! $?CONDA_VERBOSE ) then
    set CONDA_VERBOSE="${FALSE}"
else if ( "${CONDA_VERBOSE}" == "false" || "${CONDA_VERBOSE}" == "FALSE" || "${CONDA_VERBOSE}" == "False") then
    set CONDA_VERBOSE="${FALSE}"
else if ( "${CONDA_VERBOSE}" == "true" || "${CONDA_VERBOSE}" == "TRUE" || "${CONDA_VERBOSE}" == "True" ) then
    set CONDA_VERBOSE="${TRUE}"
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
                set CONDA_HELP="${TRUE}"
                breaksw
            case "-v":
            case "--verbose":
                set CONDA_VERBOSE="${TRUE}"
                breaksw
            default:
                # use == "" instead of -z test for robust support across
                # different platforms (especially Ubuntu)
                if ( "${UNKNOWN}" == "" ) then
                    set UNKNOWN="${arg}"
                else
                    set UNKNOWN="${UNKNOWN} ${arg}"
                endif
                set CONDA_HELP="${TRUE}"
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
    set CONDA_HELP="${FALSE}"
endif
if ( "`echo ${CONDA_VERBOSE} | sed 's| ||g'`" == "" ) then
    set CONDA_VERBOSE="${FALSE}"
endif

# export CONDA_* variables as necessary
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
    conda ..deactivate ${WHAT_SHELL_AM_I} -h ${UNKNOWN}

    unset WHAT_SHELL_AM_I
    if ( "${IS_ENV_CONDA_HELP}" == "${FALSE}" ) then
        unset CONDA_HELP
    endif
    if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
        unset CONDA_VERBOSE
    endif
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
unset WHAT_SHELL_AM_I
if ( "${IS_ENV_CONDA_HELP}" == "${FALSE}" ) then
    unset CONDA_HELP
endif
unset IS_ENV_CONDA_HELP
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
                if ( "${CONDA_VERBOSE}" == "${TRUE}" ) then
                    echo "[DEACTIVATE]: Sourcing ${_CONDA_DIR}/${f}."
                endif
                source "${_CONDA_DIR}/${f}"
            end
        endif
        unset _CONDA_DIR

        # restore PROMPT
        if ( $?CONDA_PS1_BACKUP && $?prompt ) then
            set prompt="${CONDA_PS1_BACKUP}"
            unsetenv CONDA_PS1_BACKUP
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
        set path=(`envvar_cleanup.bash "${tmp_path}" -r "${CONDA_PREFIX}/bin" --delim=" "`)
        set PATH=(`envvar_cleanup.bash "${tmp_PATH}" -r "${CONDA_PREFIX}/bin"`)
        unset tmp_path tmp_PATH

        # remove CONDA_PREFIX
        unsetenv CONDA_PREFIX

        # csh/tcsh both use rehash
        rehash
    endif
endif

if ( "${IS_ENV_CONDA_VERBOSE}" == "${FALSE}" ) then
    unset CONDA_VERBOSE
endif
unset IS_ENV_CONDA_VERBOSE
unset TRUE
unset FALSE
exit 0
