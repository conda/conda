#!/bin/csh

#
# `source deactivate` for csh
#

######################################################################
# test if script is sourced
######################################################################
if ( `basename -- "$0"` =~ "*deactivate*" ) then
    # we are not being sourced
    sh -c 'echo "[DEACTIVATE]: ERROR: Must be sourced. Run \`source deactivate\`." 1>&2'
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
        endif
    end
    unset num
    unset arg
endif

######################################################################
# help dialog
######################################################################
if ( "$HELP" == true ) then
    if ( "$UNKNOWN" != "" ) then
        sh -c "echo '[DEACTIVATE]: ERROR: Unknown/Invalid flag/parameter ($UNKNOWN)' 1>&2"
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
    if ( "$CONDA_PATH_BACKUP" != "" ) then
        # unload post-activate scripts
        # scripts found in $CONDA_PREFIX/etc/conda/deactivate.d
        set _CONDA_DIR="${CONDA_PREFIX}/etc/conda/deactivate.d"
        if ( -d "${_CONDA_DIR}" ) then
            foreach f ( `ls "${_CONDA_DIR}" | grep \\.csh$` )
                source "${_CONDA_DIR}/${f}"
            end
        endif
        unset _CONDA_DIR

        # restore PROMPT
        set prompt="$CONDA_PROMPT_BACKUP"

        # remove CONDA_DEFAULT_ENV
        unsetenv CONDA_DEFAULT_ENV

        # remove CONDA_PREFIX
        unsetenv CONDA_PREFIX

        # restore PATH
        set path=(${CONDA_path_BACKUP})
        set PATH=(${CONDA_PATH_BACKUP})

        # remove CONDA_PATH_BACKUP,CONDA_PROMPT_BACKUP
        unsetenv CONDA_PROMPT_BACKUP
        unsetenv CONDA_path_BACKUP
        unsetenv CONDA_PATH_BACKUP

        # csh/tcsh both use rehash
        rehash
    endif
endif

exit 0
