# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from os.path import dirname, join

# remote=True is only used in two places, in tests.conda_env.test_create


def support_file(filename, port=None, remote=False):
    if remote:
        assert port is not None
        return f"http://127.0.0.1:{port}/{filename}"
    return join(dirname(__file__), "support", filename)
