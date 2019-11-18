# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import tempfile
from unittest import TestCase
import pytest
import json
from logging import getLogger

from os.path import isdir

from conda.cli.python_api import Commands, run_command
from conda.common.io import env_var

log = getLogger(__name__)

class TestCliRun(TestCase):
    def setUp(self):
        self.prefix = tempfile.mkdtemp()
        self.testenv = tempfile.mkdtemp()
        run_command(Commands.CREATE, self.prefix, 'python=3.7')

    @pytest.mark.integration
    def test_run_simple(self):
        stdout, stderr, rc = run_command(Commands.RUN, "python", "--version")
        assert rc == 0
        assert not stderr
        assert "Python " in stdout

    @pytest.mark.integration
    def test_run_with_lots_of_std_out(self):
        stdout, stderr, rc = run_command(Commands.RUN, "python", "-c", "import sys; print('x' * int(10000))")
        assert rc == 0
        assert not stderr
        assert "xxx" in stdout

    @pytest.mark.integration
    def test_run_with_lots_of_std_err(self):
        # Issue #8386 - this command used to timeout.
        _, stderr, rc = run_command(Commands.RUN, "python", "-c", "import sys; print('x' * int(10000), file=sys.stderr)")
        assert rc == 0
        assert "xxx" in stderr