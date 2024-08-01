# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which


def test_bash_available():
    assert which("bash")
