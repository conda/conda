import shutil
import tempfile
from unittest import TestCase
from tests.test_create import run_command, Commands
from unittest import mock
from conda.exceptions import UnsatisfiableError
from conda.models.match_spec import MatchSpec
from conda.resolve import Resolve


class TestCliInstall(TestCase):
    def setUp(self):
        self.prefix = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.prefix)

    def test_conda_list(self):
        bad_deps = {'python': {((MatchSpec("statistics"), MatchSpec("python[version='>=2.7,<2.8.0a0']")), 'python=3')}}

        run_command(Commands.CREATE, self.prefix, 'python=3.7')
        with mock.patch.object(Resolve, 'find_conflicts', return_value=bad_deps) as monkey:
            with self.assertRaises(UnsatisfiableError):
                stdout, stderr, _ = run_command(Commands.INSTALL, self.prefix, 'statistics')
            self.assertEqual(monkey.call_count, 1)
