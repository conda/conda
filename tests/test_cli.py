# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import json
import unittest
import uuid
import os
import stat
from mock import patch

import pytest

from conda.base.constants import on_win
from conda.base.context import context
from conda.common.io import captured
from conda.gateways.disk.delete import rm_rf
from conda.common.compat import text_type
from conda.testing.helpers import capture_json_with_argv, run_inprocess_conda_command
from conda.testing.integration import Commands, run_command, make_temp_env, make_temp_prefix


@pytest.mark.usefixtures("tmpdir")
class TestJson(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def empty_env_tmpdir(self, tmpdir):
        # TODO :: Figure out if the pkgcache and a way to look for alternatives until one is found and add
        #         a warning about it.
        """
        # Slightly fancier, "works on my computer", using the last 3 dirs is probably a pytest-ism?
        self.tmpdir = os.path.join('opt', 'conda.tmp', *(text_type(tmpdir).split(os.sep)[-3:]))
        try:
            try:
                rm_rf(self.tmpdir)
            except:
                pass
            os.makedirs(self.tmpdir)
        except:
            self.tmpdir = text_type(tmpdir)
        """
        self.tmpdir = text_type(tmpdir)
        return self.tmpdir

    def assertJsonSuccess(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)

    def assertJsonError(self, res):
        self.assertIsInstance(res, dict)
        self.assertIn("error", res)

    def tearDown(self):
        rm_rf("tempfile.rc")

    def test_config(self):
        res = capture_json_with_argv("conda config --get --json")
        self.assertJsonSuccess(res)

        res = capture_json_with_argv("conda config --get channels --json")
        self.assertJsonSuccess(res)

        if context.root_writable:
            res = capture_json_with_argv("conda config --get channels --system --json")
            self.assertJsonSuccess(res)

        res = capture_json_with_argv("conda config --get channels --file tempfile.rc --json")
        self.assertJsonSuccess(res)

        res = capture_json_with_argv(
            "conda config --get channels --file tempfile.rc --file tempfile.rc --json"
        )
        self.assertJsonSuccess(res)

        res = capture_json_with_argv("conda config --get use_pip --json")
        self.assertJsonSuccess(res)

    @pytest.mark.integration
    @patch("conda.core.envs_manager.get_user_environments_txt_file", return_value=os.devnull)
    def test_info(self, _mocked_guetf):
        res = capture_json_with_argv("conda info --json")
        keys = (
            "channels",
            "conda_version",
            "default_prefix",
            "envs",
            "envs_dirs",
            "pkgs_dirs",
            "platform",
            "python_version",
            "rc_path",
            "root_prefix",
            "root_writable",
        )
        self.assertIsInstance(res, dict)
        for key in keys:
            assert key in res

        res = capture_json_with_argv(
            "conda info conda --json", disallow_stderr=False, ignore_stderr=True
        )
        self.assertIsInstance(res, dict)
        self.assertIn("conda", res)
        self.assertIsInstance(res["conda"], list)
        assert _mocked_guetf.call_count > 0

    @pytest.mark.usefixtures("empty_env_tmpdir")
    @patch("conda.base.context.mockable_context_envs_dirs")
    def test_list(self, mockable_context_envs_dirs):
        mockable_context_envs_dirs.return_value = (self.tmpdir,)
        res = capture_json_with_argv("conda list --json")
        self.assertIsInstance(res, list)

        res = capture_json_with_argv("conda list -r --json")
        self.assertTrue(isinstance(res, list) or (isinstance(res, dict) and "error" in res))

        res = capture_json_with_argv("conda list ipython --json")
        self.assertIsInstance(res, list)

        stdout, stderr, rc = run_inprocess_conda_command("conda list --name nonexistent --json")
        assert json.loads(stdout.strip())["exception_name"] == "EnvironmentLocationNotFound"
        assert stderr == ""
        assert rc > 0

        stdout, stderr, rc = run_inprocess_conda_command(
            "conda list --name nonexistent --revisions --json"
        )
        assert json.loads(stdout.strip())["exception_name"] == "EnvironmentLocationNotFound"
        assert stderr == ""
        assert rc > 0

        assert mockable_context_envs_dirs.call_count > 0

    @pytest.mark.usefixtures("empty_env_tmpdir")
    @patch("conda.base.context.mockable_context_envs_dirs")
    def test_compare(self, mockable_context_envs_dirs):
        mockable_context_envs_dirs.return_value = (self.tmpdir,)
        stdout, stderr, rc = run_inprocess_conda_command(
            "conda compare --name nonexistent tempfile.rc --json"
        )
        assert json.loads(stdout.strip())["exception_name"] == "EnvironmentLocationNotFound"
        assert stderr == ""
        assert rc > 0
        assert mockable_context_envs_dirs.call_count > 0

    @pytest.mark.integration
    def test_search_0(self):
        with captured():
            res = capture_json_with_argv("conda search --json")
        self.assertIsInstance(res, dict)
        self.assertIsInstance(res["conda"], list)
        self.assertIsInstance(res["conda"][0], dict)
        keys = ("build", "channel", "fn", "version")
        for key in keys:
            self.assertIn(key, res["conda"][0])

        stdout, stderr, rc = run_inprocess_conda_command("conda search * --json")
        assert stderr == ""
        assert rc is None

    @pytest.mark.integration
    def test_search_1(self):
        self.assertIsInstance(capture_json_with_argv("conda search ipython --json"), dict)

    @pytest.mark.integration
    def test_search_2(self):
        with make_temp_env() as prefix:
            stdout, stderr, _ = run_command(
                Commands.SEARCH, prefix, "nose", use_exception_handler=True
            )
            result = stdout.replace("Loading channels: ...working... done", "")

            assert "nose                           1.3.7          py37_2  pkgs/main" in result

    @pytest.mark.integration
    def test_search_3(self):
        with make_temp_env() as prefix:
            stdout, stderr, _ = run_command(
                Commands.SEARCH,
                prefix,
                "*/linux-64::nose==1.3.7[build=py37_2]",
                "--info",
                use_exception_handler=True,
            )
            result = stdout.replace("Loading channels: ...working... done", "")
            assert "file name   : nose-1.3.7-py37_2" in result
            assert "name        : nose" in result
            assert (
                "url         : https://repo.anaconda.com/pkgs/main/linux-64/nose-1.3.7-py37_2"
                in result
            )
            # assert "md5         : ff390a1e44d77e54914ca1a2c9e75445" in result

    @pytest.mark.integration
    def test_search_4(self):
        self.assertIsInstance(
            capture_json_with_argv("conda search --json --use-index-cache"), dict
        )

    @pytest.mark.integration
    def test_search_5(self):
        self.assertIsInstance(
            capture_json_with_argv("conda search --platform win-32 --json"), dict
        )


def test_run_returns_int():
    prefix = make_temp_prefix(name="test")
    with make_temp_env(prefix=prefix):
        stdout, stderr, result = run_inprocess_conda_command(
            "conda run -p {} echo hi".format(prefix)
        )

        assert isinstance(result, int)


def test_run_returns_zero_errorlevel():
    prefix = make_temp_prefix(name="test")
    with make_temp_env(prefix=prefix):
        stdout, stderr, result = run_inprocess_conda_command(
            "conda run -p {} exit 0".format(prefix)
        )

        assert result == 0


def test_run_returns_nonzero_errorlevel():
    prefix = make_temp_prefix(name="test")
    with make_temp_env(prefix=prefix) as prefix:
        stdout, stderr, result = run_inprocess_conda_command(
            'conda run -p "{}" exit 5'.format(prefix)
        )

        assert result == 5


def test_run_uncaptured(capfd):
    prefix = make_temp_prefix(name="test")
    with make_temp_env(prefix=prefix):
        random_text = uuid.uuid4().hex
        stdout, stderr, result = run_inprocess_conda_command(
            "conda run -p {} --no-capture-output echo {}".format(prefix, random_text)
        )

        assert result == 0
        # Output is not captured
        assert stdout == ""

        # Check that the expected output is somewhere between the conda logs
        captured = capfd.readouterr()
        assert random_text in captured.out


@pytest.mark.skipif(on_win, reason="cannot make readonly env on win")
def test_run_readonly_env(request):
    prefix = make_temp_prefix(name="test")
    with make_temp_env(prefix=prefix) as prefix:
        # Remove write permissions
        current = stat.S_IMODE(os.lstat(prefix).st_mode)
        os.chmod(prefix, current & ~stat.S_IWRITE)

        # reset permissions in case something goes wrong
        def reset_permissions():
            if os.path.exists(prefix):
                os.chmod(prefix, current)

        request.addfinalizer(reset_permissions)

        # Confirm we do not have write access.
        raise_ok = False
        try:
            open(os.path.join(prefix, "test.txt"), "w+")
        except PermissionError:
            raise_ok = True

        assert raise_ok

        stdout, stderr, result = run_inprocess_conda_command(
            "conda run -p {} exit 0".format(prefix)
        )

        # Reset permissions in case all goes according to plan
        reset_permissions()

        assert result == 0
