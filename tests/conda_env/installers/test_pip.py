import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from conda_env.installers import pip
from conda.exceptions import CondaValueError

class PipInstallerTest(unittest.TestCase):
    def test_straight_install(self):
        with mock.patch.object(pip.subprocess, 'Popen') as popen:
            popen.return_value.returncode = 0
            with mock.patch.object(pip, 'pip_args') as pip_args:
                pip_args.return_value = ['pip']

                pip.install('/some/prefix', ['foo'], '', '')

                popen.assert_called_with(['pip', 'install', 'foo'],
                                         universal_newlines=True)
                self.assertEqual(1, popen.return_value.communicate.call_count)

    def test_stops_on_exception(self):
        with mock.patch.object(pip.subprocess, 'Popen') as popen:
            popen.return_value.returncode = 22
            with mock.patch.object(pip, 'pip_args') as pip_args:
                # make sure that installed doesn't bail early
                pip_args.return_value = ['pip']

                self.assertRaises(CondaValueError, pip.install,
                                  '/some/prefix', ['foo'], '', '')
