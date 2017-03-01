import json

import unittest

from conda.base.context import context
from conda.gateways.disk.delete import rm_rf
import pytest

from conda.cli.common import arg2spec, spec_from_line
from conda.common.io import captured
from conda.common.compat import text_type
from conda.exceptions import CondaValueError

from tests.helpers import capture_json_with_argv, assert_in, run_inprocess_conda_command


class TestArg2Spec(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(arg2spec('python'), 'python')
        self.assertEqual(arg2spec('python=2.6'), 'python 2.6*')
        self.assertEqual(arg2spec('python=2.6*'), 'python 2.6*')
        self.assertEqual(arg2spec('ipython=0.13.2'), 'ipython 0.13.2*')
        self.assertEqual(arg2spec('ipython=0.13.0'), 'ipython 0.13.0*')
        self.assertEqual(arg2spec('foo=1.3.0=3'), 'foo 1.3.0 3')

    def test_pip_style(self):
        self.assertEqual(arg2spec('foo>=1.3'), 'foo >=1.3')
        self.assertEqual(arg2spec('zope.int>=1.3,<3.0'), 'zope.int >=1.3,<3.0')
        self.assertEqual(arg2spec('numpy >=1.9'), 'numpy >=1.9')

    def test_invalid(self):
        self.assertRaises(CondaValueError, arg2spec, '!xyz 1.3')


class TestSpecFromLine(unittest.TestCase):

    def test_invalid(self):
        self.assertEqual(spec_from_line('='), None)
        self.assertEqual(spec_from_line('foo 1.0'), None)

    def test_comment(self):
        self.assertEqual(spec_from_line('foo # comment'), 'foo')
        self.assertEqual(spec_from_line('foo ## comment'), 'foo')

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


class TestJson(unittest.TestCase):
    def assertJsonSuccess(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn('success', res)

    def assertJsonError(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn('error', res)

    def tearDown(self):
        rm_rf('tempfile.rc')

    # def test_clean(self):
    #     res = capture_json_with_argv('conda', 'clean', '--index-cache', '--lock',
    #                                  '--packages', '--tarballs', '--json')
    #     self.assertJsonSuccess(res)

    @pytest.mark.integration
    def test_config(self):
        res = capture_json_with_argv('conda config --get --json')
        self.assertJsonSuccess(res)

        res = capture_json_with_argv('conda config --get channels --json')
        self.assertJsonSuccess(res)

        if context.root_writable:
            res = capture_json_with_argv('conda config --get channels --system --json')
            self.assertJsonSuccess(res)

        res = capture_json_with_argv('conda config --get channels --file tempfile.rc --json')
        self.assertJsonSuccess(res)

        res = capture_json_with_argv('conda config --get channels --file tempfile.rc --file tempfile.rc --json')
        self.assertJsonSuccess(res)

        # res = capture_json_with_argv('conda', 'config', '--add', 'channels',
        #                              'binstar', '--json')
        # self.assertIsInstance(res, dict)
        #
        # res = capture_json_with_argv('conda', 'config', '--add', 'channels',
        #                              'binstar', '--force', '--json')
        # self.assertJsonSuccess(res)
        #
        # res = capture_json_with_argv('conda', 'config', '--remove', 'channels',
        #                              'binstar', '--json')
        # self.assertJsonError(res)
        #
        # res = capture_json_with_argv('conda', 'config', '--remove', 'channels',
        #                              'binstar', '--force', '--json')
        # self.assertJsonSuccess(res)
        #
        # res = capture_json_with_argv('conda', 'config', '--remove', 'channels',
        #                              'nonexistent', '--force', '--json')
        # self.assertJsonError(res)
        #
        # res = capture_json_with_argv('conda', 'config', '--remove', 'envs_dirs',
        #                              'binstar', '--json')
        # self.assertJsonError(res)
        #
        # res = capture_json_with_argv('conda', 'config', '--set', 'use_pip',
        #                              'yes', '--json')
        # self.assertJsonSuccess(res)

        res = capture_json_with_argv('conda config --get use_pip --json')
        self.assertJsonSuccess(res)
        # self.assertTrue(res['get']['use_pip'])

        # res = capture_json_with_argv('conda', 'config', '--remove-key', 'use_pip',
        #                              '--json')
        # self.assertJsonError(res)
        #
        # res = capture_json_with_argv('conda', 'config', '--remove-key', 'use_pip',
        #                              '--force', '--json')
        # self.assertJsonSuccess(res)q
        #
        # res = capture_json_with_argv('conda', 'config', '--remove-key', 'use_pip',
        #                              '--force', '--json')
        # self.assertJsonError(res)

    @pytest.mark.slow
    @pytest.mark.integration
    def test_info(self):
        res = capture_json_with_argv('conda info --json')
        keys = ('channels', 'conda_version', 'default_prefix', 'envs',
                'envs_dirs', 'pkgs_dirs', 'platform',
                'python_version', 'rc_path', 'root_prefix', 'root_writable')
        self.assertIsInstance(res, dict)
        for key in keys:
            assert key in res

        res = capture_json_with_argv('conda info conda --json')
        self.assertIsInstance(res, dict)
        self.assertIn('conda', res)
        self.assertIsInstance(res['conda'], list)

    # def test_install(self):
    #     res = capture_json_with_argv('conda', 'install', 'pip', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'update', 'pip', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'remove', 'pip', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'remove', 'pip', '--json', '--quiet')
    #     self.assertJsonError(res)
    #
    #     res = capture_json_with_argv('conda', 'update', 'pip', '--json', '--quiet')
    #     self.assertJsonError(res)
    #
    #     res = capture_json_with_argv('conda', 'install', 'pip=1.5.5', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'install', '=', '--json', '--quiet')
    #     self.assertJsonError(res)
    #
    #     res = capture_json_with_argv('conda', 'remove', '-n', 'testing',
    #                                  '--all', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'remove', '-n', 'testing',
    #                                  '--all', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'remove', '-n', 'testing2',
    #                                  '--all', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'create', '-n', 'testing',
    #                                  'python', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'install', '-n', 'testing',
    #                                  'python', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'install', '--dry-run',
    #                                  'python', '--json', '--quiet')
    #     self.assertJsonSuccess(res)
    #
    #     res = capture_json_with_argv('conda', 'create', '--clone', 'testing',
    #                                  '-n', 'testing2', '--json', '--quiet')
    #     self.assertJsonSuccess(res)

    @pytest.mark.integration
    def test_list(self):
        res = capture_json_with_argv('conda list --json')
        self.assertIsInstance(res, list)

        res = capture_json_with_argv('conda list -r --json')
        self.assertTrue(isinstance(res, list) or
                        (isinstance(res, dict) and 'error' in res))

        res = capture_json_with_argv('conda list ipython --json')
        self.assertIsInstance(res, list)

        stdout, stderr, rc = run_inprocess_conda_command('conda list --name nonexistent --json')
        assert json.loads(stdout.strip())['exception_name'] == 'CondaEnvironmentNotFoundError'
        assert stderr == ''
        assert rc > 0

        stdout, stderr, rc = run_inprocess_conda_command('conda list --name nonexistent --revisions --json')
        assert json.loads(stdout.strip())['exception_name'] == 'CondaEnvironmentNotFoundError'
        assert stderr == ''
        assert rc > 0

    @pytest.mark.integration
    def test_search_0(self):
        with captured():
            res = capture_json_with_argv('conda search --json')
        self.assertIsInstance(res, dict)
        self.assertIsInstance(res['conda'], list)
        self.assertIsInstance(res['conda'][0], dict)
        keys = ('build', 'channel', 'extracted', 'features', 'fn',
                'installed', 'version')
        for key in keys:
            self.assertIn(key, res['conda'][0])

        stdout, stderr, rc = run_inprocess_conda_command('conda search * --json')
        assert json.loads(stdout.strip())['exception_name'] == 'CommandArgumentError'
        assert stderr == ''
        assert rc > 0

        res = capture_json_with_argv('conda search --canonical --json')
        self.assertIsInstance(res, list)
        self.assertIsInstance(res[0], text_type)

    @pytest.mark.integration
    def test_search_1(self):
        self.assertIsInstance(capture_json_with_argv('conda search ipython --json'), dict)

    @pytest.mark.integration
    def test_search_2(self):
        self.assertIsInstance(capture_json_with_argv('conda search --unknown --json'), dict)

    @pytest.mark.integration
    def test_search_3(self):
        self.assertIsInstance(capture_json_with_argv('conda search --json --use-index-cache'), dict)

    @pytest.mark.integration
    def test_search_4(self):
        self.assertIsInstance(capture_json_with_argv('conda search --json --outdated'), dict)

    @pytest.mark.integration
    def test_search_5(self):
        self.assertIsInstance(capture_json_with_argv('conda search -c https://conda.anaconda.org/conda --json nose'), dict)

    @pytest.mark.integration
    def test_search_6(self):
        self.assertIsInstance(capture_json_with_argv('conda search -c https://conda.anaconda.org/conda --override-channel --json nose'), dict)

    @pytest.mark.integration
    def test_search_7(self):
        self.assertIsInstance(capture_json_with_argv('conda search --platform win-32 --json'), dict)

