#!/bin/bash

# create the arguments to pass to the whichshell.awk program

# get process id (for the calling process)
PARENT_PID=$(ps -o ppid= -p $$)
PARENT_PROCESS=$(ps -o command= -p $PARENT_PID)

# intercept special login cases
# required to allow unit tests to pass properly when running tests for the prompt
if [[ "${PARENT_PROCESS}" =~ "-l" || "${PARENT_PROCESS}" =~ "--login" ]]; then
    PARENT_PROCESS="-$(echo $PARENT_PROCESS | sed 's|-l||g; s|--login||g;')"
fi

# get the system we are on
if [ -x "/usr/bin/lsb_release" ]; then
    SYSTEM=$(lsb_release -si)
else
    SYSTEM=$(uname -s)
fi
SYSTEM=$(echo $SYSTEM | sed 's| ||')

# offset shell level since we are currently inside an executed program (not sourced)
SHELL_LEVEL=$(($SHLVL - 1))

# return the values detected
echo "$PARENT_PROCESS $SYSTEM $SHELL_LEVEL $1 $2"
