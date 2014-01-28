import unittest
import os
import subprocess

from conda.cli.common import arg2spec


class TestArg2Spec(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(arg2spec('python'), 'python')
        self.assertEqual(arg2spec('python=2.6'), 'python 2.6*')
        self.assertEqual(arg2spec('ipython=0.13.2'), 'ipython 0.13.2*')
        self.assertEqual(arg2spec('ipython=0.13.0'), 'ipython 0.13|0.13.0*')
        self.assertEqual(arg2spec('foo=1.3.0=3'), 'foo 1.3.0 3')

    def test_invalid_char(self):
        self.assertRaises(SystemExit, arg2spec, 'abc%def')
        self.assertRaises(SystemExit, arg2spec, '!xyz 1.3')

    def test_too_long(self):
        self.assertRaises(SystemExit, arg2spec, 'foo=1.3=2=4')

class CondaCLITest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.conda = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'conda')
        super(CondaCLITest, self).__init__(*args, **kwargs)

    def run_conda_command(self, *args):
        return subprocess.check_output((self.conda,) + args).decode('utf-8')


if __name__ == '__main__':
    unittest.main()
