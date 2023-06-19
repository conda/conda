# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import unittest

from conda_env import env
from conda_env.specs.requirements import RequirementsSpec

from .. import support_file


class TestRequiremets(unittest.TestCase):
    def test_no_environment_file(self):
        spec = RequirementsSpec(name=None, filename="not-a-file")
        self.assertEqual(spec.can_handle(), False)

    def test_no_name(self):
        spec = RequirementsSpec(filename=support_file("requirements.txt"))
        self.assertEqual(spec.can_handle(), False)

    def test_req_file_and_name(self):
        spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
        self.assertTrue(spec.can_handle())

    def test_environment(self):
        spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
        self.assertIsInstance(spec.environment, env.Environment)
        self.assertEqual(spec.environment.dependencies["conda"][0], "flask==0.10.1")
