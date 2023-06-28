#!/bin/csh

# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# check we made it here
echo "Running csh/tcsh shell script"

# Evaluate all arguments
eval "$*"

# run an interactive instance of the user's current shell to complete activation
# new shell will inherit the environment variables of this process
# tcsh and csh set $shell but other shells do not
exec ${shell}

exit 0
