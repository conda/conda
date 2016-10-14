#!/usr/bin/env bash

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # CLEANUP DELIMITED STRING (TYPICALLY THE $PATH)                      # #
# #                                                                     # #
# # usage: envvar_cleanup.bash "$ENV_VAR"                               # #
# #        [-d | [-u | -r | -g] "STR_TO_REMOVE" ...] [--delim=DELIM]    # #
# #        [-f]                                                         # #
# #                                                                     # #
# # where:                                                              # #
# #     "$ENV_VAR"              is the variable name to cleanup         # #
# #     -d                      remove duplicates                       # #
# #     -u "STR_TO_REMOVE" ...  remove first UNIQUE match of provided   # #
# #                             strings (with fuzzy match, -f, this may # #
# #                             remove multiple elements)               # #
# #     -r "STR_TO_REMOVE" ...  remove first match of provided strings  # #
# #                             (even with fuzzy match, -f, this will   # #
# #                             only remove the first match)            # #
# #     -g "STR_TO_REMOVE" ...  remove all instances of provided        # #
# #                             strings                                 # #
# #     --delim=DELIM           specify what the delimit                # #
# #     -f                      fuzzy matching in conjunction with -u,  # #
# #                             -r, and -g (not compatible with -d)     # #
# #                                                                     # #
# # reference:                                                          # #
# # http://unix.stackexchange.com/questions/40749/                      # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# DEFINE BASIC VARS                                                       #
TRUE=1
FALSE=0
SETTING=2
VARIABLE=""
MODE="duplicate"
DELIM=":"
FUZZY="${FALSE}"
STR_TO_REMOVE=""
STR_TO_REMOVE_I=-1
UNIQUE_MATCHES=""
UNIQUE_MATCHES_I=-1

# at this point VARIABLE, MODE, DELIM, and STR_TO_REMOVE are              #
# defined and do not need to be checked for unbounded again               #
# END DEFINE BASIC VARS                                                   #
###########################################################################

###########################################################################
# PARSE COMMAND LINE                                                      #
num=0
is_mode_set="${FALSE}"
is_delim_set="${FALSE}"
is_fuzzy_set="${FALSE}"
while [ $num != -1 ]; do
    num=$((num + 1))
    arg=$(eval eval echo '\${$num}') >/dev/null 2>&1

    # check if variable is blank, if so stop parsing
    if [ $? != 0 ] || [ -z "${arg/ /}" ]; then
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
                -u)
                    if [ "${is_mode_set}" = "${FALSE}" ]; then
                        MODE="unique"
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
                        STR_TO_REMOVE_I=$((STR_TO_REMOVE_I + 1))
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

# if any of these variables are undefined set them to a default           #
[ -z "${MODE}" ]  && MODE="duplicate"
[ -z "${DELIM}" ] && DELIM=":"

# check that $STR_TO_REMOVE is allocated correctly for the various $MODE  #
if [ "${MODE}" = "duplicate" ]; then
    if [ "${STR_TO_REMOVE_I}" != -1 ]; then
        echo "[ENVVAR_CLEANUP]: ERROR: Unknown/Invalid parameters for mode=${MODE}" 1>&2
        exit 1
    fi
else
    if [ "${STR_TO_REMOVE_I}" = -1 ]; then
        echo "[ENVVAR_CLEANUP]: ERROR: Missing arguments to remove for mode=${MODE}" 1>&2
        exit 1
    fi
fi
# END PARSE COMMAND LINE                                                  #
###########################################################################

###########################################################################
# HELP DIALOG                                                             #
# TODO
# END HELP DIALOG                                                         #
###########################################################################

###########################################################################
# PROCESS FOR REMOVAL(S)                                                  #
if [ -n "${VARIABLE}" ]; then
    # remove DELIM from the beginning and append DELIM to the end
    # remember if there was a delim at the beginning/end and mimic the
    # same pattern upon finish
    if [ "${VARIABLE::1}" = "${DELIM}" ]; then
        HAS_PRE_DELIM="${TRUE}"
        VARIABLE="${VARIABLE:1}"
    else
        HAS_PRE_DELIM="${FALSE}"
    fi
    if [ "${VARIABLE:(-1)}" = "${DELIM}" ]; then
        HAS_POST_DELIM="${TRUE}"
    else
        HAS_POST_DELIM="${FALSE}"
        VARIABLE="${VARIABLE}${DELIM}"
    fi

    old_VARIABLE="${VARIABLE}"
    VARIABLE="${DELIM}"

    MAX_ITER=${#old_VARIABLE}
    NUM_NONDELIMS="${old_VARIABLE//${DELIM}/}"
    NUM_NONDELIMS=${#NUM_NONDELIMS}
    MAX_ITER=$((MAX_ITER - NUM_NONDELIMS))

    if [ "${MODE}" == "duplicate" ]; then
        # iterate over all phrases split by delim
        for (( i = 1; i <= MAX_ITER; i++ )); do
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
    else
        # iterate over all phrases split by delim
        for (( i = 1; i <= MAX_ITER; i++ )); do
            # chop off the first phrase available
            x="${old_VARIABLE%%${DELIM}*}"
            old_VARIABLE="${old_VARIABLE#*${DELIM}}"

            MATCH=-1
            FUZZY_MATCH=-1
            for (( j = 0; j <= STR_TO_REMOVE_I; j++ )); do
                if [ "${STR_TO_REMOVE[${j}]}" != "" ]; then
                    # check for an exact match
                    if [ "${STR_TO_REMOVE[${j}]}" = "${x}" ]; then
                        MATCH="${j}"
                    else
                        # check for a fuzzy match (if applicable)
                        if [ "${FUZZY}" = "${TRUE}" ]; then
                            TMP="${x/${STR_TO_REMOVE[${j}]}/}"
                            if [ "${TMP}" != "${x}" ]; then
                                FUZZY_MATCH="${j}"
                            fi
                        fi
                    fi
                fi
            done

            PRIOR_MATCH=-1
            for (( j = 0; j <= UNIQUE_MATCHES_I; j++ )); do
                if [ "${UNIQUE_MATCHES[${j}]}" != "" ]; then
                    # check if we have matched this before
                    #
                    # ensure we are checking against paths that have been "standardized"
                    # on some oddball systems paths with the wrong slash are still valid
                    # but may match incorrect as a unique match
                    # example:
                    #   envvar_cleanup.bash "/prefix/path:/prefix\path" --delim=":" -u -f "/prefix"
                    unique_match_std="${UNIQUE_MATCHES[${j}]////|}"
                    unique_match_std="${unique_match_std/\\/|}"
                    x_std="${x////|}"
                    x_std="${x_std/\\/|}"
                    if [ "${unique_match_std}" = "${x_std}" ]; then
                        PRIOR_MATCH="${j}"
                    fi
                fi
            done

            if [ "${MATCH}" = -1 ] && [ "${FUZZY_MATCH}" = -1 ]; then
                VARIABLE="${VARIABLE}${x}${DELIM}"
            else
                if [ "${MODE}" = "unique" ]; then
                    # collect all matches
                    if [ "${PRIOR_MATCH}" = -1 ]; then
                        # this is a unique match
                        UNIQUE_MATCHES_I=$((UNIQUE_MATCHES_I + 1))
                        UNIQUE_MATCHES[${UNIQUE_MATCHES_I}]="${x}"
                    else
                        # this is a non-unique match
                        VARIABLE="${VARIABLE}${x}${DELIM}"
                    fi
                elif [ "${MODE}" = "remove" ]; then
                    if [ "${MATCH}" != -1 ]; then
                        STR_TO_REMOVE[${MATCH}]=""
                    else
                        STR_TO_REMOVE[${FUZZY_MATCH}]=""
                    fi
                fi
            fi
        done
    fi

    # trim off the first and last DELIM that was added at the start
    if ! [ "${#VARIABLE}" = 0 ]; then
        if [ "${HAS_PRE_DELIM}" = "${TRUE}" ]; then
            if ! [ "${VARIABLE::1}" = "${DELIM}" ]; then
                VARIABLE="${DELIM}${VARIABLE}"
            fi
        else
            if [ "${VARIABLE::1}" = "${DELIM}" ]; then
                VARIABLE="${VARIABLE:1}"
            fi
        fi
    fi
    if ! [ "${#VARIABLE}" = 0 ]; then
        if [ "${HAS_POST_DELIM}" = "${TRUE}" ]; then
            if ! [ "${VARIABLE:(-1)}" = "${DELIM}" ]; then
                VARIABLE="${VARIABLE}${DELIM}"
            fi
        else
            if [ "${VARIABLE:(-1)}" = "${DELIM}" ]; then
                # bash < 4.2 doesn't support negative slicing:
                #   ${VARIABLE::(-1)}
                LEN=${#VARIABLE}
                LEN=$((${LEN} - 1))
                VARIABLE="${VARIABLE::${LEN}}"
            fi
        fi
    fi
fi
# END PROCESS FOR REMOVAL(S)                                              #
###########################################################################

###########################################################################
# CLEANUP VARS FOR THIS SCOPE                                             #
echo "${VARIABLE}"
# END CLEANUP VARS FOR THIS SCOPE                                         #
###########################################################################
