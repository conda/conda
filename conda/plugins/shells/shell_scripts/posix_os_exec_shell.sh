#!/bin/sh

# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Evaluate all arguments
eval "$@"

# run an interactive instance of the user's default shell to complete activation
# new shell will inherit the environment variables of this process
${SHELL}

exit 0
