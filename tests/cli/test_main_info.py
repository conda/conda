# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger

from os.path import isdir

from conda.cli.python_api import Commands, run_command
from conda.common.io import env_var

log = getLogger(__name__)


def test_info_root():
    stdout, stderr, rc = run_command(Commands.INFO, "--root")
    assert rc == 0
    assert not stderr
    assert isdir(stdout.strip())

    stdout, stderr, rc = run_command(Commands.INFO, "--root", "--json")
    assert rc == 0
    assert not stderr
    json_obj = json.loads(stdout.strip())
    assert isdir(json_obj["root_prefix"])


def test_info_unsafe_channels():
    url = "https://conda.anaconda.org/t/tk-123/a/b/c"
    with env_var("CONDA_CHANNELS", url):
        stdout, stderr, rc = run_command(Commands.INFO, "--unsafe-channels")
        assert rc == 0
        assert not stderr
        assert "tk-123" in stdout

        stdout, stderr, rc = run_command(Commands.INFO, "--unsafe-channels", "--json")
        assert rc == 0
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert url in json_obj["channels"]
