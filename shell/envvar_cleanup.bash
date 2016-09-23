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
FUZZY="${FALSE}"
STR_TO_REMOVE=""
STR_TO_REMOVE_I=-1

# at this point VARIABLE, MODE, DELIM, and STR_TO_REMOVE are
# defined and do not need to be checked for unbounded again

###############################################################################
# parse command line, perform command line error checking
###############################################################################
num=0
is_mode_set="${FALSE}"
is_delim_set="${FALSE}"
is_fuzzy_set="${FALSE}"
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
                -f)
                    if [ "${is_fuzzy_set}" = "${FALSE}" ]; then
                        FUZZY="${TRUE}"
                        is_fuzzy_set="${TRUE}"
                    else
                        echo "[ENVVAR_CLEANUP]: ERROR: Cannot set fuzzy more than once (${arg})" 1>&2
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
                    else
                        STR_TO_REMOVE_I=$(( ${STR_TO_REMOVE_I} + 1 ))
                        STR_TO_REMOVE[${STR_TO_REMOVE_I}]="${arg}"
                    fi
                    ;;
            esac
        fi
    fi
done

if [ "${is_delim_set}" = "${SETTING}" ]; then
    echo "[ENVVAR_CLEANUP]: Delim flag has been provided without any delimiter" 1>&2
    exit 1
fi
unset num
unset arg
unset is_mode_set
unset is_delim_set
unset is_fuzzy_set

# if any of these variables are undefined set them to a default
[ -z "${MODE}" ]  && MODE="duplicate"
[ -z "${DELIM}" ] && DELIM=":"

# check that $STR_TO_REMOVE is allocated correctly for the various $MODE
if [ "${MODE}" = "duplicate" ]; then
    if ! [ "${STR_TO_REMOVE_I}" = -1 ]; then
        echo "[ENVVAR_CLEANUP]: ERROR: Unknown/Invalid parameters for mode=${MODE}" 1>&2
        exit 1
    fi
else
    if [ "${STR_TO_REMOVE_I}" = -1 ]; then
        echo "[ENVVAR_CLEANUP]: ERROR: Missing arguments to remove for mode=${MODE}" 1>&2
        exit 1
    fi
fi

######################################################################
# help dialog
######################################################################
# TODO

######################################################################
# process for removal(s)
######################################################################
if [ -n "${VARIABLE}" ]; then
    # remove DELIM from the beginning and append DELIM to the end
    # *only if the delim hasn't already been added/removed
    if [ "${VARIABLE:0:1}" = "${DELIM}" ]; then
        RM_PRE_DELIM="${FALSE}"
        VARIABLE="${VARIABLE#*${DELIM}}"
    else
        RM_PRE_DELIM="${TRUE}"
    fi

    if [ "${VARIABLE:(-1)}" = "${DELIM}" ]; then
        RM_POST_DELIM="${FALSE}"
    else
        RM_POST_DELIM="${TRUE}"
        VARIABLE="${VARIABLE}${DELIM}"
    fi

    old_VARIABLE="${VARIABLE}"
    VARIABLE="${DELIM}"

    MAX_ITER=${#old_VARIABLE}
    NUM_NONDELIMS="${old_VARIABLE//${DELIM}/}"
    NUM_NONDELIMS=${#NUM_NONDELIMS}
    MAX_ITER=$(( ${MAX_ITER} - ${NUM_NONDELIMS} ))

    if [ "${MODE}" == "duplicate" ]; then
        # iterate over all phrases split by delim
        for (( i = 1; i <= ${MAX_ITER}; i++ )); do
            # chop off the first phrase available
            x="${old_VARIABLE%%${DELIM}*}"
            old_VARIABLE="${old_VARIABLE#*${DELIM}}"

            FROM="${DELIM}${x}${DELIM}"

            TMP="${VARIABLE/${FROM}/${DELIM}}"

            # if removing the current phrase from the %VARIABLE% didn't change
            # anything that means that it doesn't exist yet in the new unique
            # list, consequently append the value
            [ "${TMP}" = "${VARIABLE}" ] && VARIABLE="${VARIABLE}${x}${DELIM}"
        done

        # # remove duplicate entries from $VARIABLE
        # # append delimiter to end of $VARIABLE to simplify matching logic
        # old_VARIABLE="${VARIABLE}${DELIM}"
        # VARIABLE=""
        # # iterate over $old_VARIABLE and pop substrings based on the delimiter
        # # then decide whether to append the substring to the new $VARIABLE or discard it as a duplicate
        # while [ -n "${old_VARIABLE}" ]; do
        #     x="${old_VARIABLE%%${DELIM}*}"              # the first remaining entry
        #     case "${VARIABLE}${DELIM}" in
        #         *"${DELIM}${x}${DELIM}"*) ;;            # already there
        #         *) VARIABLE="${VARIABLE}${DELIM}${x}";; # not there yet
        #     esac
        #     old_VARIABLE="${old_VARIABLE#*$DELIM}"
        # done
        # # finalize new $VARIABLE by removing the terminating delimiter
        # VARIABLE="${VARIABLE#${DELIM}}"
    else
        # iterate over all phrases split by delim
        for (( i = 1; i <= ${MAX_ITER}; i++ )); do
            # chop off the first phrase available
            x="${old_VARIABLE%%${DELIM}*}"
            old_VARIABLE="${old_VARIABLE#*${DELIM}}"

            MATCH=-1
            FUZZY_MATCH=-1
            for (( j = 0; j < 10; j++ )); do
                if ! [ "${STR_TO_REMOVE[${j}]}" = "" ]; then
                    # check for an exact match
                    if [ "${STR_TO_REMOVE[${j}]}" = "${x}" ]; then
                        MATCH="${j}"
                    else
                        # check for a fuzzy match (if applicable)
                        if [ "${FUZZY}" = "${TRUE}" ]; then
                            TMP="${x/${STR_TO_REMOVE[${j}]}/}"
                            if ! [ "${TMP}" = "${x}" ]; then
                                FUZZY_MATCH="${j}"
                            fi
                        fi
                    fi
                fi
            done

            if [ "${MATCH}" = -1 ]; then
                if [ "${FUZZY_MATCH}" = -1 ]; then
                    VARIABLE="${VARIABLE}${x}${DELIM}"
                fi
            else
                if [ "${MODE}" = "remove" ]; then
                    if ! [ "${MATCH}" = -1 ]; then
                        STR_TO_REMOVE[${MATCH}]=""
                    else
                        STR_TO_REMOVE[${FUZZY_MATCH}]=""
                    fi
                fi
            fi
        done

        # # set global/local sed flag
        # GLOBAL="g"
        # [ "${MODE}" == "remove" ] && GLOBAL=""

        # # iterate over all of the $STR_TO_REMOVE and strip them from $VARIABLE
        # VARIABLE="${DELIM}${VARIABLE}${DELIM}"
        # for num in "${STR_TO_REMOVE[@]}"; do
        #     arg=$(eval eval echo '\$$num')

        #     if [ -n $(echo "${arg}" | sed 's| ||g') ]; then
        #         # certain patterns will not be properly stripped by sed
        #         # as in this example:
        #         #   > envvar_cleanup.bash "blue-blue-red" -g "blue"
        #         #   > # $VARIABLE = "-blue-blue-red-"
        #         #   > # $MODE = "global"
        #         #   > # $GLOBAL = "g"
        #         #   > # $STR_TO_REMOVE = ("blue")
        #         # with this example sed will be able to remove the first
        #         # occurrence of "-blue-" but since the "-" is shared we
        #         # must recursively check for the "-blue-" phrase until
        #         # it no longer exists
        #         while [[ "${VARIABLE}" =~ .*${DELIM}${arg}${DELIM}.* ]]; do
        #             VARIABLE=$(echo "${VARIABLE}" | sed "s|${DELIM}${arg}${DELIM}|${DELIM}|${GLOBAL}")

        #             # only remove first occurrence if not global
        #             [ "${MODE}" == "remove" ] && break
        #         done
        #     fi
        # done

        # VARIABLE="${VARIABLE#${DELIM}}"
        # VARIABLE="${VARIABLE%${DELIM}}"
    fi

    # trim off the first and last DELIM that was added at the start
    [ "${RM_PRE_DELIM}" = "${TRUE}" ] && VARIABLE="${VARIABLE:1}"
    [ "${RM_POST_DELIM}" = "${TRUE}" ] && VARIABLE="${VARIABLE:0:${#VARIABLE}-1}"
fi

echo $(echo ${VARIABLE} | sed 's| |\ |g')
