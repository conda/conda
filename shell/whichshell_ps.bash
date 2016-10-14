#!/usr/bin/env bash

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # WHICHSHELL_PS.BASH                                                  # #
# # helper function to detect the shell from the ps command             # #
# # this is a separate function since it is utilized in multiple        # #
# # locations to detect the shell from the ps command                   # #
# #                                                                     # #
# # this works in conjunction with the other whichshell*                # #
# #                                                                     # #
# # in some versions of zsh/ps/procps the `ps -p $$` command will       # #
# # return an error but it is not a critical terminating error:         # #
# #     > ps -p $$                                                      # #
# #     > Signal 18 (CONT) caught by ps (procps-ng version 3.3.9).      # #
# #     > ps:display.c:66: please report this bug                       # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# DETECT CYGWIN VS MINGW VS MSYS VS UNIX                                  #
# since they have incompatible ps commands                                #
IS_WIN="false"
case "$(uname -s)" in
    CYGWIN*)
        IS_WIN="cygwin"
        ;;
    MINGW*)
        IS_WIN="mingw"
        ;;
    MSYS*)
        IS_WIN="msys"
        ;;
esac
# END DETECT CYGWIN VS UNIX                                               #
###########################################################################

###########################################################################
# GET PROCESS ID of this executable's parent                              #
[ "${1}" != "" ] && ID="${1}" || ID=$$
if [ "${IS_WIN}" == "cygwin" ]; then
    PARENT_PID=($(ps -f -p ${ID}))
    PARENT_PID=${PARENT_PID[8]}
elif [ "${IS_WIN}" == "mingw" ] || [ "${IS_WIN}" == "msys" ]; then
    PARENT_PID=($(ps | grep ${ID} | grep -v "ps" | grep -v "grep"))
    PARENT_PID=${PARENT_PID[1]}
else
    PARENT_PID=$(ps -o ppid= -p ${ID})
fi
# END GET PROCESS ID                                                      #
###########################################################################

###########################################################################
# DETECT PARENT PROGRAM, look at all 3 types of command representations   #
if [ "${IS_WIN}" == "cygwin" ]; then
    PARENT_PROCESS_1=($(ps -s -p ${PARENT_PID}))
    PARENT_PROCESS_1="${PARENT_PROCESS_1[@]:7}"
    PARENT_PROCESS_2=""
    PARENT_PROCESS_3=""
elif [ "${IS_WIN}" == "mingw" ] || [ "${IS_WIN}" == "msys" ]; then
    PARENT_PROCESS_1=($(ps -s | grep ${PARENT_PID}))
    PARENT_PROCESS_1="${PARENT_PROCESS_1[@]:3}"
    PARENT_PROCESS_2=""
    PARENT_PROCESS_3=""
else
    PARENT_PROCESS_1=$(ps -o command= -p ${PARENT_PID})
    PARENT_PROCESS_2=$(ps -o comm=    -p ${PARENT_PID})
    PARENT_PROCESS_3=$(ps -o args=    -p ${PARENT_PID})
fi
# END DETECT PARENT PROGRAM                                               #
###########################################################################

###########################################################################
# RESOLVE PARENT PROGRAM if possible                                      #
# if any of the parent process commands obviously tell us what the shell  #
# is go with that, otherwise leave the comparison logic to whichshell.awk #
REGEX_BASH="^bash(\s+.+)*"
IS_BASH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_BASH} ]] && IS_BASH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_BASH} ]] && IS_BASH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_BASH} ]] && IS_BASH=true

REGEX_DASH="^dash(\s+.+)*"
IS_DASH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_DASH} ]] && IS_DASH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_DASH} ]] && IS_DASH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_DASH} ]] && IS_DASH=true

REGEX_POSH="^posh(\s+.+)*"
IS_POSH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_POSH} ]] && IS_POSH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_POSH} ]] && IS_POSH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_POSH} ]] && IS_POSH=true

REGEX_ZSH="^zsh(\s+.+)*"
IS_ZSH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_ZSH} ]] && IS_ZSH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_ZSH} ]] && IS_ZSH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_ZSH} ]] && IS_ZSH=true

REGEX_KSH="^ksh(\s+.+)*"
IS_KSH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_KSH} ]] && IS_KSH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_KSH} ]] && IS_KSH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_KSH} ]] && IS_KSH=true

REGEX_CSH="^csh(\s+.+)*"
IS_CSH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_CSH} ]] && IS_CSH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_CSH} ]] && IS_CSH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_CSH} ]] && IS_CSH=true

REGEX_TCSH="^tcsh(\s+.+)*"
IS_TCSH=false
[[ "${PARENT_PROCESS_1}" =~ ${REGEX_TCSH} ]] && IS_TCSH=true
[[ "${PARENT_PROCESS_2}" =~ ${REGEX_TCSH} ]] && IS_TCSH=true
[[ "${PARENT_PROCESS_3}" =~ ${REGEX_TCSH} ]] && IS_TCSH=true

if [ "${IS_BASH}" = true ]; then
    PARENT_PROCESS="bash"
elif [ "${IS_DASH}" = true ]; then
    PARENT_PROCESS="dash"
elif [ "${IS_POSH}" = true ]; then
    PARENT_PROCESS="posh"
elif [ "${IS_ZSH}" = true ]; then
    PARENT_PROCESS="zsh"
elif [ "${IS_KSH}" = true ]; then
    PARENT_PROCESS="ksh"
elif [ "${IS_CSH}" = true ]; then
    PARENT_PROCESS="csh"
elif [ "${IS_TCSH}" = true ]; then
    PARENT_PROCESS="tcsh"
else
    PARENT_PROCESS="${PARENT_PROCESS_1}"
fi
# END RESOLVE PARENT PROGRAM                                              #
###########################################################################

###########################################################################
# IGNORE SPECIAL FLAGS                                                    #
# specifically required to allow unit tests to pass properly when running #
# tests for the prompt                                                    #
#                                                                         #
# also useful for supporting unique corner cases of login/interactive     #
# sub-shells                                                              #
if [[ "${PARENT_PROCESS}" =~ --login ]]; then
    PARENT_PROCESS="-${PARENT_PROCESS/--login/}"
fi
if [[ "${PARENT_PROCESS}" =~ -l ]]; then
    PARENT_PROCESS="-${PARENT_PROCESS/-l/}"
fi
if [[ "${PARENT_PROCESS}" =~ -i ]]; then
    PARENT_PROCESS="${PARENT_PROCESS/-i/}"
fi
# END IGNORE SPECIAL FLAGS                                                #
###########################################################################

###########################################################################
# PARENT PROCESS RETURN                                                   #
if [ "${2}" == "-v" ]; then
    echo "${PARENT_PROCESS}"
else
    if [[ "${PARENT_PROCESS}" =~ .*csh ]]; then
        exit 1
    else
        exit 0
    fi
fi
# END PARENT PROCESS RETURN                                               #
###########################################################################
