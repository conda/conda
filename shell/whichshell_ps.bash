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
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# GET PROCESS ID of this executable's parent                              #
if [ "${1}" != "" ]; then
    PARENT_PID=$(ps -o ppid= -p $1)
else
    PARENT_PID=$(ps -o ppid= -p $$)
fi
# END GET PROCESS ID                                                      #
###########################################################################

###########################################################################
# DETECT PARENT PROGRAM, look at all 3 types of command representations   #
PARENT_PROCESS_1=$(ps -o command= -p ${PARENT_PID})
PARENT_PROCESS_2=$(ps -o comm=    -p ${PARENT_PID})
PARENT_PROCESS_3=$(ps -o args=    -p ${PARENT_PID})
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
if [[ "${PARENT_PROCESS}" =~ "--login" ]]; then
    PARENT_PROCESS="-$(echo ${PARENT_PROCESS} | sed 's|--login||g;')"
fi
if [[ "${PARENT_PROCESS}" =~ "-l" ]]; then
    PARENT_PROCESS="-$(echo ${PARENT_PROCESS} | sed 's|-l||g;')"
fi
if [[ "${PARENT_PROCESS}" =~ "-i" ]]; then
    PARENT_PROCESS="$(echo ${PARENT_PROCESS} | sed 's|-i||g;')"
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
