# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import shutil
import tempfile
import unittest
from logging import getLogger

import pytest

from conda.testing.integration import Commands, run_command

log = getLogger(__name__)


class TestLinkOrder(unittest.TestCase):
    def setUp(self):
        self.prefix = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.prefix)

    @pytest.mark.integration
    def test_link_order_post_link_actions(self):
        stdout, stderr, _ = run_command(
            Commands.CREATE, self.prefix, "c_post_link_package", "-c", "conda-test"
        )
        assert stderr == ""

    @pytest.mark.integration
    def test_link_order_post_link_depend(self):
        stdout, stderr, _ = run_command(
            Commands.CREATE, self.prefix, "e_post_link_package", "-c", "conda-test"
        )
        assert stderr == ""
