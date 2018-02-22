import json
import unittest

from conda._vendor.auxlib.ish import dals
import pytest

from conda.base.context import context
from conda.common.io import captured
from conda.gateways.disk.delete import rm_rf
from tests.helpers import capture_json_with_argv, run_inprocess_conda_command


class TestJson(unittest.TestCase):
    def assertJsonSuccess(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn('success', res)

    def assertJsonError(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn('error', res)

    def tearDown(self):
        rm_rf('tempfile.rc')

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

        res = capture_json_with_argv('conda config --get use_pip --json')
        self.assertJsonSuccess(res)

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

    def test_list(self):
        res = capture_json_with_argv('conda list --json')
        self.assertIsInstance(res, list)

        res = capture_json_with_argv('conda list -r --json')
        self.assertTrue(isinstance(res, list) or
                        (isinstance(res, dict) and 'error' in res))

        res = capture_json_with_argv('conda list ipython --json')
        self.assertIsInstance(res, list)

        stdout, stderr, rc = run_inprocess_conda_command('conda list --name nonexistent --json')
        assert json.loads(stdout.strip())['exception_name'] == 'EnvironmentLocationNotFound'
        assert stderr == ''
        assert rc > 0

        stdout, stderr, rc = run_inprocess_conda_command('conda list --name nonexistent --revisions --json')
        assert json.loads(stdout.strip())['exception_name'] == 'EnvironmentLocationNotFound'
        assert stderr == ''
        assert rc > 0

    @pytest.mark.integration
    def test_search_0(self):
        with captured():
            res = capture_json_with_argv('conda search --json')
        self.assertIsInstance(res, dict)
        self.assertIsInstance(res['conda'], list)
        self.assertIsInstance(res['conda'][0], dict)
        keys = ('build', 'channel', 'fn', 'version')
        for key in keys:
            self.assertIn(key, res['conda'][0])

        stdout, stderr, rc = run_inprocess_conda_command('conda search * --json')
        assert stderr == ''
        assert rc is None

    @pytest.mark.integration
    def test_search_1(self):
        self.assertIsInstance(capture_json_with_argv('conda search ipython --json'), dict)

    @pytest.mark.integration
    def test_search_2(self):
        from tests.test_create import make_temp_env
        from tests.test_create import run_command
        from tests.test_create import Commands
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "nose", use_exception_handler=True)
            result = stdout.replace("Loading channels: ...working... done", "")

            assert "nose                      1.3.4          py34_0  pkgs/free" in result

    @pytest.mark.integration
    def test_search_3(self):
        from tests.test_create import make_temp_env
        from tests.test_create import run_command
        from tests.test_create import Commands
        with make_temp_env() as prefix:
            stdout, stderr = run_command(Commands.SEARCH, prefix, "*/linux-64::nose==1.3.7[build=py36_1]", "--info", use_exception_handler=True)
            result = stdout.replace("Loading channels: ...working... done", "")
            assert "file name   : nose-1.3.7-py36_1.tar.bz2" in result
            assert "name        : nose" in result
            assert "url         : https://repo.anaconda.com/pkgs/free/linux-64/nose-1.3.7-py36_1.tar.bz2" in result
            assert "md5         : f4f697f5ad4df9c8fe35357d269718a5" in result

    @pytest.mark.integration
    def test_search_4(self):
        self.assertIsInstance(capture_json_with_argv('conda search --json --use-index-cache'), dict)

    @pytest.mark.integration
    def test_search_5(self):
        self.assertIsInstance(capture_json_with_argv('conda search --platform win-32 --json'), dict)
