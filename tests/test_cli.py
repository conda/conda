import sys
import json
import unittest

import conda.cli as cli
from conda.cli.common import arg2spec, spec_from_line

# Use the Python 2 StringIO when available because it works with str
# (io.StringIO always expects unicode)
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

try:
    StringClass = unicode
except NameError:
    StringClass = str


class TestArg2Spec(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(arg2spec('python'), 'python')
        self.assertEqual(arg2spec('python=2.6'), 'python 2.6*')
        self.assertEqual(arg2spec('ipython=0.13.2'), 'ipython 0.13.2*')
        self.assertEqual(arg2spec('ipython=0.13.0'), 'ipython 0.13|0.13.0*')
        self.assertEqual(arg2spec('foo=1.3.0=3'), 'foo 1.3.0 3')

    def test_pip_style(self):
        self.assertEqual(arg2spec('foo>=1.3'), 'foo >=1.3')
        self.assertEqual(arg2spec('zope.int>=1.3,<3.0'), 'zope.int >=1.3,<3.0')
        self.assertEqual(arg2spec('numpy >=1.9'), 'numpy >=1.9')

    def test_invalid(self):
        self.assertRaises(SystemExit, arg2spec, '!xyz 1.3')


class TestSpecFromLine(unittest.TestCase):

    def test_invalid(self):
        self.assertEqual(spec_from_line('='), None)
        self.assertEqual(spec_from_line('foo 1.0'), None)

    def test_conda_style(self):
        self.assertEqual(spec_from_line('foo'), 'foo')
        self.assertEqual(spec_from_line('foo=1.0'), 'foo 1.0')
        self.assertEqual(spec_from_line('foo=1.0*'), 'foo 1.0*')
        self.assertEqual(spec_from_line('foo=1.0|1.2'), 'foo 1.0|1.2')
        self.assertEqual(spec_from_line('foo=1.0=2'), 'foo 1.0 2')

    def test_pip_style(self):
        self.assertEqual(spec_from_line('foo>=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo >=1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('FOO-Bar >=1.0'), 'foo-bar >=1.0')
        self.assertEqual(spec_from_line('foo >= 1.0'), 'foo >=1.0')
        self.assertEqual(spec_from_line('foo > 1.0'), 'foo >1.0')
        self.assertEqual(spec_from_line('foo != 1.0'), 'foo !=1.0')
        self.assertEqual(spec_from_line('foo <1.0'), 'foo <1.0')
        self.assertEqual(spec_from_line('foo >=1.0 , < 2.0'), 'foo >=1.0,<2.0')


def capture_with_argv(*argv):
    sys.argv = argv
    stdout, stderr = StringIO(), StringIO()
    oldstdout, oldstderr = sys.stdout, sys.stderr
    sys.stdout = stdout
    sys.stderr = stderr
    try:
        cli.main()
    except SystemExit:
        pass
    sys.stdout = oldstdout
    sys.stderr = oldstderr

    stdout.seek(0)
    stderr.seek(0)
    return stdout.read(), stderr.read()


def capture_json_with_argv(*argv):
    stdout, stderr = capture_with_argv(*argv)
    if stderr:
        # TODO should be exception
        return stderr

    try:
        return json.loads(stdout)
    except ValueError:
        print(stdout, stderr)
        raise


class TestJson(unittest.TestCase):
    def assertJsonError(self, res):
        self.assertIsInstance(res, dict)
        self.assertTrue('error' in res)

    def test_info(self):
        res = capture_json_with_argv('conda', 'info', '--json')
        keys = ('channels', 'conda_version', 'default_prefix', 'envs',
                'envs_dirs', 'is_foreign', 'pkgs_dirs', 'platform',
                'python_version', 'rc_path', 'root_prefix', 'root_writable')
        self.assertTrue(all(key in res for key in keys))

        res = capture_json_with_argv('conda', 'info', 'conda', '--json')
        self.assertIsInstance(res, dict)
        self.assertTrue('conda' in res)
        self.assertIsInstance(res['conda'], list)

    def test_launch(self):
        res = capture_json_with_argv('conda', 'launch', 'not_installed', '--json')
        self.assertJsonError(res)

        res = capture_json_with_argv('conda', 'launch', 'not_installed-0.1-py27_0.tar.bz2', '--json')
        self.assertJsonError(res)

    def test_list(self):
        res = capture_json_with_argv('conda', 'list', '--json')
        self.assertIsInstance(res, list)

        res = capture_json_with_argv('conda', 'list', '-r', '--json')
        self.assertTrue(isinstance(res, list) or
                        (isinstance(res, dict) and 'error' in res))

        res = capture_json_with_argv('conda', 'list', 'ipython', '--json')
        self.assertIsInstance(res, list)

        res = capture_json_with_argv('conda', 'list', '--name', 'nonexistent', '--json')
        self.assertJsonError(res)

        res = capture_json_with_argv('conda', 'list', '--name', 'nonexistent', '-r', '--json')
        self.assertJsonError(res)

    def test_search(self):
        res = capture_json_with_argv('conda', 'search', '--json')
        self.assertIsInstance(res, dict)
        self.assertIsInstance(res['_license'], list)
        self.assertIsInstance(res['_license'][0], dict)
        keys = ('build', 'channel', 'extracted', 'features', 'fn',
                'installed', 'version')
        self.assertTrue(all(key in res['_license'][0] for key in keys))
        for res in (capture_json_with_argv('conda', 'search', 'ipython', '--json'),
            capture_json_with_argv('conda', 'search', '--unknown', '--json'),
            capture_json_with_argv('conda', 'search', '--use-index-cache', '--json'),
            capture_json_with_argv('conda', 'search', '--outdated', '--json'),
            capture_json_with_argv('conda', 'search', '-c', 'https://conda.binstar.org/asmeurer', '--json'),
            capture_json_with_argv('conda', 'search', '-c', 'https://conda.binstar.org/asmeurer', '--override-channels', '--json'),
            capture_json_with_argv('conda', 'search', '--platform', 'win-32', '--json'),):
            self.assertIsInstance(res, dict)

        res = capture_json_with_argv('conda', 'search', '*', '--json')
        self.assertJsonError(res)

        res = capture_json_with_argv('conda', 'search', '--canonical', '--json')
        self.assertIsInstance(res, list)
        self.assertIsInstance(res[0], StringClass)


if __name__ == '__main__':
    unittest.main()
