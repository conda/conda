#!/bin/bash

#
# function to cleanup a :-delimited string
#
# usage: envvar_cleanup.sh "$ENV_VAR" [-d | -r "STR_TO_REMOVE" ... | -g "STR_TO_REMOVE" ...] [--delim DELIM]
#
# where:
#   "$ENV_VAR"             is the variable name to cleanup
#   -d                     remove duplicates
#   -r "STR_TO_REMOVE" ... remove first instance of provided strings
#   -g "STR_TO_REMOVE" ... remove all instances of provided strings
#   --delim DELIM          specify what the delimit
#
# reference:
# http://unix.stackexchange.com/questions/40749/remove-duplicate-path-entries-with-awk-command
#
# TODO:
# consider adding more path cleanup like symlinking paths that are longer than __
#

# get first parameter, the environment variable
VARIABLE="$1"
MODE=""
DELIM=":"
STR_TO_REMOVE=""

num=1
while [ $num != -1 ]; do
    num=$(($num + 1))
    arg=$(eval eval echo '\$$num')

    if [ -z $(echo "${arg}" | sed 's| ||g') ]; then
        num=-1
    else
        case "${arg}" in
            -d)
                MODE="duplicate"
                ;;
            -r)
                MODE="remove"
                ;;
            -g)
                MODE="global"
                ;;
            --delim=*)
                DELIM=`echo "$arg" | awk '{print(substr($0,9));}'`
                ;;
            -*)
                echo "[ENVVAR_CLEANUP]: ERROR: Unknown/Invalid flag/parameter (${arg})" 1>&2
                ;;
            *)
                STR_TO_REMOVE="$STR_TO_REMOVE $num"
                ;;
        esac
    fi
done
unset num
unset arg

if [ -n "${VARIABLE}" ]; then
  if [ "${MODE}" == "duplicate" ]; then
    old_VARIABLE="${VARIABLE}${DELIM}"
    VARIABLE=""
    while [ -n "${old_VARIABLE}" ]; do
      x="${old_VARIABLE%%:*}"                   # the first remaining entry
      case "${VARIABLE}:" in
        *"${DELIM}${x}${DELIM}"*) ;;            # already there
        *) VARIABLE="${VARIABLE}${DELIM}${x}";; # not there yet
      esac
      old_VARIABLE="${old_VARIABLE#*:}"
    done
    VARIABLE="${VARIABLE#${DELIM}}"
  elif [ "${MODE}" == "remove" ] || [ "${MODE}" == "global" ]; then
    if [ "${MODE}" == "remove" ]; then
      GLOBAL=""
      num=1
    else
      GLOBAL="g"
      num=2
    fi

    VARIABLE="${DELIM}${VARIABLE}${DELIM}"

    while [ $num != -1 ]; do
      num=$(($num + 1))
      arg=$(eval eval echo '\$$num')

      if [ -z $(echo "${arg}" | sed 's| ||g') ]; then
        num=-1
      else
        VARIABLE=$(echo "${VARIABLE}" | sed "s|${DELIM}${arg}${DELIM}|${DELIM}|${GLOBAL}")
      fi
    done

    VARIABLE="${VARIABLE#$DELIM}"
    VARIABLE="${VARIABLE%$DELIM}"
  fi
fi

echo $(echo ${VARIABLE} | sed 's| |\ |g')
