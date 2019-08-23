import tempfile
from unittest import TestCase
from tests.test_create import run_command, Commands

import pytest

from conda.models.match_spec import MatchSpec
from conda.exceptions import UnsatisfiableError
from conda.gateways.disk.delete import rm_rf

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestCliInstall(TestCase):
    def setUp(self):
        self.prefix = tempfile.mkdtemp()
        self.testenv = tempfile.mkdtemp()
        run_command(Commands.CREATE, self.prefix, 'python=3.7')

    def tearDown(self):
        rm_rf(self.prefix)
        rm_rf(self.testenv)

    @pytest.mark.integration
    def test_find_conflicts_called_once(self):
        bad_deps = {'python': {((MatchSpec("statistics"), MatchSpec("python[version='>=2.7,<2.8.0a0']")), 'python=3')}}

        with patch('conda.resolve.Resolve.find_conflicts') as monkey:
            monkey.side_effect = UnsatisfiableError(bad_deps, strict=True)
            with self.assertRaises(UnsatisfiableError):
                # Statistics is a py27 only package allowing us a simple unsatisfiable case
                stdout, stderr, _ = run_command(Commands.INSTALL, self.prefix, 'statistics')
            self.assertEqual(monkey.call_count, 1)
            monkey.reset_mock()
            with self.assertRaises(UnsatisfiableError):
                stdout, stderr, _ = run_command(Commands.INSTALL, self.prefix, 'statistics', '--freeze-installed')
            self.assertEqual(monkey.call_count, 1)
            monkey.reset_mock()
            with self.assertRaises(UnsatisfiableError):
                stdout, stderr, _ = run_command(Commands.CREATE, self.testenv, 'statistics', 'python=3.7')
            self.assertEqual(monkey.call_count, 1)
