# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from os.path import dirname, join


def support_file(filename, remote=False):
    if remote:
        return f"http://127.0.0.1:8928/{filename}"
    return join(dirname(__file__), "support", filename)
