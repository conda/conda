#!/bin/bash

#
# function to cleanup a :-delimited string
#
# usage: envvar_cleanup.bash "$ENV_VAR" [-d | -r "STR_TO_REMOVE" ... | -g "STR_TO_REMOVE" ...] [--delim=DELIM] [-f]
#
# where:
#   "$ENV_VAR"              is the variable name to cleanup
#   -d                      remove duplicates
#   -r "STR_TO_REMOVE" ...  remove first instance of provided strings
#   -g "STR_TO_REMOVE" ...  remove all instances of provided strings
#   --delim=DELIM           specify what the delimit
#   -f                      fuzzy matching in conjunction with -r and -g
#                           (not compatible with -d)
#
# reference:
# http://unix.stackexchange.com/questions/40749/remove-duplicate-path-entries-with-awk-command
#
# TODO:
# consider adding more path cleanup like symlinking paths that are longer than __
#

###############################################################################
# local vars
###############################################################################
TRUE=0
FALSE=1
SETTING=2
VARIABLE=""
MODE="duplicate"
DELIM=":"
STR_TO_REMOVE=""

# at this point VARIABLE, MODE, DELIM, and STR_TO_REMOVE are
# defined and do not need to be checked for unbounded again

###############################################################################
# parse command line, perform command line error checking
###############################################################################
num=0
is_mode_set="${FALSE}"
is_delim_set="${FALSE}"
while [ $num != -1 ]; do
    num=$((${num} + 1))
    arg=$(eval eval echo '\$$num')

    if [ -z $(echo "${arg}" | sed 's| ||g') ]; then
        num=-1
    else
        if [ "${is_delim_set}" = "${SETTING}" ]; then
            DELIM="${arg}"
            is_delim_set="${TRUE}"
        else
            case "${arg}" in
                -d)
                    if [ "${is_mode_set}" = "${FALSE}" ]; then
                        MODE="duplicate"
                        is_mode_set="${TRUE}"
                    else
                        echo "[ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once (${arg})" 1>&2
                        exit 1
                    fi
                    ;;
                -r)
                    if [ "${is_mode_set}" = "${FALSE}" ]; then
                        MODE="remove"
                        is_mode_set="${TRUE}"
                    else
                        echo "[ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once (${arg})" 1>&2
                        exit 1
                    fi
                    ;;
                -g)
                    if [ "${is_mode_set}" = "${FALSE}" ]; then
                        MODE="global"
                        is_mode_set="${TRUE}"
                    else
                        echo "[ENVVAR_CLEANUP]: ERROR: Cannot set mode more than once (${arg})" 1>&2
                        exit 1
                    fi
                    ;;
                --delim)
                    if [ "${is_delim_set}" = "${FALSE}" ]; then
                        is_delim_set="${SETTING}"
                    else
                        echo "[ENVVAR_CLEANUP]: ERROR: Cannot set delim more than once (${arg})" 1>&2
                        exit 1
                    fi
                    ;;
                --delim=*)
                    if [ "${is_delim_set}" = "${FALSE}" ]; then
                        DELIM="${arg:8}"
                        is_delim_set="${TRUE}"
                    else
                        echo "[ENVVAR_CLEANUP]: ERROR: Cannot set delim more than once (${arg})" 1>&2
                        exit 1
                    fi
                    ;;
                -*)
                    echo "[ENVVAR_CLEANUP]: ERROR: Unknown/Invalid flag/parameter (${arg})" 1>&2
                    exit 1
                    ;;
                *)
                    if [ -z "${VARIABLE}" ]; then
                        VARIABLE="${arg}"
                    elif [ -z "${STR_TO_REMOVE}" ]; then
                        STR_TO_REMOVE="${num}"
                    else
                        STR_TO_REMOVE="${STR_TO_REMOVE} ${num}"
                    fi
                    ;;
            esac
        fi
    fi
done
unset num
unset arg
unset is_mode_set
unset is_delim_set

# if any of these variables are undefined set them to a default
[ -z "${MODE}" ]  && MODE="duplicate"
[ -z "${DELIM}" ] && DELIM=":"

# check that $STR_TO_REMOVE is allocated correctly for the various $MODE
if [ "${MODE}" = "duplicate" ]; then
    if [ -n "${STR_TO_REMOVE}" ]; then
        echo "[ENVVAR_CLEANUP]: ERROR: Unknown/Invalid parameters for mode=${MODE} (${STR_TO_REMOVE})" 1>&2
        exit 1
    fi
else
    if [ -z "${STR_TO_REMOVE}" ]; then
        echo "[ENVVAR_CLEANUP]: ERROR: Missing arguments to remove for mode=${MODE}" 1>&2
        exit 1
    fi
fi
STR_TO_REMOVE=( $STR_TO_REMOVE )

######################################################################
# help dialog
######################################################################

######################################################################
# process for removal(s)
######################################################################
if [ -n "${VARIABLE}" ]; then
    if [ "${MODE}" == "duplicate" ]; then
        # remove duplicate entries from $VARIABLE
        # append delimiter to end of $VARIABLE to simplify matching logic
        old_VARIABLE="${VARIABLE}${DELIM}"
        VARIABLE=""
        # iterate over $old_VARIABLE and pop substrings based on the delimiter
        # then decide whether to append the substring to the new $VARIABLE or discard it as a duplicate
        while [ -n "${old_VARIABLE}" ]; do
            x="${old_VARIABLE%%${DELIM}*}"              # the first remaining entry
            case "${VARIABLE}${DELIM}" in
                *"${DELIM}${x}${DELIM}"*) ;;            # already there
                *) VARIABLE="${VARIABLE}${DELIM}${x}";; # not there yet
            esac
            old_VARIABLE="${old_VARIABLE#*$DELIM}"
        done
        # finalize new $VARIABLE by removing the terminating delimiter
        VARIABLE="${VARIABLE#${DELIM}}"
    else
        # set global/local sed flag
        GLOBAL="g"
        [ "${MODE}" == "remove" ] && GLOBAL=""

        # iterate over all of the $STR_TO_REMOVE and strip them from $VARIABLE
        VARIABLE="${DELIM}${VARIABLE}${DELIM}"
        for num in "${STR_TO_REMOVE[@]}"; do
            arg=$(eval eval echo '\$$num')

            if [ -n $(echo "${arg}" | sed 's| ||g') ]; then
                # certain patterns will not be properly stripped by sed
                # as in this example:
                #   > envvar_cleanup.bash "blue-blue-red" -g "blue"
                #   > # $VARIABLE = "-blue-blue-red-"
                #   > # $MODE = "global"
                #   > # $GLOBAL = "g"
                #   > # $STR_TO_REMOVE = ("blue")
                # with this example sed will be able to remove the first
                # occurrence of "-blue-" but since the "-" is shared we
                # must recursively check for the "-blue-" phrase until
                # it no longer exists
                while [[ "${VARIABLE}" =~ .*${DELIM}${arg}${DELIM}.* ]]; do
                    VARIABLE=$(echo "${VARIABLE}" | sed "s|${DELIM}${arg}${DELIM}|${DELIM}|${GLOBAL}")

                    # only remove first occurrence if not global
                    [ "${MODE}" == "remove" ] && break
                done
            fi
        done

        VARIABLE="${VARIABLE#${DELIM}}"
        VARIABLE="${VARIABLE%${DELIM}}"
    fi
fi

echo $(echo ${VARIABLE} | sed 's| |\ |g')
