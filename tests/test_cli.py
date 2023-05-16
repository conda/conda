# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import re
import stat
import unittest
import uuid
from unittest.mock import patch

import pytest

from conda.base.constants import on_win
from conda.base.context import context
from conda.gateways.disk.delete import rm_rf
from conda.testing import TmpEnvFixture
from conda.testing.helpers import capture_json_with_argv, run_inprocess_conda_command
from conda.testing.integration import Commands, run_command


@pytest.mark.usefixtures("tmpdir")
class TestJson(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def empty_env_tmpdir(self, tmpdir):
        # TODO :: Figure out if the pkgcache and a way to look for alternatives until one is found and add
        #         a warning about it.
        """
        # Slightly fancier, "works on my computer", using the last 3 dirs is probably a pytest-ism?
        self.tmpdir = os.path.join('opt', 'conda.tmp', *(str(tmpdir).split(os.sep)[-3:]))
        try:
            try:
                rm_rf(self.tmpdir)
            except:
                pass
            os.makedirs(self.tmpdir)
        except:
            self.tmpdir = str(tmpdir)
        """
        self.tmpdir = str(tmpdir)
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

        res = capture_json_with_argv(
            "conda config --get channels --file tempfile.rc --json"
        )
        self.assertJsonSuccess(res)

        res = capture_json_with_argv(
            "conda config --get channels --file tempfile.rc --file tempfile.rc --json"
        )
        self.assertJsonSuccess(res)

        res = capture_json_with_argv("conda config --get use_pip --json")
        self.assertJsonSuccess(res)

    @pytest.mark.integration
    @patch(
        "conda.core.envs_manager.get_user_environments_txt_file",
        return_value=os.devnull,
    )
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
        self.assertTrue(
            isinstance(res, list) or (isinstance(res, dict) and "error" in res)
        )

        res = capture_json_with_argv("conda list ipython --json")
        self.assertIsInstance(res, list)

        stdout, stderr, rc = run_inprocess_conda_command(
            "conda list --name nonexistent --json"
        )
        assert (
            json.loads(stdout.strip())["exception_name"]
            == "EnvironmentLocationNotFound"
        )
        assert stderr == ""
        assert rc > 0

        stdout, stderr, rc = run_inprocess_conda_command(
            "conda list --name nonexistent --revisions --json"
        )
        assert (
            json.loads(stdout.strip())["exception_name"]
            == "EnvironmentLocationNotFound"
        )
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
        assert (
            json.loads(stdout.strip())["exception_name"]
            == "EnvironmentLocationNotFound"
        )
        assert stderr == ""
        assert rc > 0
        assert mockable_context_envs_dirs.call_count > 0

    @pytest.mark.integration
    def test_search_0(self):
        # searching for everything is quite slow; search without name, few
        # matching packages. py_3 is not a special build tag, but there are just
        # a few of them in defaults.
        stdout, stderr, rc = run_inprocess_conda_command(
            "conda search *[build=py_3] --json --override-channels -c defaults"
        )
        assert stderr == ""
        assert rc is None

        res = json.loads(stdout)

        # happens to have py_3 build in noarch
        package_name = "pydotplus"

        self.assertIsInstance(res, dict)
        self.assertIsInstance(res[package_name], list)
        self.assertIsInstance(res[package_name][0], dict)
        keys = ("build", "channel", "fn", "version")
        for key in keys:
            self.assertIn(key, res[package_name][0])
        assert res[package_name][0]["build"] == "py_3"

    @pytest.mark.integration
    def test_search_1(self):
        self.assertIsInstance(
            capture_json_with_argv(
                "conda search ipython --json --override-channels -c defaults"
            ),
            dict,
        )

    @pytest.mark.integration
    def test_search_2(self, tmp_env: TmpEnvFixture):
        with tmp_env() as prefix:
            stdout, stderr, _ = run_command(
                Commands.SEARCH,
                prefix,
                "python",
                "--override-channels",
                "-c",
                "defaults",
                use_exception_handler=True,
            )
            result = stdout.replace("Loading channels: ...working... done", "")
            assert re.search(
                r"""python\s*
                \d*\.\d*\.\d*\s*
                \w+\s*
                pkgs/main""",
                result,
                re.VERBOSE,
            )

            # exact match not found, search wildcards
            stdout, _, _ = run_command(
                Commands.SEARCH,
                prefix,
                "ython",
                "--override-channels",
                "-c",
                "defaults",
                use_exception_handler=True,
            )

            assert re.search(
                r"""python\s*
                \d*\.\d*\.\d*\s*
                \w+\s*
                pkgs/main""",
                result,
                re.VERBOSE,
            )

    @pytest.mark.integration
    def test_search_3(self, tmp_env: TmpEnvFixture):
        with tmp_env() as prefix:
            stdout, stderr, _ = run_command(
                Commands.SEARCH,
                prefix,
                "*/linux-64::nose==1.3.7[build=py37_2]",
                "--info",
                "--override-channels",
                "-c",
                "defaults",
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
            capture_json_with_argv(
                "conda search --json --override-channels -c defaults --use-index-cache python"
            ),
            dict,
        )

    @pytest.mark.integration
    def test_search_5(self):
        self.assertIsInstance(
            capture_json_with_argv(
                "conda search --platform win-32 --json --override-channels -c defaults python"
            ),
            dict,
        )


@pytest.mark.integration
def test_search_envs():
    for extra in ("--info", "--json", ""):
        stdout, _, _ = run_inprocess_conda_command(f"conda search --envs {extra} conda")
        if "--json" not in extra:
            assert "Searching environments" in stdout
        assert "conda" in stdout


def test_run_returns_int(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        stdout, stderr, result = run_inprocess_conda_command(
            f"conda run -p {prefix} echo hi"
        )

        assert isinstance(result, int)


def test_run_returns_zero_errorlevel(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        stdout, stderr, result = run_inprocess_conda_command(
            f"conda run -p {prefix} exit 0"
        )

        assert result == 0


def test_run_returns_nonzero_errorlevel(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        stdout, stderr, result = run_inprocess_conda_command(
            f'conda run -p "{prefix}" exit 5'
        )

        assert result == 5


def test_run_uncaptured(capfd, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        random_text = uuid.uuid4().hex
        stdout, stderr, result = run_inprocess_conda_command(
            f"conda run -p {prefix} --no-capture-output echo {random_text}"
        )

        assert result == 0
        # Output is not captured
        assert stdout == ""

        # Check that the expected output is somewhere between the conda logs
        captured = capfd.readouterr()
        assert random_text in captured.out


@pytest.mark.skipif(on_win, reason="cannot make readonly env on win")
def test_run_readonly_env(request, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
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
            f"conda run -p {prefix} exit 0"
        )

        # Reset permissions in case all goes according to plan
        reset_permissions()

        assert result == 0


def test_main():
    with pytest.raises(SystemExit):
        __import__("conda.__main__")
