# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from os.path import dirname, join


def support_file(filename):
    return join(dirname(__file__), "support", filename)


def remote_support_file(filename, port: int):
    assert port is not None
    return f"http://127.0.0.1:{port}/{filename}"
