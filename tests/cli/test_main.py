# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest


def test_main():
    with pytest.raises(SystemExit):
        __import__("conda.__main__")
