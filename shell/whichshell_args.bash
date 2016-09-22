#!/usr/bin/env bash

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # WHICHSHELL_ARGS.BASH                                                # #
# # create the arguments to pass to the whichshell.awk program          # #
# # this is the FIRST filtering of what shell the user is running       # #
# #                                                                     # #
# # this works in conjunction with the other whichshell*                # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# DETECT PARENT PROGRAM                                                   #
# since this is already an executable we need to get this parent          #
PARENT_PROCESS=$(whichshell_ps.bash $$ -v)
# END DETECT PARENT PROGRAM                                               #
###########################################################################

###########################################################################
# GET SYSTEM                                                              #
# need to check lsb_release for Ubuntu since the Ubuntu is notorious for  #
# being odd                                                               #
SYSTEM1=""
[ -x "/usr/bin/lsb_release" ] && SYSTEM1="$(lsb_release -si)"
SYSTEM2="$(uname -s)"
# combine lsb_release and uname results                                   #
SYSTEM="${SYSTEM2}"
[ "${SYSTEM1}" == "Ubuntu" ] && SYSTEM="${SYSTEM1}"
# remove any spaces that may occur on certain systems, the spacing will   #
# cause disastrous results when passing arguments to whichshell.awk       #
#                                                                         #
# on openSUSE:                                                            #
#   > lsb_release -si                                                     #
#   > SUSE LINUX                                                          #
SYSTEM=$(echo "${SYSTEM}" | sed 's| ||')
# END GET SYSTEM                                                          #
###########################################################################

###########################################################################
# OFFSET $SHLVL                                                           #
# since we are currently inside an executed program (not sourced)         #
SHELL_LEVEL=$((${SHLVL} - 1))
# END OFFSET $SHLVL                                                       #
###########################################################################

###########################################################################
# $0
ZERO="${3}"
[[ "${PARENT_PROCESS}" =~ ".*csh" ]] && ZERO="CSH"
# END $0
###########################################################################

###########################################################################
# RETURN DETECTED VALUES                                                  #
# whichshell_args.bash expects to have been given two arguments, those    #
# two arguments are passed directly through without modification          #
echo "${PARENT_PROCESS} ${SYSTEM} ${SHELL_LEVEL} ${ZERO} ${1} ${2}"
# END RETURN DETECTED VALUES                                              #
###########################################################################
