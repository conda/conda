# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import re
import sys
from glob import glob
from itertools import chain, zip_longest
from json import loads as json_loads
from logging import getLogger
from os.path import (
    abspath,
    basename,
    dirname,
    exists,
    isdir,
    isfile,
    islink,
    join,
    lexists,
    relpath,
)
from pathlib import Path
from shutil import copyfile, rmtree
from subprocess import PIPE, Popen, check_call, check_output
from textwrap import dedent
from unittest.mock import patch
from uuid import uuid4

import pytest
import requests
from pytest import CaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture

from conda import CondaError, CondaMultiError
from conda.auxlib.ish import dals
from conda.base.constants import (
    CONDA_PACKAGE_EXTENSIONS,
    PREFIX_MAGIC_FILE,
    SafetyChecks,
)
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from conda.common.compat import ensure_text_type, on_mac, on_win
from conda.common.io import env_var, env_vars, stderr_log_level
from conda.common.iterators import groupby_to_dict as groupby
from conda.common.path import (
    get_bin_directory_short_path,
    get_python_site_packages_short_path,
    pyc_path,
)
from conda.common.serialize import json_dump, yaml_round_trip_load
from conda.core.index import get_reduced_index
from conda.core.package_cache_data import PackageCacheData
from conda.core.prefix_data import PrefixData, get_python_version_for_prefix
from conda.core.subdir_data import create_cache_dir
from conda.exceptions import (
    ArgumentError,
    CondaValueError,
    DirectoryNotACondaEnvironmentError,
    DisallowedPackageError,
    DryRunExit,
    EnvironmentLocationNotFound,
    OperationNotAllowed,
    PackageNotInstalledError,
    PackagesNotFoundError,
    RemoveError,
    SpecsConfigurationConflictError,
    UnsatisfiableError,
)
from conda.gateways.anaconda_client import read_binstar_tokens
from conda.gateways.disk.create import compile_multiple_pyc
from conda.gateways.disk.delete import path_is_clean, rm_rf
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.disk.update import touch
from conda.gateways.subprocess import (
    Response,
    subprocess_call,
    subprocess_call_with_clean_env,
)
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.models.version import VersionOrder
from conda.resolve import Resolve
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture
from conda.testing.integration import (
    BIN_DIRECTORY,
    PYTHON_BINARY,
    TEST_LOG_LEVEL,
    Commands,
    cp_or_copy,
    env_or_set,
    get_shortcut_dir,
    make_temp_channel,
    make_temp_env,
    make_temp_package_cache,
    make_temp_prefix,
    package_is_installed,
    reload_config,
    run_command,
    tempdir,
    which_or_where,
)

log = getLogger(__name__)
stderr_log_level(TEST_LOG_LEVEL, "conda")
stderr_log_level(TEST_LOG_LEVEL, "requests")


# all tests in this file are integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("parametrized_solver_fixture"),
]


@pytest.fixture(autouse=True)
def clear_package_cache() -> None:
    PackageCacheData.clear()


def test_install_python_and_search(
    path_factory: PathFactoryFixture,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    environment_txt = path_factory(suffix=".txt")
    environment_txt.touch()
    mocker.patch(
        "conda.core.envs_manager.get_user_environments_txt_file",
        return_value=environment_txt,
    )

    monkeypatch.setenv("CONDA_REGISTER_ENVS", "true")
    # regression test for #4513
    monkeypatch.setenv("CONDA_ALLOW_NON_CHANNEL_URLS", "true")
    channels = (
        "https://repo.continuum.io/pkgs/not-a-channel",
        "defaults",
        "conda-forge",
    )
    monkeypatch.setenv("CONDA_CHANNELS", ",".join(channels))
    reset_context()
    assert context.register_envs
    assert context.allow_non_channel_urls
    assert context.channels == channels

    with tmp_env("python") as prefix:
        assert (prefix / PYTHON_BINARY).exists()
        assert package_is_installed(prefix, "python")

        stdout, stderr, err = conda_cli("search", "python", "--json")
        assert len(json.loads(stdout)) == 1
        assert not stderr
        assert not err

        stdout, stderr, err = conda_cli("search", "python", "--json", "--envs")
        assert any(prefix.samefile(env["location"]) for env in json.loads(stdout))
        assert not stderr
        assert not err

        stdout, stderr, err = conda_cli("search", "python", "--envs")
        assert str(prefix) in stdout
        assert not stderr
        assert not err


def test_run_preserves_arguments(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python=3") as prefix:
        echo_args_py = prefix / "echo-args.py"
        echo_args_py.write_text("import sys\nfor arg in sys.argv[1:]: print(arg)")
        # If 'two two' were 'two' this test would pass.
        args = ("one", "two two", "three")
        stdout, stderr, code = conda_cli(
            "run",
            f"--prefix={prefix}",
            "python",
            echo_args_py,
            *args,
        )
        for value, expected in zip_longest(stdout.strip().splitlines(), args):
            assert value == expected
        assert not stderr
        assert not code


def test_create_install_update_remove_smoketest(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("python=3") as prefix:
        assert (prefix / PYTHON_BINARY).exists()
        assert package_is_installed(prefix, "python=3")

        conda_cli("install", f"--prefix={prefix}", "flask=2.0.1", "--yes")
        PrefixData._cache_.clear()
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "python=3")

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "--force-reinstall",
            "flask=2.0.1",
            "--yes",
        )
        PrefixData._cache_.clear()
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "python=3")

        conda_cli("update", f"--prefix={prefix}", "flask", "--yes")
        PrefixData._cache_.clear()
        assert not package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")

        conda_cli("remove", f"--prefix={prefix}", "flask", "--yes")
        PrefixData._cache_.clear()
        assert not package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")

        stdout, stderr, code = conda_cli("list", f"--prefix={prefix}", "--revisions")
        assert not stderr
        assert " (rev 4)\n" in stdout
        assert " (rev 5)\n" not in stdout

        conda_cli("install", f"--prefix={prefix}", "--revision", "0", "--yes")
        PrefixData._cache_.clear()
        assert not package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")


def test_install_broken_post_install_keeps_existing_folders():
    # regression test for https://github.com/conda/conda/issues/8258
    with make_temp_env("python=3.5") as prefix:
        assert exists(join(prefix, BIN_DIRECTORY))
        assert package_is_installed(prefix, "python=3")

        run_command(
            Commands.INSTALL,
            prefix,
            "-c",
            "conda-test",
            "failing_post_link",
            use_exception_handler=True,
        )
        assert exists(join(prefix, BIN_DIRECTORY))


def test_safety_checks():
    # This test uses https://anaconda.org/conda-test/spiffy-test-app/0.5/download/noarch/spiffy-test-app-0.5-pyh6afbcc8_0.tar.bz2
    # which is a modification of https://anaconda.org/conda-test/spiffy-test-app/1.0/download/noarch/spiffy-test-app-1.0-pyh6afabb7_0.tar.bz2
    # as documented in info/README within that package.
    # I also had to fix the post-link script in the package by adding quotation marks to handle
    # spaces in path names.

    with make_temp_env() as prefix:
        with open(join(prefix, "condarc"), "a") as fh:
            fh.write("safety_checks: enabled\n")
            fh.write("extra_safety_checks: true\n")
        reload_config(prefix)
        assert context.safety_checks is SafetyChecks.enabled

        with pytest.raises(CondaMultiError) as exc:
            run_command(
                Commands.INSTALL, prefix, "-c", "conda-test", "spiffy-test-app=0.5"
            )

        error_message = str(exc.value)
        message1 = dals(
            """
            The path 'site-packages/spiffy_test_app-1.0-py2.7.egg-info/top_level.txt'
            has an incorrect size.
              reported size: 32 bytes
              actual size: 16 bytes
            """
        )
        message2 = "has a sha256 mismatch."
        assert message1 in error_message
        assert message2 in error_message

        with open(join(prefix, "condarc"), "w") as fh:
            fh.write("safety_checks: warn\n")
            fh.write("extra_safety_checks: true\n")
        reload_config(prefix)
        assert context.safety_checks is SafetyChecks.warn

        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "-c", "conda-test", "spiffy-test-app=0.5"
        )
        assert message1 in stderr
        assert message2 in stderr
        assert package_is_installed(prefix, "spiffy-test-app=0.5")

    with make_temp_env() as prefix:
        with open(join(prefix, "condarc"), "a") as fh:
            fh.write("safety_checks: disabled\n")
        reload_config(prefix)
        assert context.safety_checks is SafetyChecks.disabled

        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "-c", "conda-test", "spiffy-test-app=0.5"
        )
        assert message1 not in stderr
        assert message2 not in stderr
        assert package_is_installed(prefix, "spiffy-test-app=0.5")


def test_json_create_install_update_remove():
    # regression test for #5384

    def assert_json_parsable(content):
        string = None
        try:
            for string in content and content.split("\0") or ():
                json.loads(string)
        except Exception as e:
            log.warn(
                "Problem parsing json output.\n"
                "  content: %s\n"
                "  string: %s\n"
                "  error: %r",
                content,
                string,
                e,
            )
            raise

    try:
        prefix = make_temp_prefix(str(uuid4())[:7])

        stdout, stderr, _ = run_command(
            Commands.CREATE,
            prefix,
            "python=3.8",
            "--json",
            "--dry-run",
            use_exception_handler=True,
        )
        assert_json_parsable(stdout)

        # regression test for #5825
        # contents of LINK and UNLINK is expected to have Dist format
        json_obj = json.loads(stdout)
        dist_dump = json_obj["actions"]["LINK"][0]
        assert "dist_name" in dist_dump

        stdout, stderr, _ = run_command(Commands.CREATE, prefix, "python=3.8", "--json")
        assert_json_parsable(stdout)
        assert not stderr
        json_obj = json.loads(stdout)
        dist_dump = json_obj["actions"]["LINK"][0]
        assert "dist_name" in dist_dump

        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "flask=2.0.1", "--json"
        )
        assert_json_parsable(stdout)
        assert not stderr
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "python=3")

        # Test force reinstall
        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "--force-reinstall", "flask=2.0.1", "--json"
        )
        assert_json_parsable(stdout)
        assert not stderr
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "python=3")

        stdout, stderr, _ = run_command(Commands.UPDATE, prefix, "flask", "--json")
        assert_json_parsable(stdout)
        assert not stderr
        assert not package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")

        stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "flask", "--json")
        assert_json_parsable(stdout)
        assert not stderr
        assert not package_is_installed(prefix, "flask=2.*")
        assert package_is_installed(prefix, "python=3")

        # regression test for #5825
        # contents of LINK and UNLINK is expected to have Dist format
        json_obj = json.loads(stdout)
        dist_dump = json_obj["actions"]["UNLINK"][0]
        assert "dist_name" in dist_dump

        stdout, stderr, _ = run_command(Commands.LIST, prefix, "--revisions", "--json")
        assert not stderr
        json_obj = json.loads(stdout)
        assert len(json_obj) == 5
        assert json_obj[4]["rev"] == 4

        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "--revision", "0", "--json"
        )
        assert_json_parsable(stdout)
        assert not stderr
        assert not package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")
    finally:
        rmtree(prefix, ignore_errors=True)


def test_not_writable_env_raises_EnvironmentNotWritableError():
    with make_temp_env() as prefix:
        make_read_only(join(prefix, PREFIX_MAGIC_FILE))
        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "openssl", use_exception_handler=True
        )
        assert "EnvironmentNotWritableError" in stderr
        assert prefix in stderr


def test_conda_update_package_not_installed():
    with make_temp_env() as prefix:
        with pytest.raises(PackageNotInstalledError):
            run_command(Commands.UPDATE, prefix, "sqlite", "openssl")

        with pytest.raises(CondaError) as conda_error:
            run_command(Commands.UPDATE, prefix, "conda-forge::*")
        assert conda_error.value.message.startswith("Invalid spec for 'conda update'")


def test_noarch_python_package_with_entry_points():
    # this channel has an ancient flask that is incompatible with jinja2>=3.1.0
    with make_temp_env("-c", "conda-test", "flask", "jinja2<3.1") as prefix:
        py_ver = get_python_version_for_prefix(prefix)
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/flask/__init__.py"
        pyc_file = pyc_path(py_file, py_ver).replace("/", os.sep)
        assert isfile(join(prefix, py_file))
        assert isfile(join(prefix, pyc_file))
        exe_path = join(prefix, get_bin_directory_short_path(), "flask")
        if on_win:
            exe_path += ".exe"
        assert isfile(exe_path)
        output = check_output([exe_path, "--help"], text=True)
        assert "Usage: flask" in output

        run_command(Commands.REMOVE, prefix, "flask")

        assert not isfile(join(prefix, py_file))
        assert not isfile(join(prefix, pyc_file))
        assert not isfile(exe_path)


def test_noarch_python_package_without_entry_points():
    # regression test for #4546
    with make_temp_env("-c", "conda-test", "itsdangerous") as prefix:
        py_ver = get_python_version_for_prefix(prefix)
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/itsdangerous.py"
        pyc_file = pyc_path(py_file, py_ver).replace("/", os.sep)
        assert isfile(join(prefix, py_file))
        assert isfile(join(prefix, pyc_file))

        run_command(Commands.REMOVE, prefix, "itsdangerous")

        assert not isfile(join(prefix, py_file))
        assert not isfile(join(prefix, pyc_file))


def test_noarch_python_package_reinstall_on_pyver_change():
    with make_temp_env(
        "-c",
        "conda-test",
        "itsdangerous=0.24",
        "python=3",
        use_restricted_unicode=on_win,
    ) as prefix:
        py_ver = get_python_version_for_prefix(prefix)
        assert py_ver.startswith("3")
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/itsdangerous.py"
        pyc_file_py3 = pyc_path(py_file, py_ver).replace("/", os.sep)
        assert isfile(join(prefix, py_file))
        assert isfile(join(prefix, pyc_file_py3))

        run_command(Commands.INSTALL, prefix, "python=2")
        assert not isfile(join(prefix, pyc_file_py3))  # python3 pyc file should be gone

        py_ver = get_python_version_for_prefix(prefix)
        assert py_ver.startswith("2")
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/itsdangerous.py"
        pyc_file_py2 = pyc_path(py_file, py_ver).replace("/", os.sep)

        assert isfile(join(prefix, py_file))
        assert isfile(join(prefix, pyc_file_py2))


def test_noarch_generic_package():
    with make_temp_env("-c", "conda-test", "font-ttf-inconsolata") as prefix:
        assert isfile(join(prefix, "fonts", "Inconsolata-Regular.ttf"))


def test_override_channels():
    with pytest.raises(OperationNotAllowed):
        with env_var(
            "CONDA_OVERRIDE_CHANNELS_ENABLED",
            "no",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            with make_temp_env("--override-channels", "python") as prefix:
                assert prefix

    with pytest.raises(ArgumentError):
        with make_temp_env("--override-channels", "python") as prefix:
            assert prefix

    stdout, stderr, _ = run_command(
        Commands.SEARCH,
        None,
        "--override-channels",
        "-c",
        "conda-test",
        "flask",
        "--json",
    )
    assert not stderr
    assert len(json.loads(stdout)["flask"]) < 3
    assert json.loads(stdout)["flask"][0]["noarch"] == "python"


def test_create_empty_env():
    with make_temp_env() as prefix:
        assert exists(join(prefix, "conda-meta/history"))

        list_output = run_command(Commands.LIST, prefix)
        stdout = list_output[0]
        stderr = list_output[1]
        assert stdout == dals(
            f"""
            # packages in environment at {prefix}:
            #
            # Name                    Version                   Build  Channel
            """
        )
        assert not stderr

        revision_output = run_command(Commands.LIST, prefix, "--revisions")
        stdout = revision_output[0]
        stderr = revision_output[1]
        assert not stderr
        assert isinstance(stdout, str)


@pytest.mark.skipif(reason="conda-forge doesn't have a full set of packages")
def test_strict_channel_priority():
    with make_temp_env() as prefix:
        stdout, stderr, rc = run_command(
            Commands.CREATE,
            prefix,
            "-c",
            "conda-forge",
            "-c",
            "defaults",
            "python=3.6",
            "quaternion",
            "--strict-channel-priority",
            "--dry-run",
            "--json",
            use_exception_handler=True,
        )
        assert not rc
        json_obj = json_loads(stdout)
        # We see:
        # libcxx             pkgs/main/osx-64::libcxx-4.0.1-h579ed51_0
        # Rather than spending more time looking for another package, just filter it out.
        # Same thing for Windows, this is because we use MKL always. Perhaps there's a
        # way to exclude it, I tried the "nomkl" package but that did not work.
        json_obj["actions"]["LINK"] = [
            link
            for link in json_obj["actions"]["LINK"]
            if link["name"] not in ("libcxx", "libcxxabi", "mkl", "intel-openmp")
        ]
        channel_groups = groupby(lambda x: x["channel"], json_obj["actions"]["LINK"])
        channel_groups = sorted(list(channel_groups))
        assert channel_groups == [
            "conda-forge",
        ]


def test_strict_resolve_get_reduced_index():
    channels = (Channel("defaults"),)
    specs = (MatchSpec("anaconda"),)
    index = get_reduced_index(None, channels, context.subdirs, specs, "repodata.json")
    r = Resolve(index, channels=channels)
    with env_var(
        "CONDA_CHANNEL_PRIORITY",
        "strict",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        reduced_index = r.get_reduced_index(specs)
        channel_name_groups = {
            name: {prec.channel.name for prec in group}
            for name, group in groupby(lambda x: x["name"], reduced_index).items()
        }
        channel_name_groups = {
            name: channel_names
            for name, channel_names in channel_name_groups.items()
            if len(channel_names) > 1
        }
        assert {} == channel_name_groups


def test_list_with_pip_no_binary(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    from conda.exports import rm_rf as _rm_rf

    # For this test to work on Windows, you can either pass use_restricted_unicode=on_win
    # to make_temp_env(), or you can set PYTHONUTF8 to 1 (and use Python 3.7 or above).
    # We elect to test the more complex of the two options.
    py_ver = "3.10"
    with tmp_env(f"python={py_ver}", "pip") as prefix:
        check_call(
            f"{PYTHON_BINARY} -m pip install --no-binary flask flask==1.0.2",
            cwd=prefix,
            shell=True,
        )

        PrefixData._cache_.clear()
        stdout, stderr, err = conda_cli("list", f"--prefix={prefix}")
        assert any(
            line.endswith("pypi")
            for line in stdout.split("\n")
            if line.lower().startswith("flask")
        )
        assert not stderr
        assert not err

        # regression test for #5847
        #   when using rm_rf on a directory
        assert prefix in PrefixData._cache_
        _rm_rf(prefix / get_python_site_packages_short_path(py_ver))
        assert prefix not in PrefixData._cache_


def test_list_with_pip_wheel(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python=3.10", "pip") as prefix:
        check_call(
            f"{PYTHON_BINARY} -m pip install flask==1.0.2",
            cwd=prefix,
            shell=True,
        )

        PrefixData._cache_.clear()
        stdout, stderr, err = conda_cli("list", f"--prefix={prefix}")
        assert any(
            line.endswith("pypi")
            for line in stdout.split("\n")
            if line.lower().startswith("flask")
        )
        assert not stderr
        assert not err

        # regression test for #3433
        conda_cli("install", f"--prefix={prefix}", "python=3.9", "--yes")
        assert package_is_installed(prefix, "python=3.9")


def test_rm_rf(clear_package_cache: None, tmp_env: TmpEnvFixture):
    # regression test for #5980, related to #5847
    from conda.exports import rm_rf as _rm_rf

    py_ver = "3.10"
    with tmp_env(f"python={py_ver}") as prefix:
        # regression test for #5847
        #   when using rm_rf on a file
        assert prefix in PrefixData._cache_
        _rm_rf(prefix / get_python_site_packages_short_path(py_ver), "os.py")
        assert prefix not in PrefixData._cache_

    with tmp_env() as prefix:
        assert isdir(prefix)
        assert prefix in PrefixData._cache_

        rmtree(prefix)
        assert not isdir(prefix)
        assert prefix in PrefixData._cache_

        _rm_rf(prefix)
        assert not isdir(prefix)
        assert prefix not in PrefixData._cache_


def test_compare_success():
    with make_temp_env("python=3.6", "flask=1.0.2", "bzip2=1.0.8") as prefix:
        env_file = join(prefix, "env.yml")
        touch(env_file)
        with open(env_file, "w") as f:
            f.write(
                dals(
                    """
                    name: dummy
                    channels:
                      - defaults
                    dependencies:
                      - bzip2=1.0.8
                      - flask>=1.0.1,<=1.0.4
                    """
                )
            )
        output, _, _ = run_command(Commands.COMPARE, prefix, env_file, "--json")
        assert "Success" in output
        rmtree(prefix, ignore_errors=True)


def test_compare_fail():
    with make_temp_env("python=3.6", "flask=1.0.2", "bzip2=1.0.8") as prefix:
        env_file = join(prefix, "env.yml")
        touch(env_file)
        with open(env_file, "w") as f:
            f.write(
                dals(
                    """
                    name: dummy
                    channels:
                      - defaults
                    dependencies:
                      - yaml
                      - flask=1.0.3
                    """
                )
            )
        output, _, _ = run_command(Commands.COMPARE, prefix, env_file, "--json")
        assert "yaml not found" in output
        assert (
            "flask found but mismatch. Specification pkg: flask=1.0.3, Running pkg: flask==1.0.2=py36_1"
            in output
        )
        rmtree(prefix, ignore_errors=True)


def test_install_tarball_from_local_channel(tmp_path: Path, monkeypatch: MonkeyPatch):
    # Regression test for #2812
    # install from local channel
    """
    path = u'/private/var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/pytest-of-rdonnelly/pytest-16/test_install_tarball_from_loca0/c352_çñßôêá'
    if on_win:
        path = u'C:\\çñ'
        percy = u'file:///C:/%C3%A7%C3%B1'
    else:
        path = u'/çñ'
        percy = 'file:///%C3%A7%C3%B1'

    url = path_to_url(path)
    assert url == percy
    path2 = url_to_path(url)
    assert path == path2
    assert type(path) == type(path2)
    # path_to_url("c:\\users\\est_install_tarball_from_loca0\a48a_6f154a82dbe3c7")
    """
    monkeypatch.setenv("CONDA_BLD_PATH", str(tmp_path))
    reset_context()
    assert context.bld_path == str(tmp_path)

    with make_temp_env() as prefix, make_temp_channel(["flask-2.1.3"]) as channel:
        run_command(Commands.INSTALL, prefix, "-c", channel, "flask=2.1.3", "--json")
        assert package_is_installed(prefix, channel + "::" + "flask")
        flask_fname = [
            p for p in PrefixData(prefix).iter_records() if p["name"] == "flask"
        ][0]["fn"]

        run_command(Commands.REMOVE, prefix, "flask")
        assert not package_is_installed(prefix, "flask=0")

        # Regression test for 2970
        # install from build channel as a tarball
        tar_path = Path(PackageCacheData.first_writable().pkgs_dir, flask_fname)
        if not tar_path.is_file():
            tar_path = tar_path.with_suffix(".tar.bz2")

        # create a temporary conda-bld
        conda_bld_sub = tmp_path / context.subdir
        conda_bld_sub.mkdir(exist_ok=True)
        tar_bld_path = str(conda_bld_sub / tar_path.name)
        copyfile(tar_path, tar_bld_path)

        run_command(Commands.INSTALL, prefix, tar_bld_path)
        assert package_is_installed(prefix, "flask")

        # Regression test for #462
        with make_temp_env(tar_bld_path) as prefix2:
            assert package_is_installed(prefix2, "flask")


def test_tarball_install():
    with make_temp_env("bzip2") as prefix:
        # We have a problem. If bzip2 is extracted already but the tarball is missing then this fails.
        bzip2_data = [
            p for p in PrefixData(prefix).iter_records() if p["name"] == "bzip2"
        ][0]
        bzip2_fname = bzip2_data["fn"]
        tar_old_path = join(PackageCacheData.first_writable().pkgs_dir, bzip2_fname)
        if not isfile(tar_old_path):
            log.warning(
                "Installing bzip2 failed to save the compressed package, downloading it 'manually' .."
            )
            # Downloading to the package cache causes some internal inconsistency here:
            #
            #   File "/Users/rdonnelly/conda/conda/conda/common/path.py", line 72, in url_to_path
            #     raise CondaError("You can only turn absolute file: urls into paths (not %s)" % url)
            # conda.CondaError: You can only turn absolute file: urls into paths (not https://repo.anaconda.com/pkgs/main/osx-64/bzip2-1.0.6-h1de35cc_5.tar.bz2)
            #
            # .. so download to the root of the prefix instead.
            tar_old_path = join(prefix, bzip2_fname)
            from conda.gateways.connection.download import download

            download(
                "https://repo.anaconda.com/pkgs/main/"
                + bzip2_data.subdir
                + "/"
                + bzip2_fname,
                tar_old_path,
                None,
            )
        assert isfile(tar_old_path), f"Failed to cache:\n{tar_old_path}"
        # It would be nice to be able to do this, but the cache folder name comes from
        # the file name and that is then all out of whack with the metadata.
        # tar_new_path = join(prefix, '家' + bzip2_fname)
        tar_new_path = join(prefix, bzip2_fname)

        run_command(Commands.RUN, prefix, cp_or_copy, tar_old_path, tar_new_path)
        assert isfile(
            tar_new_path
        ), f"Failed to copy:\n{tar_old_path}\nto:\n{tar_new_path}"
        run_command(Commands.INSTALL, prefix, tar_new_path)
        assert package_is_installed(prefix, "bzip2")


def test_tarball_install_and_bad_metadata():
    with make_temp_env("python=3.10.9", "flask=1.1.1", "--json") as prefix:
        assert package_is_installed(prefix, "flask==1.1.1")
        flask_data = [
            p for p in PrefixData(prefix).iter_records() if p["name"] == "flask"
        ][0]
        run_command(Commands.REMOVE, prefix, "flask")
        assert not package_is_installed(prefix, "flask==1.1.1")
        assert package_is_installed(prefix, "python")

        flask_fname = flask_data["fn"]
        tar_old_path = join(PackageCacheData.first_writable().pkgs_dir, flask_fname)

        # if a .tar.bz2 is already in the file cache, it's fine.  Accept it or the .conda file here.
        if not isfile(tar_old_path):
            tar_old_path = tar_old_path.replace(".conda", ".tar.bz2")
        assert isfile(tar_old_path)

        with pytest.raises(DryRunExit):
            run_command(Commands.INSTALL, prefix, tar_old_path, "--dry-run")
            assert not package_is_installed(prefix, "flask=1.*")

        # regression test for #2886 (part 1 of 2)
        # install tarball from package cache, default channel
        run_command(Commands.INSTALL, prefix, tar_old_path)
        assert package_is_installed(prefix, "flask=1.*")

        # regression test for #2626
        # install tarball with full path, outside channel
        tar_new_path = join(prefix, flask_fname)
        copyfile(tar_old_path, tar_new_path)
        run_command(Commands.INSTALL, prefix, tar_new_path)
        assert package_is_installed(prefix, "flask=1")

        # regression test for #2626
        # install tarball with relative path, outside channel
        run_command(Commands.REMOVE, prefix, "flask")
        assert not package_is_installed(prefix, "flask=1.1.1")
        tar_new_path = relpath(tar_new_path)
        run_command(Commands.INSTALL, prefix, tar_new_path)
        assert package_is_installed(prefix, "flask=1")

        # regression test for #2886 (part 2 of 2)
        # install tarball from package cache, local channel
        run_command(Commands.REMOVE, prefix, "flask", "--json")
        assert not package_is_installed(prefix, "flask=1")
        run_command(Commands.INSTALL, prefix, tar_old_path)
        # The last install was from the `local::` channel
        assert package_is_installed(prefix, "flask")

        # regression test for #2599
        # ignore json files in conda-meta that don't conform to name-version-build.json
        if not on_win:
            # xz is only a python dependency on unix
            xz_prec = next(PrefixData(prefix).query("xz"))
            dist_name = xz_prec.dist_str().split("::")[-1]
            xz_prefix_data_json_path = join(prefix, "conda-meta", dist_name + ".json")
            copyfile(xz_prefix_data_json_path, join(prefix, "conda-meta", "xz.json"))
            rm_rf(xz_prefix_data_json_path)
            assert not lexists(xz_prefix_data_json_path)
            PrefixData._cache_ = {}
            assert not package_is_installed(prefix, "xz")


@pytest.mark.skipif(on_win, reason="windows python doesn't depend on readline")
def test_update_with_pinned_packages():
    # regression test for #6914
    with make_temp_env(
        "-c", "https://repo.anaconda.com/pkgs/free", "python=2.7.12"
    ) as prefix:
        assert package_is_installed(prefix, "readline=6.2")
        # removing the history allows python to be updated too
        open(join(prefix, "conda-meta", "history"), "w").close()
        PrefixData._cache_.clear()
        run_command(Commands.UPDATE, prefix, "readline", no_capture=True)
        assert package_is_installed(prefix, "readline")
        assert not package_is_installed(prefix, "readline=6.2")
        assert package_is_installed(prefix, "python=2.7")
        assert not package_is_installed(prefix, "python=2.7.12")


def test_pinned_override_with_explicit_spec():
    with make_temp_env("python=3.9") as prefix:
        pyver = next(PrefixData(prefix).query("python")).version
        run_command(
            Commands.CONFIG, prefix, "--add", "pinned_packages", f"python={pyver}"
        )
        if context.solver == "libmamba":
            # LIBMAMBA ADJUSTMENT
            # Incompatible pin overrides forbidden in conda-libmamba-solver 23.9.0+
            # See https://github.com/conda/conda-libmamba-solver/pull/294
            with pytest.raises(SpecsConfigurationConflictError):
                run_command(Commands.INSTALL, prefix, "python=3.10", no_capture=True)
        else:
            run_command(Commands.INSTALL, prefix, "python=3.10", no_capture=True)
            assert package_is_installed(prefix, "python=3.10")


def test_remove_all():
    with make_temp_env("python") as prefix:
        assert exists(join(prefix, PYTHON_BINARY))
        assert package_is_installed(prefix, "python")

        # regression test for #2154
        with pytest.raises(PackagesNotFoundError) as exc:
            run_command(Commands.REMOVE, prefix, "python", "foo", "numpy")
        exception_string = repr(exc.value)
        assert "PackagesNotFoundError" in exception_string
        assert "- numpy" in exception_string
        assert "- foo" in exception_string

        run_command(Commands.REMOVE, prefix, "--all")
        assert path_is_clean(prefix)


@pytest.mark.skipif(
    on_win, reason="windows usually doesn't support symlinks out-of-the box"
)
@patch("conda.core.link.hardlink_supported", side_effect=lambda x, y: False)
def test_allow_softlinks(hardlink_supported_mock):
    hardlink_supported_mock._result_cache.clear()
    with env_var(
        "CONDA_ALLOW_SOFTLINKS",
        "true",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with make_temp_env("pip") as prefix:
            assert islink(
                join(
                    prefix,
                    get_python_site_packages_short_path(
                        get_python_version_for_prefix(prefix)
                    ),
                    "pip",
                    "__init__.py",
                )
            )
    hardlink_supported_mock._result_cache.clear()


@pytest.mark.skipif(on_win, reason="nomkl not present on windows")
def test_remove_features(clear_package_cache: None, request):
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="Features not supported in libmamba",
            strict=True,
        )
    )

    with make_temp_env("python=2", "numpy=1.13", "nomkl") as prefix:
        assert exists(join(prefix, PYTHON_BINARY))
        assert package_is_installed(prefix, "numpy")
        assert package_is_installed(prefix, "nomkl")
        assert not package_is_installed(prefix, "mkl")

        # A consequence of discontinuing use of the 'features' key and instead
        # using direct dependencies is that removing the feature means that
        # packages associated with the track_features base package are completely removed
        # and not replaced with equivalent non-variant packages as before.
        run_command(Commands.REMOVE, prefix, "--features", "nomkl")
        # assert package_is_installed(prefix, 'numpy')   # removed per above comment
        assert not package_is_installed(prefix, "nomkl")
        # assert package_is_installed(prefix, 'mkl')  # removed per above comment


@pytest.mark.skipif(
    on_win and context.bits == 32, reason="no 32-bit windows python on conda-forge"
)
@pytest.mark.flaky(reruns=2)
def test_dash_c_usage_replacing_python():
    # Regression test for #2606
    with make_temp_env("-c", "conda-forge", "python=3.10", no_capture=True) as prefix:
        assert exists(join(prefix, PYTHON_BINARY))
        assert package_is_installed(prefix, "conda-forge::python=3.10")
        run_command(Commands.INSTALL, prefix, "decorator")
        assert package_is_installed(prefix, "conda-forge::python=3.10")

        with make_temp_env("--clone", prefix) as clone_prefix:
            assert package_is_installed(clone_prefix, "conda-forge::python=3.10")
            assert package_is_installed(clone_prefix, "decorator")

        # Regression test for #2645
        fn = glob(join(prefix, "conda-meta", "python-3.10*.json"))[-1]
        with open(fn) as f:
            data = json.load(f)
        for field in ("url", "channel", "schannel"):
            if field in data:
                del data[field]
        with open(fn, "w") as f:
            json.dump(data, f)
        PrefixData._cache_ = {}

        with make_temp_env("-c", "conda-forge", "--clone", prefix) as clone_prefix:
            assert package_is_installed(clone_prefix, "python=3.10")
            assert package_is_installed(clone_prefix, "decorator")


def test_install_prune_flag():
    with make_temp_env("python=3", "flask") as prefix:
        assert package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")
        run_command(Commands.REMOVE, prefix, "flask")
        assert not package_is_installed(prefix, "flask")
        # this should get pruned when flask is removed
        assert not package_is_installed(prefix, "itsdangerous")
        assert package_is_installed(prefix, "python=3")


@pytest.mark.skipif(on_win, reason="readline is only a python dependency on unix")
def test_remove_force_remove_flag():
    with make_temp_env("python") as prefix:
        assert package_is_installed(prefix, "readline")
        assert package_is_installed(prefix, "python")

        run_command(Commands.REMOVE, prefix, "readline", "--force-remove")
        assert not package_is_installed(prefix, "readline")
        assert package_is_installed(prefix, "python")


def test_install_force_reinstall_flag():
    with make_temp_env("python") as prefix:
        stdout, stderr, _ = run_command(
            Commands.INSTALL,
            prefix,
            "--json",
            "--dry-run",
            "--force-reinstall",
            "python",
            use_exception_handler=True,
        )
        output_obj = json.loads(stdout.strip())
        unlink_actions = output_obj["actions"]["UNLINK"]
        link_actions = output_obj["actions"]["LINK"]
        assert len(unlink_actions) == len(link_actions) == 1
        assert unlink_actions[0] == link_actions[0]
        assert unlink_actions[0]["name"] == "python"


def test_create_no_deps_flag():
    with make_temp_env("python=2", "flask", "--no-deps") as prefix:
        assert package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=2")
        assert not package_is_installed(prefix, "openssl")
        assert not package_is_installed(prefix, "itsdangerous")


def test_create_only_deps_flag():
    with make_temp_env("python", "flask", "--only-deps", no_capture=True) as prefix:
        assert not package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python")
        if not on_win:
            # sqlite is a dependency of Python on all platforms
            assert package_is_installed(prefix, "sqlite")
        assert package_is_installed(prefix, "itsdangerous")

        # test that a later install keeps the --only-deps packages around
        run_command(Commands.INSTALL, prefix, "imagesize", no_capture=True)
        assert package_is_installed(prefix, "itsdangerous")
        assert not package_is_installed(prefix, "flask")

        # test that --only-deps installed stuff survives updates of unrelated packages
        run_command(Commands.UPDATE, prefix, "imagesize", no_capture=True)
        assert package_is_installed(prefix, "itsdangerous")
        assert not package_is_installed(prefix, "flask")

        # test that --only-deps installed stuff survives removal of unrelated packages
        run_command(Commands.REMOVE, prefix, "imagesize", no_capture=True)
        assert package_is_installed(prefix, "itsdangerous")
        assert not package_is_installed(prefix, "flask")


def test_install_update_deps_flag():
    with make_temp_env("flask=2.0.1", "jinja2=3.0.1") as prefix:
        python = join(prefix, PYTHON_BINARY)
        result_before = subprocess_call_with_clean_env([python, "--version"])
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "jinja2=3.0.1")
        run_command(Commands.INSTALL, prefix, "flask", "--update-deps")
        result_after = subprocess_call_with_clean_env([python, "--version"])
        assert result_before == result_after
        assert package_is_installed(prefix, "flask>2.0.1")
        assert package_is_installed(prefix, "jinja2>3.0.1")


def test_install_only_deps_flag():
    with make_temp_env("flask=2.0.2", "jinja2=3.0.2") as prefix:
        python = join(prefix, PYTHON_BINARY)
        result_before = subprocess_call_with_clean_env([python, "--version"])
        assert package_is_installed(prefix, "flask=2.0.2")
        assert package_is_installed(prefix, "jinja2=3.0.2")
        run_command(Commands.INSTALL, prefix, "flask", "--only-deps")
        result_after = subprocess_call_with_clean_env([python, "--version"])
        assert result_before == result_after
        assert package_is_installed(prefix, "flask=2.0.2")
        assert package_is_installed(prefix, "jinja2=3.0.2")

    with make_temp_env("flask==2.0.2", "--only-deps") as prefix:
        assert not package_is_installed(prefix, "flask")


def test_install_update_deps_only_deps_flags(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("flask=2.0.1", "jinja2=3.0.1", "python>=3.12") as prefix:
        python = str(prefix / PYTHON_BINARY)
        result_before = subprocess_call_with_clean_env([python, "--version"])
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "jinja2=3.0.1")
        conda_cli(
            "install",
            f"--prefix={prefix}",
            "flask",
            "python",
            "--update-deps",
            "--only-deps",
            "--yes",
        )
        result_after = subprocess_call_with_clean_env([python, "--version"])
        assert result_before == result_after
        assert package_is_installed(prefix, "flask=2.0.1")
        assert package_is_installed(prefix, "jinja2>3.0.1")


@pytest.mark.xfail(on_win, reason="nomkl not present on windows", strict=True)
def test_install_features(clear_package_cache: None, request):
    # https://github.com/conda/conda/pull/12984#issuecomment-1749634162
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="Features not supported in libmamba",
        )
    )

    with make_temp_env("python=2", "numpy=1.13", "nomkl", no_capture=True) as prefix:
        assert package_is_installed(prefix, "numpy")
        assert package_is_installed(prefix, "nomkl")
        assert not package_is_installed(prefix, "mkl")

    with make_temp_env("python=2", "numpy=1.13") as prefix:
        assert package_is_installed(prefix, "numpy")
        assert not package_is_installed(prefix, "nomkl")
        assert package_is_installed(prefix, "mkl")

        run_command(Commands.INSTALL, prefix, "nomkl", no_capture=True)
        assert package_is_installed(prefix, "numpy")
        assert package_is_installed(prefix, "nomkl")
        assert package_is_installed(prefix, "blas=1.0=openblas")
        assert not package_is_installed(prefix, "mkl_fft")
        assert not package_is_installed(prefix, "mkl_random")
        # assert not package_is_installed(prefix, "mkl")  # pruned as an indirect dep


def test_clone_offline_simple():
    with make_temp_env("bzip2") as prefix:
        assert package_is_installed(prefix, "bzip2")

        with make_temp_env("--clone", prefix, "--offline") as clone_prefix:
            assert context.offline
            assert package_is_installed(clone_prefix, "bzip2")


def test_conda_config_describe():
    with make_temp_env() as prefix:
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--describe")
        assert not stderr
        skip_categories = ("CLI-only", "Hidden and Undocumented")
        documented_parameter_names = chain.from_iterable(
            (
                parameter_names
                for category, parameter_names in context.category_map.items()
                if category not in skip_categories
            )
        )

        for param_name in documented_parameter_names:
            assert re.search(
                r"^# # %s \(" % param_name, stdout, re.MULTILINE
            ), param_name

        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--describe", "--json")
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert len(json_obj) >= 55
        assert "description" in json_obj[0]

        with env_var(
            "CONDA_QUIET", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol
        ):
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show-sources")
            assert not stderr
            assert "envvars" in stdout.strip()

            stdout, stderr, _ = run_command(
                Commands.CONFIG, prefix, "--show-sources", "--json"
            )
            assert not stderr
            json_obj = json.loads(stdout.strip())
            assert (
                "quiet" in json_obj["envvars"] and json_obj["envvars"]["quiet"] is True
            )
            assert json_obj["cmd_line"] == {"json": True}

        run_command(Commands.CONFIG, prefix, "--set", "changeps1", "false")
        with pytest.raises(CondaError):
            run_command(Commands.CONFIG, prefix, "--write-default")

        rm_rf(join(prefix, "condarc"))
        run_command(Commands.CONFIG, prefix, "--write-default")

        with open(join(prefix, "condarc")) as fh:
            data = fh.read()

        for param_name in documented_parameter_names:
            assert re.search(r"^# %s \(" % param_name, data, re.MULTILINE), param_name

        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--describe", "--json")
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert len(json_obj) >= 42
        assert "description" in json_obj[0]

        with env_var(
            "CONDA_QUIET", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol
        ):
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show-sources")
            assert not stderr
            assert "envvars" in stdout.strip()

            stdout, stderr, _ = run_command(
                Commands.CONFIG, prefix, "--show-sources", "--json"
            )
            assert not stderr
            json_obj = json.loads(stdout.strip())
            assert (
                "quiet" in json_obj["envvars"] and json_obj["envvars"]["quiet"] is True
            )
            assert json_obj["cmd_line"] == {"json": True}


def test_conda_config_validate():
    with make_temp_env() as prefix:
        run_command(Commands.CONFIG, prefix, "--set", "ssl_verify", "no")
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--validate")
        assert not stdout
        assert not stderr

        try:
            with open(join(prefix, "condarc"), "w") as fh:
                fh.write("default_python: anaconda\n")
                fh.write("ssl_verify: /path/doesnt/exist\n")
            reload_config(prefix)

            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.CONFIG, prefix, "--validate")

            assert len(exc.value.errors) == 2
            str_exc_value = str(exc.value)
            assert (
                "must be a boolean, a path to a certificate bundle file, a path to a directory containing certificates of trusted CAs, or 'truststore' to use the operating system certificate store."
                in str_exc_value
            )
            assert (
                "default_python value 'anaconda' not of the form '[23].[0-9][0-9]?'"
                in str_exc_value
            )
        finally:
            reset_context()


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="Skip truststore on earlier python versions",
)
def test_conda_config_validate_sslverify_truststore():
    with make_temp_env() as prefix:
        run_command(Commands.CONFIG, prefix, "--set", "ssl_verify", "truststore")
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--validate")
        assert not stdout
        assert not stderr


@pytest.mark.skipif(
    context.subdir not in ("linux-64", "osx-64", "win-32", "win-64", "linux-32"),
    reason="Skip unsupported platforms",
)
def test_rpy_search():
    with make_temp_env("python=3.5", "--override-channels", "-c", "defaults") as prefix:
        payload, _, _ = run_command(
            Commands.CONFIG, prefix, "--get", "channels", "--json"
        )
        default_channels = json_loads(payload)["get"].get("channels", ["defaults"])
        run_command(
            Commands.CONFIG,
            prefix,
            "--add",
            "channels",
            "https://repo.anaconda.com/pkgs/free",
        )
        # config --append on an empty key pre-populates it with the hardcoded default value!
        for channel in default_channels:
            run_command(Commands.CONFIG, prefix, "--remove", "channels", channel)
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show", "--json")
        json_obj = json_loads(stdout)
        assert "defaults" not in json_obj["channels"]

        assert package_is_installed(prefix, "python")
        assert "r" not in context.channels

        # assert conda search cannot find rpy2
        stdout, stderr, _ = run_command(
            Commands.SEARCH, prefix, "rpy2", "--json", use_exception_handler=True
        )
        json_obj = json_loads(
            stdout.replace("Fetching package metadata ...", "").strip()
        )
        assert json_obj["exception_name"] == "PackagesNotFoundError"

        # add r channel
        run_command(Commands.CONFIG, prefix, "--add", "channels", "r")
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show", "--json")
        json_obj = json_loads(stdout)
        assert "r" in json_obj["channels"]

        # assert conda search can now find rpy2
        stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "rpy2", "--json")
        json_obj = json_loads(
            stdout.replace("Fetching package metadata ...", "").strip()
        )


@pytest.mark.parametrize("use_sys_python", [True, False])
def test_compile_pyc(use_sys_python: bool):
    evs = {}
    with env_vars(evs, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        packages = []
        if use_sys_python:
            py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        else:
            # We force the use of 'the other' Python on Windows so that Windows
            # runtime / DLL incompatibilities will be readily apparent.
            py_ver = "3.10"
            packages.append(f"python={py_ver}")
        with make_temp_env(*packages, use_restricted_unicode=False) as prefix:
            if use_sys_python:
                python_binary = sys.executable
            else:
                python_binary = join(prefix, "python.exe" if on_win else "bin/python")
            assert os.path.isfile(python_binary), "Cannot even find Python"

            if on_win:
                site_packages = join("Lib", "site-packages")
            else:
                site_packages = join("lib", "python", py_ver)

            test_py_path = join(prefix, site_packages, "test_compile.py")
            test_pyc_path = pyc_path(test_py_path, py_ver).replace("/", os.sep)

            os.makedirs(dirname(test_py_path), exist_ok=True)
            os.makedirs(dirname(test_pyc_path), exist_ok=True)

            with open(test_py_path, "w") as test_py_file:
                test_py_file.write("__version__ = 1.0")

            compile_multiple_pyc(
                python_binary,
                (test_py_path,),
                (test_pyc_path,),
                prefix,
                py_ver,
            )
            assert isfile(
                test_pyc_path
            ), f"Failed to generate expected .pyc file {test_pyc_path}"


def test_conda_run_1():
    with make_temp_env(use_restricted_unicode=False, name=str(uuid4())[:7]) as prefix:
        output, error, rc = run_command(Commands.RUN, prefix, "echo", "hello")
        assert output == f"hello{os.linesep}\n"
        assert not error
        assert rc == 0
        output, error, rc = run_command(Commands.RUN, prefix, "exit", "5")
        assert not output
        assert not error
        assert rc == 5


def test_conda_run_nonexistant_prefix():
    with make_temp_env(use_restricted_unicode=False, name=str(uuid4())[:7]) as prefix:
        prefix = join(prefix, "clearly_a_prefix_that_does_not_exist")
        with pytest.raises(EnvironmentLocationNotFound):
            output, error, rc = run_command(Commands.RUN, prefix, "echo", "hello")


def test_conda_run_prefix_not_a_conda_env():
    with tempdir() as prefix:
        with pytest.raises(DirectoryNotACondaEnvironmentError):
            output, error, rc = run_command(Commands.RUN, prefix, "echo", "hello")


def test_clone_offline_multichannel_with_untracked():
    with env_vars(
        {
            "CONDA_DLL_SEARCH_MODIFICATION_ENABLE": "1",
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        # The flask install will use this version of Python. That is then used to compile flask's pycs.
        flask_python = "3.8"  # oldest available for osx-arm64
        with make_temp_env("python=3.9", use_restricted_unicode=True) as prefix:
            payload, _, _ = run_command(
                Commands.CONFIG, prefix, "--get", "channels", "--json"
            )
            default_channels = json_loads(payload)["get"].get("channels", ["defaults"])
            run_command(
                Commands.CONFIG,
                prefix,
                "--add",
                "channels",
                "https://repo.anaconda.com/pkgs/main",
            )
            # config --append on an empty key pre-populates it with the hardcoded default value!
            for channel in default_channels:
                run_command(Commands.CONFIG, prefix, "--remove", "channels", channel)

            run_command(
                Commands.INSTALL,
                prefix,
                "-c",
                "conda-test",
                "flask",
                "python=" + flask_python,
            )

            touch(join(prefix, "test.file"))  # untracked file
            with make_temp_env("--clone", prefix, "--offline") as clone_prefix:
                assert context.offline
                assert package_is_installed(clone_prefix, "python=" + flask_python)
                assert package_is_installed(clone_prefix, "flask=0.11.1=py_0")
                assert isfile(join(clone_prefix, "test.file"))  # untracked file


def test_package_pinning():
    with make_temp_env(
        "python=2.7", "itsdangerous=0.24", "pytz=2017.3", no_capture=True
    ) as prefix:
        assert package_is_installed(prefix, "itsdangerous=0.24")
        assert package_is_installed(prefix, "python=2.7")
        assert package_is_installed(prefix, "pytz=2017.3")

        with open(join(prefix, "conda-meta", "pinned"), "w") as fh:
            fh.write("itsdangerous 0.24\n")

        run_command(Commands.UPDATE, prefix, "--all", no_capture=True)
        assert package_is_installed(prefix, "itsdangerous=0.24")
        # assert not package_is_installed(prefix, "python=3.5")  # should be python-3.6, but it's not because of add_defaults_to_specs
        assert package_is_installed(prefix, "python=2.7")
        assert not package_is_installed(prefix, "pytz=2017.3")
        assert package_is_installed(prefix, "pytz")

        run_command(Commands.UPDATE, prefix, "--all", "--no-pin", no_capture=True)
        assert package_is_installed(prefix, "python=2.7")
        assert not package_is_installed(prefix, "itsdangerous=0.24")


def test_update_all_updates_pip_pkg():
    with make_temp_env("python=3.6", "pip", "pytz=2018", no_capture=True) as prefix:
        pip_ioo, pip_ioe, _ = run_command(
            Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true"
        )

        pip_o, pip_e, _ = run_command(
            Commands.RUN,
            prefix,
            "--dev",
            "python",
            "-m",
            "pip",
            "install",
            "itsdangerous==0.24",
        )
        PrefixData._cache_.clear()
        stdout, stderr, _ = run_command(Commands.LIST, prefix, "--json")
        assert not stderr
        json_obj = json.loads(stdout)
        six_info = next(info for info in json_obj if info["name"] == "itsdangerous")
        assert six_info == {
            "base_url": "https://conda.anaconda.org/pypi",
            "build_number": 0,
            "build_string": "pypi_0",
            "channel": "pypi",
            "dist_name": "itsdangerous-0.24-pypi_0",
            "name": "itsdangerous",
            "platform": "pypi",
            "version": "0.24",
        }
        assert package_is_installed(prefix, "itsdangerous=0.24")

        run_command(Commands.UPDATE, prefix, "--all")
        assert package_is_installed(prefix, "itsdangerous>0.24")
        assert package_is_installed(prefix, "pytz>2018")


def test_package_optional_pinning():
    with make_temp_env() as prefix:
        run_command(Commands.CONFIG, prefix, "--add", "pinned_packages", "python=3.10")
        run_command(Commands.INSTALL, prefix, "zlib")
        assert not package_is_installed(prefix, "python")
        run_command(Commands.INSTALL, prefix, "flask")
        assert package_is_installed(prefix, "python=3.10")


def test_update_deps_flag_absent():
    with make_temp_env("python=2", "itsdangerous=0.24") as prefix:
        assert package_is_installed(prefix, "python=2")
        assert package_is_installed(prefix, "itsdangerous=0.24")
        assert not package_is_installed(prefix, "flask")

        run_command(Commands.INSTALL, prefix, "flask")
        assert package_is_installed(prefix, "python=2")
        assert package_is_installed(prefix, "itsdangerous=0.24")
        assert package_is_installed(prefix, "flask")


def test_update_deps_flag_present():
    with make_temp_env("python=2", "itsdangerous=0.24") as prefix:
        assert package_is_installed(prefix, "python=2")
        assert package_is_installed(prefix, "itsdangerous=0.24")
        assert not package_is_installed(prefix, "flask")

        run_command(Commands.INSTALL, prefix, "--update-deps", "python=2", "flask")
        assert package_is_installed(prefix, "python=2")
        assert not package_is_installed(prefix, "itsdangerous=0.24")
        assert package_is_installed(prefix, "itsdangerous")
        assert package_is_installed(prefix, "flask")


@pytest.mark.skipif(True, reason="Add this test back someday.")
# @pytest.mark.skipif(not on_win, reason="menuinst-v1 shortcuts only relevant on Windows")
def test_shortcut_in_underscore_env_shows_message():
    prefix = make_temp_prefix("_" + str(uuid4())[:7])
    with make_temp_env(prefix=prefix):
        stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "console_shortcut")
        assert (
            "Environment name starts with underscore '_'.  "
            "Skipping menu installation." in stderr
        )


@pytest.mark.skipif(not on_win, reason="menuinst-v1 shortcuts only relevant on Windows")
def test_shortcut_not_attempted_with_no_shortcuts_arg():
    prefix = make_temp_prefix("_" + str(uuid4())[:7])
    shortcut_dir = get_shortcut_dir()
    shortcut_file = join(shortcut_dir, f"Anaconda Prompt ({basename(prefix)}).lnk")
    with make_temp_env(prefix=prefix):
        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "console_shortcut", "--no-shortcuts"
        )
        assert (
            "Environment name starts with underscore '_'.  Skipping menu installation."
            not in stderr
        )
        assert not isfile(shortcut_file)


@pytest.mark.skipif(not on_win, reason="menuinst-v1 shortcuts only relevant on Windows")
def test_shortcut_creation_installs_shortcut():
    shortcut_dir = get_shortcut_dir()
    shortcut_dir = join(
        shortcut_dir,
        "Anaconda{} ({}-bit)".format(sys.version_info.major, context.bits),
    )

    prefix = make_temp_prefix(str(uuid4())[:7])
    shortcut_file = join(shortcut_dir, f"Anaconda Prompt ({basename(prefix)}).lnk")
    try:
        with make_temp_env("console_shortcut", prefix=prefix):
            assert package_is_installed(prefix, "console_shortcut")
            assert isfile(
                shortcut_file
            ), "Shortcut not found in menu dir. Contents of dir:\n{}".format(
                os.listdir(shortcut_dir)
            )

            # make sure that cleanup without specifying --shortcuts still removes shortcuts
            run_command(Commands.REMOVE, prefix, "console_shortcut")
            assert not package_is_installed(prefix, "console_shortcut")
            assert not isfile(shortcut_file)
    finally:
        rmtree(prefix, ignore_errors=True)
        if isfile(shortcut_file):
            os.remove(shortcut_file)


@pytest.mark.skipif(not on_win, reason="menuinst-v1 shortcuts only relevant on Windows")
def test_shortcut_absent_does_not_barf_on_uninstall():
    shortcut_dir = get_shortcut_dir()
    shortcut_dir = join(
        shortcut_dir,
        "Anaconda{} ({}-bit)".format(sys.version_info.major, context.bits),
    )

    prefix = make_temp_prefix(str(uuid4())[:7])
    shortcut_file = join(shortcut_dir, f"Anaconda Prompt ({basename(prefix)}).lnk")
    assert not isfile(shortcut_file)

    try:
        # including --no-shortcuts should not get shortcuts installed
        with make_temp_env("console_shortcut", "--no-shortcuts", prefix=prefix):
            assert package_is_installed(prefix, "console_shortcut")
            assert not isfile(shortcut_file)

            # make sure that cleanup without specifying --shortcuts still removes shortcuts
            run_command(Commands.REMOVE, prefix, "console_shortcut")
            assert not package_is_installed(prefix, "console_shortcut")
            assert not isfile(shortcut_file)
    finally:
        rmtree(prefix, ignore_errors=True)
        if isfile(shortcut_file):
            os.remove(shortcut_file)


@pytest.mark.skipif(not on_win, reason="menuinst-v1 shortcuts only relevant on Windows")
def test_shortcut_absent_when_condarc_set():
    shortcut_dir = get_shortcut_dir()
    shortcut_dir = join(
        shortcut_dir,
        "Anaconda{} ({}-bit)".format(sys.version_info.major, context.bits),
    )

    prefix = make_temp_prefix(str(uuid4())[:7])
    shortcut_file = join(shortcut_dir, f"Anaconda Prompt ({basename(prefix)}).lnk")
    assert not isfile(shortcut_file)

    # set condarc shortcuts: False
    run_command(Commands.CONFIG, prefix, "--set", "shortcuts", "false")
    stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--get", "--json")
    json_obj = json_loads(stdout)
    assert json_obj["rc_path"] == join(prefix, "condarc")
    assert json_obj["get"]["shortcuts"] is False

    try:
        with make_temp_env("console_shortcut", prefix=prefix):
            # including shortcuts: False from condarc should not get shortcuts installed
            assert package_is_installed(prefix, "console_shortcut")
            assert not isfile(shortcut_file)

            # make sure that cleanup without specifying --shortcuts still removes shortcuts
            run_command(Commands.REMOVE, prefix, "console_shortcut")
            assert not package_is_installed(prefix, "console_shortcut")
            assert not isfile(shortcut_file)
    finally:
        rmtree(prefix, ignore_errors=True)
        if isfile(shortcut_file):
            os.remove(shortcut_file)
        # even if the $PREFIX/.condarc is gone,
        # the context object still has that config in memory
        reset_context()


def test_menuinst_v2(monkeypatch: MonkeyPatch):
    called = False
    from menuinst import install

    def mock_install(*args, **kwargs):
        nonlocal called, install
        called = True
        return install(*args, **kwargs)

    monkeypatch.setattr("menuinst.install", mock_install)
    prefix = make_temp_prefix(str(uuid4())[:7])

    Path(prefix).mkdir(parents=True, exist_ok=True)
    Path(prefix).touch(".nonadmin")
    out, err, _ = run_command(
        Commands.CREATE,
        prefix,
        "conda-test/label/menuinst-tests::package_1",
        "--no-deps",
    )
    assert package_is_installed(prefix, "package_1")
    assert Path(prefix, "Menu", "package_1.json").is_file()
    assert called
    assert "menuinst Exception" not in out + err
    base_dir = Path(get_shortcut_dir(prefix_for_unix=prefix))
    if sys.platform == "win32":
        assert (base_dir / "Package 1" / "A.lnk").is_file()
    elif sys.platform == "darwin":
        assert (base_dir / "A.app" / "Contents" / "MacOS" / "a").is_file()
    elif sys.platform == "linux":
        assert (base_dir / "package-1_a.desktop").is_file()
    else:
        raise NotImplementedError(sys.platform)


def test_create_default_packages():
    # Regression test for #3453
    try:
        prefix = make_temp_prefix(str(uuid4())[:7])

        # set packages
        run_command(Commands.CONFIG, prefix, "--add", "create_default_packages", "pip")
        run_command(
            Commands.CONFIG, prefix, "--add", "create_default_packages", "flask"
        )
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
        yml_obj = yaml_round_trip_load(stdout)
        assert yml_obj["create_default_packages"] == ["flask", "pip"]

        assert not package_is_installed(prefix, "python=2")
        assert not package_is_installed(prefix, "pytz")
        assert not package_is_installed(prefix, "flask")

        with make_temp_env("python=2", "pytz", prefix=prefix):
            assert package_is_installed(prefix, "python=2")
            assert package_is_installed(prefix, "pytz")
            assert package_is_installed(prefix, "flask")

    finally:
        rmtree(prefix, ignore_errors=True)


def test_create_default_packages_no_default_packages():
    try:
        prefix = make_temp_prefix(str(uuid4())[:7])

        # set packages
        run_command(Commands.CONFIG, prefix, "--add", "create_default_packages", "pip")
        run_command(
            Commands.CONFIG, prefix, "--add", "create_default_packages", "flask"
        )
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
        yml_obj = yaml_round_trip_load(stdout)
        assert yml_obj["create_default_packages"] == ["flask", "pip"]

        assert not package_is_installed(prefix, "python=2")
        assert not package_is_installed(prefix, "pytz")
        assert not package_is_installed(prefix, "flask")

        with make_temp_env("python=2", "pytz", "--no-default-packages", prefix=prefix):
            assert package_is_installed(prefix, "python=2")
            assert package_is_installed(prefix, "pytz")
            assert not package_is_installed(prefix, "flask")

    finally:
        rmtree(prefix, ignore_errors=True)


def test_create_dry_run(path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture):
    # regression test for #3453
    prefix = path_factory()

    stdout, stderr, code = conda_cli(
        "create",
        f"--prefix={prefix}",
        "--dry-run",
        catch=DryRunExit,
    )
    assert str(prefix) in stdout
    assert not stderr
    assert not code

    stdout, stderr, code = conda_cli(
        "create",
        f"--prefix={prefix}",
        "flask",
        "--dry-run",
        catch=DryRunExit,
    )
    assert ":flask" in stdout
    assert ":python" in stdout
    assert str(prefix) in stdout
    assert not stderr
    assert not code


def test_create_dry_run_json(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    prefix = path_factory()

    stdout, stderr, code = conda_cli(
        "create",
        f"--prefix={prefix}",
        "flask",
        "--dry-run",
        "--json",
        catch=DryRunExit,
    )
    names = {link["name"] for link in json.loads(stdout)["actions"]["LINK"]}
    assert "python" in names
    assert "flask" in names
    assert not stderr
    assert not code


def test_create_dry_run_yes_safety():
    with make_temp_env() as prefix:
        with pytest.raises(CondaValueError):
            run_command(Commands.CREATE, prefix, "--dry-run", "--yes")
        assert exists(prefix)


def test_packages_not_found():
    with make_temp_env() as prefix:
        with pytest.raises(PackagesNotFoundError) as exc:
            run_command(Commands.INSTALL, prefix, "not-a-real-package")
        assert "not-a-real-package" in str(exc.value)

        _, error, _ = run_command(
            Commands.INSTALL,
            prefix,
            "not-a-real-package",
            use_exception_handler=True,
        )
        assert "not-a-real-package" in error


def test_conda_pip_interop_dependency_satisfied_by_pip():
    with make_temp_env("python=3.10", "pip", use_restricted_unicode=False) as prefix:
        run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
        run_command(
            Commands.RUN,
            prefix,
            "--dev",
            "python",
            "-m",
            "pip",
            "install",
            "itsdangerous",
        )

        PrefixData._cache_.clear()
        output, error, _ = run_command(Commands.LIST, prefix)
        assert "itsdangerous" in output
        assert not error

        output, _, _ = run_command(
            Commands.INSTALL,
            prefix,
            "flask",
            "--dry-run",
            "--json",
            use_exception_handler=True,
        )
        json_obj = json.loads(output)
        print(json_obj)
        # itsdangerous shouldn't be in this list, because it's already present and satisfied
        #     by the pip package
        assert any(rec["name"] == "flask" for rec in json_obj["actions"]["LINK"])
        assert not any(
            rec["name"] == "itsdangerous" for rec in json_obj["actions"]["LINK"]
        )

        output, error, _ = run_command(
            Commands.SEARCH,
            prefix,
            "not-a-real-package",
            "--json",
            use_exception_handler=True,
        )
        assert not error
        json_obj = json_loads(output.strip())
        assert json_obj["exception_name"] == "PackagesNotFoundError"
        assert not len(json_obj.keys()) == 0


# XXX this test fails for osx-arm64 or other platforms absent from old 'free' channel
@pytest.mark.skipif(
    context.subdir == "win-32", reason="metadata is wrong; give python2.7"
)
def test_conda_pip_interop_pip_clobbers_conda():
    # 1. conda install old six
    # 2. pip install -U six
    # 3. conda list shows new six and deletes old conda record
    # 4. probably need to purge something with the history file too?
    # Python 3.5 and PIP are not unicode-happy on Windows:
    #   File "C:\Users\builder\AppData\Local\Temp\f903_固ō한ñђáγßê家ôç_35\lib\site-packages\pip\_vendor\urllib3\util\ssl_.py", line 313, in ssl_wrap_socket
    #     context.load_verify_locations(ca_certs, ca_cert_dir)
    #   TypeError: cafile should be a valid filesystem path
    with make_temp_env(
        "-c",
        "https://repo.anaconda.com/pkgs/free",
        "six=1.9",
        "pip=9.0.3",
        "python=3.5",
        use_restricted_unicode=on_win,
    ) as prefix:
        run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
        assert package_is_installed(prefix, "six=1.9.0")
        assert package_is_installed(prefix, "python=3.5")

        # On Windows, it's more than prefix.lower(), we get differently shortened paths too.
        # If only we could use pathlib.
        if not on_win:
            output, _, _ = run_command(Commands.RUN, prefix, which_or_where, "python")
            assert prefix.lower() in output.lower(), (
                "We should be running python in {}\n"
                "We are running {}\n"
                "Please check the CONDA_PREFIX PATH promotion in tests/__init__.py\n"
                "for a likely place to add more fixes".format(prefix, output)
            )
        output, _, _ = run_command(
            Commands.RUN, prefix, "python", "-m", "pip", "freeze"
        )
        pkgs = {ensure_text_type(v.strip()) for v in output.splitlines() if v.strip()}
        assert "six==1.9.0" in pkgs

        py_ver = get_python_version_for_prefix(prefix)
        sp_dir = get_python_site_packages_short_path(py_ver)

        output, _, _ = run_command(
            Commands.RUN,
            prefix,
            "python",
            "-m",
            "pip",
            "install",
            "-U",
            "six==1.10",
        )
        assert "Successfully installed six-1.10.0" in ensure_text_type(output)
        PrefixData._cache_.clear()
        stdout, stderr, _ = run_command(Commands.LIST, prefix, "--json")
        assert not stderr
        json_obj = json.loads(stdout)
        six_info = next(info for info in json_obj if info["name"] == "six")
        assert six_info == {
            "base_url": "https://conda.anaconda.org/pypi",
            "build_number": 0,
            "build_string": "pypi_0",
            "channel": "pypi",
            "dist_name": "six-1.10.0-pypi_0",
            "name": "six",
            "platform": "pypi",
            "version": "1.10.0",
        }
        assert package_is_installed(prefix, "six=1.10.0")
        output, err, _ = run_command(
            Commands.RUN, prefix, "python", "-m", "pip", "freeze"
        )
        pkgs = {ensure_text_type(v.strip()) for v in output.splitlines() if v.strip()}
        assert "six==1.10.0" in pkgs

        six_record = next(PrefixData(prefix).query("six"))
        print(json_dump(six_record))
        assert json_loads(json_dump(six_record)) == {
            "build": "pypi_0",
            "build_number": 0,
            "channel": "https://conda.anaconda.org/pypi",
            "constrains": [],
            "depends": ["python 3.5.*"],
            "files": [
                sp_dir + "/" + "__pycache__/six.cpython-35.pyc",
                sp_dir + "/" + "six-1.10.0.dist-info/DESCRIPTION.rst",
                sp_dir + "/" + "six-1.10.0.dist-info/INSTALLER",
                sp_dir + "/" + "six-1.10.0.dist-info/METADATA",
                sp_dir + "/" + "six-1.10.0.dist-info/RECORD",
                sp_dir + "/" + "six-1.10.0.dist-info/WHEEL",
                sp_dir + "/" + "six-1.10.0.dist-info/metadata.json",
                sp_dir + "/" + "six-1.10.0.dist-info/top_level.txt",
                sp_dir + "/" + "six.py",
            ],
            "fn": "six-1.10.0.dist-info",
            "name": "six",
            "package_type": "virtual_python_wheel",
            "paths_data": {
                "paths": [
                    {
                        "_path": sp_dir + "/" + "__pycache__/six.cpython-35.pyc",
                        "path_type": "hardlink",
                        "sha256": None,
                        "size_in_bytes": None,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/DESCRIPTION.rst",
                        "path_type": "hardlink",
                        "sha256": "QWBtSTT2zzabwJv1NQbTfClSX13m-Qc6tqU4TRL1RLs",
                        "size_in_bytes": 774,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/INSTALLER",
                        "path_type": "hardlink",
                        "sha256": "zuuue4knoyJ-UwPPXg8fezS7VCrXJQrAP7zeNuwvFQg",
                        "size_in_bytes": 4,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/METADATA",
                        "path_type": "hardlink",
                        "sha256": "5HceJsUnHof2IRamlCKO2MwNjve1eSP4rLzVQDfwpCQ",
                        "size_in_bytes": 1283,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/RECORD",
                        "path_type": "hardlink",
                        "sha256": None,
                        "size_in_bytes": None,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/WHEEL",
                        "path_type": "hardlink",
                        "sha256": "GrqQvamwgBV4nLoJe0vhYRSWzWsx7xjlt74FT0SWYfE",
                        "size_in_bytes": 110,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/metadata.json",
                        "path_type": "hardlink",
                        "sha256": "jtOeeTBubYDChl_5Ql5ZPlKoHgg6rdqRIjOz1e5Ek2U",
                        "size_in_bytes": 658,
                    },
                    {
                        "_path": sp_dir + "/" + "six-1.10.0.dist-info/top_level.txt",
                        "path_type": "hardlink",
                        "sha256": "_iVH_iYEtEXnD8nYGQYpYFUvkUW9sEO1GYbkeKSAais",
                        "size_in_bytes": 4,
                    },
                    {
                        "_path": sp_dir + "/" + "six.py",
                        "path_type": "hardlink",
                        "sha256": "A6hdJZVjI3t_geebZ9BzUvwRrIXo0lfwzQlM2LcKyas",
                        "size_in_bytes": 30098,
                    },
                ],
                "paths_version": 1,
            },
            "subdir": "pypi",
            "version": "1.10.0",
        }

        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "six", "--satisfied-skip-solve"
        )
        assert not stderr
        assert "All requested packages already installed." in stdout

        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "six", "--repodata-fn", "repodata.json"
        )
        assert not stderr
        assert package_is_installed(prefix, "six>=1.11")
        output, err, _ = run_command(
            Commands.RUN, prefix, "python", "-m", "pip", "freeze"
        )
        pkgs = {ensure_text_type(v.strip()) for v in output.splitlines() if v.strip()}
        six_record = next(PrefixData(prefix).query("six"))
        assert "six==%s" % six_record.version in pkgs

        assert len(glob(join(prefix, "conda-meta", "six-*.json"))) == 1

        output, err, _ = run_command(
            Commands.RUN,
            prefix,
            "python",
            "-m",
            "pip",
            "install",
            "-U",
            "six==1.10",
        )
        print(output)
        assert "Successfully installed six-1.10.0" in ensure_text_type(output)
        PrefixData._cache_.clear()
        assert package_is_installed(prefix, "six=1.10.0")

        stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "six")
        assert not stderr
        assert "six-1.10.0-pypi_0" in stdout
        assert not package_is_installed(prefix, "six")

        assert not glob(join(prefix, sp_dir, "six*"))


@pytest.mark.skipif(
    context.subdir not in ("linux-64", "osx-64", "win-32", "win-64", "linux-32"),
    reason="Skip unsupported platforms",
)
def test_conda_pip_interop_conda_editable_package(clear_package_cache: None, request):
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="conda-libmamba-solver does not implement pip interoperability",
        )
    )

    with env_vars(
        {
            "CONDA_REPORT_ERRORS": "false",
            "CONDA_RESTORE_FREE_CHANNEL": True,
            "CONDA_CHANNELS": "defaults",
            "CONDA_PIP_INTEROP_ENABLED": "true",
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with make_temp_env(
            "python=2.7", "pip=10", "git", use_restricted_unicode=on_win
        ) as prefix:
            workdir = prefix

            assert package_is_installed(prefix, "python")

            # install an "editable" urllib3 that cannot be managed
            output, err, _ = run_command(
                Commands.RUN,
                prefix,
                "--cwd",
                workdir,
                "python",
                "-m",
                "pip",
                "install",
                "-e",
                "git+https://github.com/urllib3/urllib3.git@1.19.1#egg=urllib3",
            )
            assert isfile(join(workdir, "src", "urllib3", "urllib3", "__init__.py"))
            assert not isfile(join("src", "urllib3", "urllib3", "__init__.py"))
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "urllib3")
            urllib3_record = next(PrefixData(prefix).query("urllib3"))
            urllib3_record_dump = urllib3_record.dump()
            urllib3_record_dump.pop("files")
            urllib3_record_dump.pop("paths_data")
            print(json_dump(urllib3_record_dump))

            assert json_loads(json_dump(urllib3_record_dump)) == {
                "build": "dev_0",
                "build_number": 0,
                "channel": "https://conda.anaconda.org/<develop>",
                "constrains": [
                    "cryptography >=1.3.4",
                    "idna >=2.0.0",
                    "pyopenssl >=0.14",
                    "pysocks !=1.5.7,<2.0,>=1.5.6",
                ],
                "depends": ["python 2.7.*"],
                "fn": "urllib3-1.19.1-dev_0",
                "name": "urllib3",
                "package_type": "virtual_python_egg_link",
                "subdir": "pypi",
                "version": "1.19.1",
            }

            # the unmanageable urllib3 should prevent a new requests from being installed
            stdout, stderr, _ = run_command(
                Commands.INSTALL,
                prefix,
                "requests",
                "--dry-run",
                "--json",
                use_exception_handler=True,
            )
            assert not stderr
            json_obj = json_loads(stdout)
            assert "UNLINK" not in json_obj["actions"]
            link_dists = json_obj["actions"]["LINK"]
            assert len(link_dists) == 1
            assert link_dists[0]["name"] == "requests"
            assert VersionOrder(link_dists[0]["version"]) < VersionOrder("2.16")

            # should already be satisfied
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "urllib3", "-S")
            assert "All requested packages already installed." in stdout

            # should raise an error
            with pytest.raises(PackagesNotFoundError):
                # TODO: This raises PackagesNotFoundError, but the error should really explain
                #       that we can't install urllib3 because it's already installed and
                #       unmanageable. The error should suggest trying to use pip to uninstall it.
                stdout, stderr, _ = run_command(
                    Commands.INSTALL, prefix, "urllib3=1.20", "--dry-run"
                )

            # Now install a manageable urllib3.
            output = check_output(
                PYTHON_BINARY + " -m pip install -U urllib3==1.20",
                cwd=prefix,
                shell=True,
            )
            print(output)
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "urllib3")
            urllib3_record = next(PrefixData(prefix).query("urllib3"))
            urllib3_record_dump = urllib3_record.dump()
            urllib3_record_dump.pop("files")
            urllib3_record_dump.pop("paths_data")
            print(json_dump(urllib3_record_dump))

            assert json_loads(json_dump(urllib3_record_dump)) == {
                "build": "pypi_0",
                "build_number": 0,
                "channel": "https://conda.anaconda.org/pypi",
                "constrains": ["pysocks >=1.5.6,<2.0,!=1.5.7"],
                "depends": ["python 2.7.*"],
                "fn": "urllib3-1.20.dist-info",
                "name": "urllib3",
                "package_type": "virtual_python_wheel",
                "subdir": "pypi",
                "version": "1.20",
            }

            # we should be able to install an unbundled requests that upgrades urllib3 in the process
            stdout, stderr, _ = run_command(
                Commands.INSTALL, prefix, "requests=2.18", "--json"
            )
            assert package_is_installed(prefix, "requests")
            assert package_is_installed(prefix, "urllib3>=1.21")
            assert not stderr
            json_obj = json_loads(stdout)
            unlink_dists = [
                dist_obj
                for dist_obj in json_obj["actions"]["UNLINK"]
                if dist_obj.get("platform") == "pypi"
            ]  # filter out conda package upgrades like python and libffi
            assert len(unlink_dists) == 1
            assert unlink_dists[0]["name"] == "urllib3"
            assert unlink_dists[0]["channel"] == "pypi"


def test_conda_pip_interop_compatible_release_operator():
    # Regression test for #7776
    # important to start the env with six 1.9.  That version forces an upgrade later in the test
    with make_temp_env(
        "-c",
        "https://repo.anaconda.com/pkgs/free",
        "pip=10",
        "six=1.9",
        "appdirs",
        use_restricted_unicode=on_win,
    ) as prefix:
        run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
        assert package_is_installed(prefix, "python")
        assert package_is_installed(prefix, "six=1.9")
        assert package_is_installed(prefix, "appdirs>=1.4.3")

        python_binary = join(prefix, PYTHON_BINARY)
        p = Popen(
            [python_binary, "-m", "pip", "install", "fs==2.1.0"],
            stdout=PIPE,
            stderr=PIPE,
            cwd=prefix,
            shell=False,
        )
        stdout, stderr = p.communicate()
        rc = p.returncode
        assert int(rc) != 0
        stderr = (
            stderr.decode("utf-8", errors="replace")
            if hasattr(stderr, "decode")
            else str(stderr)
        )
        assert "Cannot uninstall" in stderr

        run_command(Commands.REMOVE, prefix, "six")
        assert not package_is_installed(prefix, "six")

        output = check_output(
            [python_binary, "-m", "pip", "install", "fs==2.1.0"],
            cwd=prefix,
            shell=False,
        )
        print(output)
        PrefixData._cache_.clear()
        assert package_is_installed(prefix, "fs==2.1.0")
        # six_record = next(PrefixData(prefix).query("six"))
        # print(json_dump(six_record.dump()))
        assert package_is_installed(prefix, "six~=1.10")

        stdout, stderr, _ = run_command(Commands.LIST, prefix)
        assert not stderr
        assert (
            "fs                        2.1.0                    pypi_0    pypi"
            in stdout
        )

        with pytest.raises(DryRunExit):
            run_command(
                Commands.INSTALL,
                prefix,
                "-c",
                "https://repo.anaconda.com/pkgs/free",
                "agate=1.6",
                "--dry-run",
            )


def test_install_freezes_env_by_default():
    """We pass --no-update-deps/--freeze-installed by default, effectively.  This helps speed things
    up by not considering changes to existing stuff unless the solve ends up unsatisfiable.
    """

    # create an initial env
    with make_temp_env(
        "python=2", use_restricted_unicode=on_win, no_capture=True
    ) as prefix:
        assert package_is_installed(prefix, "python=2.7.*")
        # Install a version older than the last one
        run_command(Commands.INSTALL, prefix, "setuptools=40.*")

        stdout, stderr, _ = run_command(Commands.LIST, prefix, "--json")

        pkgs = json.loads(stdout)

        run_command(Commands.INSTALL, prefix, "imagesize", "--freeze-installed")

        stdout, _, _ = run_command(Commands.LIST, prefix, "--json")
        pkgs_after_install = json.loads(stdout)

        # Compare before and after installing package
        for pkg in pkgs:
            for pkg_after in pkgs_after_install:
                if pkg["name"] == pkg_after["name"]:
                    assert pkg["version"] == pkg_after["version"]


@pytest.mark.skipif(on_win, reason="gawk is a windows only package")
def test_search_gawk_not_win_filter():
    with make_temp_env() as prefix:
        stdout, stderr, _ = run_command(
            Commands.SEARCH,
            prefix,
            "*gawk",
            "--platform",
            "win-64",
            "--json",
            "-c",
            "https://repo.anaconda.com/pkgs/msys2",
            "--json",
            use_exception_handler=True,
        )
        json_obj = json_loads(
            stdout.replace("Fetching package metadata ...", "").strip()
        )
        assert "m2-gawk" in json_obj.keys()
        assert len(json_obj.keys()) == 1


@pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
def test_search_gawk_on_win():
    with make_temp_env() as prefix:
        stdout, _, _ = run_command(
            Commands.SEARCH, prefix, "*gawk", "--json", use_exception_handler=True
        )
        json_obj = json_loads(
            stdout.replace("Fetching package metadata ...", "").strip()
        )
        assert "m2-gawk" in json_obj.keys()
        assert len(json_obj.keys()) == 1


@pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
def test_search_gawk_on_win_filter():
    with make_temp_env() as prefix:
        stdout, _, _ = run_command(
            Commands.SEARCH,
            prefix,
            "gawk",
            "--platform",
            "linux-64",
            "--json",
            use_exception_handler=True,
        )
        json_obj = json_loads(
            stdout.replace("Fetching package metadata ...", "").strip()
        )
        assert not len(json_obj.keys()) == 0


def test_bad_anaconda_token_infinite_loop():
    # This test is being changed around 2017-10-17, when the behavior of anaconda.org
    # was changed.  Previously, an expired token would return with a 401 response.
    # Now, a 200 response is always given, with any public packages available on the channel.
    response = requests.get(
        "https://conda.anaconda.org/t/cqgccfm1mfma/data-portal/"
        "%s/repodata.json" % context.subdir
    )
    assert response.status_code == 200

    try:
        prefix = make_temp_prefix(str(uuid4())[:7])
        channel_url = "https://conda.anaconda.org/t/cqgccfm1mfma/data-portal"
        run_command(Commands.CONFIG, prefix, "--add", "channels", channel_url)
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
        yml_obj = yaml_round_trip_load(stdout)
        assert channel_url.replace("cqgccfm1mfma", "<TOKEN>") in yml_obj["channels"]

        with pytest.raises(PackagesNotFoundError):
            # this was supposed to be a package available in private but not
            # public data-portal; boltons was added to defaults in 2023 Jan.
            # --override-channels instead.
            run_command(
                Commands.SEARCH,
                prefix,
                "boltons",
                "-c",
                channel_url,
                "--override-channels",
                "--json",
            )

        stdout, stderr, _ = run_command(
            Commands.SEARCH, prefix, "anaconda-mosaic", "--json"
        )

        json_obj = json.loads(stdout)
        assert "anaconda-mosaic" in json_obj
        assert len(json_obj["anaconda-mosaic"]) > 0

    finally:
        rmtree(prefix, ignore_errors=True)
        reset_context()


@pytest.mark.skipif(
    read_binstar_tokens(),
    reason="binstar token found in global configuration",
)
def test_anaconda_token_with_private_package(
    conda_cli: CondaCLIFixture,
    capsys: CaptureFixture,
):
    # TODO: should also write a test to use binstar_client to set the token,
    # then let conda load the token
    package = "private-package"

    # Step 1. Make sure without the token we don't see the package
    channel_url = "https://conda-web.anaconda.org/conda-test"
    with pytest.raises(PackagesNotFoundError):
        conda_cli("search", "--channel", channel_url, package)
    # flush stdout/stderr
    capsys.readouterr()

    # Step 2. Now with the token make sure we can see the package
    channel_url = "https://conda-web.anaconda.org/t/co-91473e2c-56c1-4e16-b23e-26ab5fa4aed1/conda-test"
    stdout, _, _ = conda_cli(
        "search",
        *("--channel", channel_url),
        package,
        "--json",
    )
    assert package in json_loads(stdout)


def test_use_index_cache():
    from conda.core.subdir_data import SubdirData
    from conda.gateways.connection.session import CondaSession

    SubdirData.clear_cached_local_channel_data(exclude_file=False)

    prefix = make_temp_prefix("_" + str(uuid4())[:7])
    with make_temp_env(prefix=prefix, no_capture=True):
        # First, clear the index cache to make sure we start with an empty cache.
        index_cache_dir = create_cache_dir()
        run_command(Commands.CLEAN, "", "--index-cache", "--yes")
        assert not glob(join(index_cache_dir, "*.json"))

        # Then, populate the index cache.
        orig_get = CondaSession.get
        with patch.object(CondaSession, "get", autospec=True) as mock_method:

            def side_effect(self, url, **kwargs):
                # Make sure that we don't use the cache because of the
                # corresponding HTTP header. This test is supposed to test
                # whether the --use-index-cache causes the cache to be used.
                result = orig_get(self, url, **kwargs)
                for header in ("Etag", "Last-Modified", "Cache-Control"):
                    if header in result.headers:
                        del result.headers[header]
                return result

            SubdirData.clear_cached_local_channel_data(exclude_file=False)
            mock_method.side_effect = side_effect
            stdout, stderr, _ = run_command(
                Commands.SEARCH, prefix, "flask", "--info", "--json"
            )
            assert mock_method.called

        # Next run with --use-index-cache and make sure it actually hits the cache
        # and does not go out fetching index data remotely.
        with patch.object(CondaSession, "get", autospec=True) as mock_method:

            def side_effect(self, url, **kwargs):
                if url.endswith("/repodata.json") or url.endswith("/repodata.json.bz2"):
                    raise AssertionError("Index cache was not hit")
                else:
                    return orig_get(self, url, **kwargs)

            mock_method.side_effect = side_effect
            run_command(
                Commands.INSTALL, prefix, "flask", "--json", "--use-index-cache"
            )


def test_offline_with_empty_index_cache():
    from conda.core.subdir_data import SubdirData

    SubdirData.clear_cached_local_channel_data(exclude_file=False)

    try:
        with make_temp_env(use_restricted_unicode=on_win) as prefix:
            pkgs_dir = join(prefix, "pkgs")
            with env_var(
                "CONDA_PKGS_DIRS",
                pkgs_dir,
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                with make_temp_channel(["flask-2.1.3"]) as channel:
                    # Clear the index cache.
                    index_cache_dir = create_cache_dir()
                    run_command(Commands.CLEAN, "", "--index-cache", "--yes")
                    assert not exists(index_cache_dir)

                    # Then attempt to install a package with --offline. The package (flask) is
                    # available in a local channel, however its dependencies are not. Make sure
                    # that a) it fails because the dependencies are not available and b)
                    # we don't try to download the repodata from non-local channels but we do
                    # download repodata from local channels.
                    from conda.gateways.connection.session import CondaSession

                    orig_get = CondaSession.get

                    result_dict = {}

                    def side_effect(self, url, **kwargs):
                        if not url.startswith("file://"):
                            raise AssertionError(f"Attempt to fetch repodata: {url}")
                        if url.startswith(channel):
                            result_dict["local_channel_seen"] = True
                        return orig_get(self, url, **kwargs)

                    with patch.object(
                        CondaSession, "get", autospec=True
                    ) as mock_method:
                        mock_method.side_effect = side_effect

                        SubdirData.clear_cached_local_channel_data(exclude_file=False)

                        assert not package_is_installed(prefix, "flask")
                        command = (
                            Commands.INSTALL,
                            prefix,
                            "-c",
                            channel,
                            "flask",
                            "--offline",
                        )
                        if context.solver == "libmamba":
                            # libmamba solver expects repodata to be loaded into Repo objects
                            # It doesn't use the info from the tarball cache as conda does
                            with pytest.raises((RuntimeError, UnsatisfiableError)):
                                run_command(*command)
                        else:
                            # This first install passes because flask and its dependencies are in the
                            # package cache.
                            run_command(*command)
                            assert package_is_installed(prefix, "flask")

                            # The mock should have been called with our local channel URL though.
                            assert result_dict.get("local_channel_seen")

                        # Fails because pytz cannot be found in available channels.
                        # TODO: conda-libmamba-solver <=23.9.1 raises an ugly RuntimeError
                        # We can remove it when 23.9.2 is out with a fix
                        with pytest.raises((PackagesNotFoundError, RuntimeError)):
                            run_command(
                                Commands.INSTALL,
                                prefix,
                                "-c",
                                channel,
                                "pytz",
                                "--offline",
                            )
                        assert not package_is_installed(prefix, "pytz")
    finally:
        SubdirData.clear_cached_local_channel_data(exclude_file=False)


def test_create_from_extracted():
    with make_temp_package_cache() as pkgs_dir:
        assert context.pkgs_dirs == (pkgs_dir,)

        def pkgs_dir_has_tarball(tarball_prefix):
            return any(
                f.startswith(tarball_prefix)
                and any(f.endswith(ext) for ext in CONDA_PACKAGE_EXTENSIONS)
                for f in os.listdir(pkgs_dir)
            )

        with make_temp_env() as prefix:
            # First, make sure the openssl package is present in the cache,
            # downloading it if needed
            assert not pkgs_dir_has_tarball("openssl-")
            run_command(Commands.INSTALL, prefix, "openssl")
            assert pkgs_dir_has_tarball("openssl-")

            # Then, remove the tarball but keep the extracted directory around
            run_command(Commands.CLEAN, prefix, "--tarballs", "--yes")
            assert not pkgs_dir_has_tarball("openssl-")

        with make_temp_env() as prefix:
            # Finally, install openssl, enforcing the use of the extracted package.
            # We expect that the tarball does not appear again because we simply
            # linked the package from the extracted directory. If the tarball
            # appeared again, we decided to re-download the package for some reason.
            run_command(Commands.INSTALL, prefix, "openssl", "--offline")
            assert not pkgs_dir_has_tarball("openssl-")


def test_install_mkdir():
    try:
        prefix = make_temp_prefix()
        with open(os.path.join(prefix, "tempfile.txt"), "w") as f:
            f.write("test")
        assert isdir(prefix)
        assert isfile(os.path.join(prefix, "tempfile.txt"))
        with pytest.raises(DirectoryNotACondaEnvironmentError):
            run_command(Commands.INSTALL, prefix, "python", "--mkdir")

        run_command(Commands.CREATE, prefix)
        run_command(Commands.INSTALL, prefix, "python", "--mkdir")
        assert package_is_installed(prefix, "python")

        rm_rf(prefix, clean_empty_parents=True)
        assert path_is_clean(prefix)

        # this part also a regression test for #4849
        run_command(
            Commands.INSTALL,
            prefix,
            "python-dateutil",
            "python",
            "--mkdir",
            no_capture=True,
        )
        assert package_is_installed(prefix, "python")
        assert package_is_installed(prefix, "python-dateutil")

    finally:
        rm_rf(prefix, clean_empty_parents=True)


@pytest.mark.skipif(on_win, reason="python doesn't have dependencies on windows")
def test_disallowed_packages():
    with make_temp_env() as prefix:
        with env_var(
            "CONDA_DISALLOWED_PACKAGES",
            "sqlite&flask",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.INSTALL, prefix, "python")
        exc_val = exc.value.errors[0]
        assert isinstance(exc_val, DisallowedPackageError)
        assert exc_val.dump_map()["package_ref"]["name"] == "sqlite"


def test_dont_remove_conda_1():
    pkgs_dirs = context.pkgs_dirs
    prefix = make_temp_prefix()
    with env_vars(
        {"CONDA_ROOT_PREFIX": prefix, "CONDA_PKGS_DIRS": ",".join(pkgs_dirs)},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with make_temp_env(prefix=prefix):
            _, _, _ = run_command(Commands.INSTALL, prefix, "conda", "conda-build")
            assert package_is_installed(prefix, "conda")
            assert package_is_installed(prefix, "pycosat")
            assert package_is_installed(prefix, "conda-build")

            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.REMOVE, prefix, "conda")

            assert any(isinstance(e, RemoveError) for e in exc.value.errors)
            assert package_is_installed(prefix, "conda")
            assert package_is_installed(prefix, "pycosat")

            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.REMOVE, prefix, "pycosat")

            assert any(isinstance(e, RemoveError) for e in exc.value.errors)
            assert package_is_installed(prefix, "conda")
            assert package_is_installed(prefix, "pycosat")
            assert package_is_installed(prefix, "conda-build")


def test_dont_remove_conda_2():
    # regression test for #6904
    pkgs_dirs = context.pkgs_dirs
    prefix = make_temp_prefix()
    with make_temp_env(prefix=prefix):
        with env_vars(
            {"CONDA_ROOT_PREFIX": prefix, "CONDA_PKGS_DIRS": ",".join(pkgs_dirs)},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            _, _, _ = run_command(Commands.INSTALL, prefix, "conda")
            assert package_is_installed(prefix, "conda")
            assert package_is_installed(prefix, "pycosat")

            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.REMOVE, prefix, "pycosat")

            assert any(isinstance(e, RemoveError) for e in exc.value.errors)
            assert package_is_installed(prefix, "conda")
            assert package_is_installed(prefix, "pycosat")

            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.REMOVE, prefix, "conda")

            assert any(isinstance(e, RemoveError) for e in exc.value.errors)
            assert package_is_installed(prefix, "conda")
            assert package_is_installed(prefix, "pycosat")


def test_force_remove():
    with make_temp_env() as prefix:
        stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "libarchive")
        assert package_is_installed(prefix, "libarchive")
        assert package_is_installed(prefix, "xz")

        stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "xz", "--force")
        assert not package_is_installed(prefix, "xz")
        assert package_is_installed(prefix, "libarchive")

        stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "libarchive")
        assert not package_is_installed(prefix, "libarchive")

    # regression test for #3489
    # don't raise for remove --all if environment doesn't exist
    rm_rf(prefix, clean_empty_parents=True)
    run_command(Commands.REMOVE, prefix, "--all")


def test_download_only_flag():
    from conda.core.link import UnlinkLinkTransaction

    with patch.object(UnlinkLinkTransaction, "execute") as mock_method:
        with make_temp_env("openssl", "--download-only", use_exception_handler=True):
            assert mock_method.call_count == 0
        with make_temp_env("openssl", use_exception_handler=True):
            assert mock_method.call_count == 1


def test_transactional_rollback_simple():
    from conda.core.path_actions import CreatePrefixRecordAction

    with patch.object(CreatePrefixRecordAction, "execute") as mock_method:
        with make_temp_env() as prefix:
            mock_method.side_effect = KeyError("Bang bang!!")
            with pytest.raises(CondaMultiError):
                run_command(Commands.INSTALL, prefix, "openssl")
            assert not package_is_installed(prefix, "openssl")


def test_transactional_rollback_upgrade_downgrade():
    with make_temp_env("python=3.8", no_capture=True) as prefix:
        assert exists(join(prefix, PYTHON_BINARY))
        assert package_is_installed(prefix, "python=3")

        run_command(Commands.INSTALL, prefix, "flask=2.1.3")
        assert package_is_installed(prefix, "flask=2.1.3")

        from conda.core.path_actions import CreatePrefixRecordAction

        with patch.object(CreatePrefixRecordAction, "execute") as mock_method:
            mock_method.side_effect = KeyError("Bang bang!!")
            with pytest.raises(CondaMultiError):
                run_command(Commands.INSTALL, prefix, "flask=2.0.1")
            assert package_is_installed(prefix, "flask=2.1.3")


def test_directory_not_a_conda_environment():
    prefix = make_temp_prefix(str(uuid4())[:7])
    with open(join(prefix, "tempfile.txt"), "w") as f:
        f.write("weeee")
    try:
        with pytest.raises(DirectoryNotACondaEnvironmentError):
            run_command(Commands.INSTALL, prefix, "sqlite")
    finally:
        rm_rf(prefix)


def test_multiline_run_command():
    with make_temp_env() as prefix:
        env_which_etc, errs_etc, _ = run_command(
            Commands.RUN,
            prefix,
            "--cwd",
            prefix,
            dedent(
                f"""
                {env_or_set}
                {which_or_where} conda
                """
            ),
            dev=True,
        )
    assert env_which_etc
    assert not errs_etc


def _check_create_xz_env_different_platform(prefix, platform):
    assert exists(join(prefix, "bin", "xz"))
    # make sure we read the config from PREFIX/.condarc
    prefix_condarc = Path(prefix, ".condarc")
    reset_context([prefix_condarc])
    config_sources = context.collect_all()
    assert config_sources[prefix_condarc]["subdir"] == platform

    stdout, _, _ = run_command(
        Commands.INSTALL,
        prefix,
        "python",
        "--dry-run",
        "--json",
        use_exception_handler=True,
    )
    result = json.loads(stdout)
    assert result["success"]
    python = next(pkg for pkg in result["actions"]["LINK"] if pkg["name"] == "python")
    assert python["platform"] == platform


def test_create_env_different_platform_cli_flag():
    platform = "linux-64" if on_mac else "osx-64"
    with make_temp_env("xz", "--platform", platform) as prefix:
        _check_create_xz_env_different_platform(prefix, platform)


def test_create_env_different_platform_env_var():
    platform = "linux-64" if on_mac else "osx-64"
    with env_var("CONDA_SUBDIR", platform), make_temp_env("xz") as prefix:
        _check_create_xz_env_different_platform(prefix, platform)


@pytest.mark.skip("Test is flaky")
def test_conda_downgrade():
    # Create an environment with the current conda under test, but include an earlier
    # version of conda and other packages in that environment.
    # Make sure we can flip back and forth.
    with env_vars(
        {
            "CONDA_AUTO_UPDATE_CONDA": "false",
            "CONDA_ALLOW_CONDA_DOWNGRADES": "true",
            "CONDA_DLL_SEARCH_MODIFICATION_ENABLE": "1",
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        py_ver = "3"
        with make_temp_env(
            "conda=4.6.14",
            "python=" + py_ver,
            "conda-package-handling",
            use_restricted_unicode=True,
            name="_" + str(uuid4())[:8],
        ) as prefix:  # rev 0
            # See comment in test_init_dev_and_NoBaseEnvironmentError.
            python_exe = (
                join(prefix, "python.exe") if on_win else join(prefix, "bin", "python")
            )
            conda_exe = (
                join(prefix, "Scripts", "conda.exe")
                if on_win
                else join(prefix, "bin", "conda")
            )
            # this is used to run the python interpreter in the env and loads our dev
            #     version of conda
            py_co = [python_exe, "-m", "conda"]
            assert package_is_installed(prefix, "conda=4.6.14")

            # runs our current version of conda to install into the foreign env
            run_command(Commands.INSTALL, prefix, "lockfile")  # rev 1
            assert package_is_installed(prefix, "lockfile")

            # runs the conda in the env to install something new into the env
            subprocess_call_with_clean_env(
                [conda_exe, "install", "-yp", prefix, "itsdangerous"], path=prefix
            )  # rev 2
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "itsdangerous")

            # downgrade the version of conda in the env, using our dev version of conda
            subprocess_call(
                py_co + ["install", "-yp", prefix, "conda<4.6.14"], path=prefix
            )  # rev 3
            PrefixData._cache_.clear()
            assert not package_is_installed(prefix, "conda=4.6.14")

            # look at the revision history (for your reference, doesn't affect the test)
            stdout, stderr, _ = run_command(Commands.LIST, prefix, "--revisions")
            print(stdout)

            # undo the conda downgrade in the env (using our current outer conda version)
            PrefixData._cache_.clear()
            run_command(Commands.INSTALL, prefix, "--rev", "2")
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "conda=4.6.14")

            # use the conda in the env to revert to a previous state
            subprocess_call_with_clean_env(
                [conda_exe, "install", "-yp", prefix, "--rev", "1"], path=prefix
            )
            PrefixData._cache_.clear()
            assert not package_is_installed(prefix, "itsdangerous")
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "conda=4.6.14")
            assert package_is_installed(prefix, "python=" + py_ver)

            result = subprocess_call_with_clean_env(
                [conda_exe, "info", "--json"], path=prefix
            )
            conda_info = json.loads(result.stdout)
            assert conda_info["conda_version"] == "4.6.14"


@pytest.mark.skipif(on_win, reason="openssl only has a postlink script on unix")
def test_run_script_called():
    import conda.core.link

    with patch.object(conda.core.link, "subprocess_call") as rs:
        rs.return_value = Response(None, None, 0)
        with make_temp_env(
            "-c",
            "http://repo.anaconda.com/pkgs/free",
            "openssl=1.0.2j",
            "--no-deps",
        ) as prefix:
            assert package_is_installed(prefix, "openssl")
            assert rs.call_count == 1


@pytest.mark.xfail(on_mac, reason="known broken; see #11127")
def test_post_link_run_in_env():
    test_pkg = "_conda_test_env_activated_when_post_link_executed"
    # a non-unicode name must be provided here as activate.d scripts
    # are not executed on windows, see https://github.com/conda/conda/issues/8241
    with make_temp_env(test_pkg, "-c", "conda-test") as prefix:
        assert package_is_installed(prefix, test_pkg)


def test_conda_info_python():
    output, _, _ = run_command(Commands.INFO, None, "python=3.5")
    assert "python 3.5.4" in output


def test_toolz_cytoolz_package_cache_regression():
    with make_temp_env("python=3.5", use_restricted_unicode=on_win) as prefix:
        pkgs_dir = join(prefix, "pkgs")
        with env_var(
            "CONDA_PKGS_DIRS",
            pkgs_dir,
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            assert context.pkgs_dirs == (pkgs_dir,)
            run_command(
                Commands.INSTALL, prefix, "-c", "conda-forge", "toolz", "cytoolz"
            )
            assert package_is_installed(prefix, "toolz")


def test_remove_spellcheck():
    with make_temp_env("numpy=1.12") as prefix:
        assert exists(join(prefix, PYTHON_BINARY))
        assert package_is_installed(prefix, "numpy")

        with pytest.raises(PackagesNotFoundError) as exc:
            run_command(Commands.REMOVE, prefix, "numpi")

        exc_string = "%r" % exc.value
        assert (
            exc_string.strip()
            == dals(
                """
                PackagesNotFoundError: The following packages are missing from the target environment:
                  - numpi
                """
            ).strip()
        )
        assert package_is_installed(prefix, "numpy")


def test_conda_list_json():
    def pkg_info(s):
        # function from nb_conda/envmanager.py
        if isinstance(s, str):
            name, version, build = s.rsplit("-", 2)
            return {"name": name, "version": version, "build": build}
        else:
            return {
                "name": s["name"],
                "version": s["version"],
                "build": s.get("build_string") or s["build"],
            }

    with make_temp_env("python=3") as prefix:
        stdout, stderr, _ = run_command(Commands.LIST, prefix, "--json")
        stdout_json = json.loads(stdout)
        packages = [pkg_info(package) for package in stdout_json]
        python_package = next(p for p in packages if p["name"] == "python")
        assert python_package["version"].startswith("3")


@pytest.mark.skipif(
    context.subdir == "win-32", reason="dependencies not available for win-32"
)
def test_legacy_repodata():
    channel = join(dirname(abspath(__file__)), "data", "legacy_repodata")
    subdir = context.subdir
    if subdir not in ("win-64", "linux-64", "osx-64"):
        # run test even though default subdir doesn't have dependencies
        subdir = "linux-64"
    with env_var("CONDA_SUBDIR", subdir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with make_temp_env(
            "python", "moto=1.3.7", "-c", channel, "--no-deps"
        ) as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, "moto=1.3.7")


@pytest.mark.skipif(
    context.subdir == "win-32", reason="dependencies not available for win-32"
)
def test_cross_channel_incompatibility():
    # regression test for https://github.com/conda/conda/issues/8772
    # conda-forge puts a run_constrains on libboost, which they don't have on conda-forge.
    #   This is a way of forcing libboost to be removed.  It's a way that they achieve
    #   mutual exclusivity with the boost from defaults that works differently.

    # if this test passes, we'll hit the DryRunExit exception, instead of an UnsatisfiableError
    with pytest.raises(DryRunExit):
        stdout, stderr, _ = run_command(
            Commands.CREATE,
            "dummy_channel_incompat_test",
            "--dry-run",
            "-c",
            "conda-forge",
            "python",
            "boost==1.70.0",
            "boost-cpp==1.70.0",
            no_capture=True,
        )


# https://github.com/conda/conda/issues/9124
@pytest.mark.skipif(
    context.subdir != "linux-64",
    reason="lazy; package constraint here only valid on linux-64",
)
def test_neutering_of_historic_specs():
    with make_temp_env("psutil=5.6.3=py37h7b6447c_0") as prefix:
        stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "python=3.6")
        with open(os.path.join(prefix, "conda-meta", "history")) as f:
            d = f.read()
        assert re.search(r"neutered specs:.*'psutil==5.6.3'\]", d)
        # this would be unsatisfiable if the neutered specs were not being factored in correctly.
        #    If this command runs successfully (does not raise), then all is well.
        stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "imagesize")


# https://github.com/conda/conda/issues/10116
@pytest.mark.skipif(
    not context.subdir.startswith("linux"), reason="__glibc only available on linux"
)
def test_install_bound_virtual_package():
    with make_temp_env("__glibc>0"):
        pass


@pytest.mark.integration
def test_remove_empty_env():
    with make_temp_env() as prefix:
        run_command(Commands.CREATE, prefix)
        run_command(Commands.REMOVE, prefix, "--all")


def test_remove_ignore_nonenv():
    with tempdir() as test_root:
        prefix = join(test_root, "not-an-env")
        filename = join(prefix, "file.dat")

        os.mkdir(prefix)
        with open(filename, "wb"):
            pass

        with pytest.raises(DirectoryNotACondaEnvironmentError):
            run_command(Commands.REMOVE, prefix, "--all")

        assert exists(filename)
        assert exists(prefix)
