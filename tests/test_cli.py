# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import re
import stat
import unittest
import uuid
from unittest.mock import patch

import pytest

from conda.base.constants import on_win
from conda.base.context import context
from conda.gateways.disk.delete import rm_rf
from conda.testing.helpers import capture_json_with_argv, run_inprocess_conda_command
from conda.testing.integration import (
    Commands,
    make_temp_env,
    make_temp_prefix,
    run_command,
)


@pytest.mark.usefixtures("tmpdir")
class TestJson(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def empty_env_tmpdir(self, tmpdir):
        # TODO :: Figure out if the pkgcache and a way to look for alternatives until one is found and add
        #         a warning about it.
        """
        # Slightly fancier, "works on my computer", using the last 3 dirs is probably a pytest-ism?
        self.tmpdir = os.path.join('opt', 'conda.tmp', *(str(tmpdir).split(os.sep)[-3:]))
        try:
            try:
                rm_rf(self.tmpdir)
            except:
                pass
            os.makedirs(self.tmpdir)
        except:
            self.tmpdir = str(tmpdir)
        """
        self.tmpdir = str(tmpdir)
        return self.tmpdir

    def assertJsonSuccess(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)

    def assertJsonError(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)

    def tearDown(self):
        rm_rf("tempfile.rc")
