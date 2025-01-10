# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import platform
import re
import sys
from datetime import datetime
from importlib.metadata import version
from itertools import zip_longest
from json import loads as json_loads
from logging import getLogger
from os.path import basename, isdir
from pathlib import Path
from shutil import rmtree
from subprocess import check_call, check_output
from typing import TYPE_CHECKING
from unittest.mock import patch

import menuinst
import pytest

from conda import CondaError, CondaExitZero, CondaMultiError
from conda.auxlib.ish import dals
from conda.base.constants import (
    PREFIX_MAGIC_FILE,
    ChannelPriority,
    SafetyChecks,
)
from conda.base.context import context, reset_context
from conda.common.compat import on_linux, on_mac, on_win
from conda.common.io import stderr_log_level
from conda.common.iterators import groupby_to_dict as groupby
from conda.common.path import (
    BIN_DIRECTORY,
    get_python_site_packages_short_path,
    pyc_path,
)
from conda.common.serialize import json_dump, yaml_round_trip_load
from conda.core.index import get_reduced_index
from conda.core.package_cache_data import PackageCacheData
from conda.core.prefix_data import PrefixData, get_python_version_for_prefix
from conda.exceptions import (
    ArgumentError,
    CondaValueError,
    DirectoryNotACondaEnvironmentError,
    DisallowedPackageError,
    DryRunExit,
    EnvironmentLocationNotFound,
    EnvironmentNotWritableError,
    LinkError,
    OperationNotAllowed,
    PackageNotInstalledError,
    PackagesNotFoundError,
    RemoveError,
    SpecsConfigurationConflictError,
    UnsatisfiableError,
)
from conda.gateways.disk.create import compile_multiple_pyc
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.subprocess import (
    Response,
    subprocess_call,
    subprocess_call_with_clean_env,
)
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.models.version import VersionOrder
from conda.resolve import Resolve
from conda.testing.helpers import CHANNEL_DIR_V2
from conda.testing.integration import (
    PYTHON_BINARY,
    TEST_LOG_LEVEL,
    get_shortcut_dir,
    package_is_installed,
    which_or_where,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Callable, Literal

    from pytest import CaptureFixture, FixtureRequest, MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpChannelFixture,
        TmpEnvFixture,
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


def test_install_broken_post_install_keeps_existing_folders(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    # regression test for #8258
    with tmp_env("small-executable") as prefix:
        assert (prefix / BIN_DIRECTORY).exists()
        assert package_is_installed(prefix, "small-executable")

        _, _, exc = conda_cli(
            "install",
            f"--prefix={prefix}",
            "failing_post_link",
            "--yes",
            raises=CondaMultiError,
        )

        # CondaMultiError contains a non-Exception, why?
        # see, e.g., insertion of axngroup into CondaMultiError in
        # https://github.com/conda/conda/commit/c765d6a48151710040539bb82c51fce4c87ba81e
        # assert len(exc.value.errors) == 1
        assert isinstance(exc.value.errors[0], LinkError)
        assert exc.match("post-link script failed")

        assert (prefix / BIN_DIRECTORY).exists()
        assert package_is_installed(prefix, "small-executable")


def test_safety_checks_enabled(
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_SAFETY_CHECKS", "enabled")
        monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
        reset_context()
        assert context.safety_checks is SafetyChecks.enabled
        assert context.extra_safety_checks

        with pytest.raises(CondaMultiError) as exc:
            conda_cli(
                "install",
                f"--prefix={prefix}",
                "--channel=conda-test",
                "spiffy-test-app=0.5",
                "--yes",
            )

        # conda-test::spiffy-test-app=0.5 is a modified version of conda-test::spiffy-test-app=1.0
        assert dals(
            """
            The path 'site-packages/spiffy_test_app-1.0-py2.7.egg-info/top_level.txt'
            has an incorrect size.
              reported size: 32 bytes
              actual size: 16 bytes
            """
        ) in str(exc.value)
        assert "has a sha256 mismatch." in str(exc.value)
        assert not package_is_installed(prefix, "spiffy-test-app=0.5")


def test_safety_checks_warn(
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_SAFETY_CHECKS", "warn")
        monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
        reset_context()
        assert context.safety_checks is SafetyChecks.warn
        assert context.extra_safety_checks

        stdout, stderr, code = conda_cli(
            "install",
            f"--prefix={prefix}",
            "--channel=conda-test",
            "spiffy-test-app=0.5",
            "--yes",
        )
        assert stdout
        # conda-test::spiffy-test-app=0.5 is a modified version of conda-test::spiffy-test-app=1.0
        assert (
            dals(
                """
            The path 'site-packages/spiffy_test_app-1.0-py2.7.egg-info/top_level.txt'
            has an incorrect size.
              reported size: 32 bytes
              actual size: 16 bytes
            """
            )
            in stderr
        )
        assert "has a sha256 mismatch." in stderr
        assert not code
        assert package_is_installed(prefix, "spiffy-test-app=0.5")


def test_safety_checks_disabled(
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_SAFETY_CHECKS", "disabled")
        reset_context()
        assert context.safety_checks is SafetyChecks.disabled
        assert not context.extra_safety_checks

        stdout, stderr, code = conda_cli(
            "install",
            f"--prefix={prefix}",
            "--channel=conda-test",
            "spiffy-test-app=0.5",
            "--yes",
        )
        assert stdout
        # conda-test::spiffy-test-app=0.5 is a modified version of conda-test::spiffy-test-app=1.0
        assert (
            dals(
                """
            The path 'site-packages/spiffy_test_app-1.0-py2.7.egg-info/top_level.txt'
            has an incorrect size.
              reported size: 32 bytes
              actual size: 16 bytes
            """
            )
            not in stderr
        )
        assert "has a sha256 mismatch." not in stderr
        assert not code
        assert package_is_installed(prefix, "spiffy-test-app=0.5")


def test_json_create_install_update_remove(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
    capsys: CaptureFixture,
):
    # regression test for #5384

    def assert_json_parsable(content):
        string = None
        try:
            for string in content and content.split("\0") or ():
                json.loads(string)
        except Exception as e:
            log.warning(
                "Problem parsing json output.\n"
                "  content: %s\n"
                "  string: %s\n"
                "  error: %r",
                content,
                string,
                e,
            )
            raise

    prefix = path_factory()

    with pytest.raises(DryRunExit):
        conda_cli(
            "create",
            f"--prefix={prefix}",
            "zlib",
            "--json",
            "--dry-run",
        )
    stdout, stderr = capsys.readouterr()
    assert_json_parsable(stdout)

    # regression test for #5825
    # contents of LINK and UNLINK is expected to have dist format
    json_obj = json.loads(stdout)
    dist_dump = json_obj["actions"]["LINK"][0]
    assert "dist_name" in dist_dump

    stdout, stderr, _ = conda_cli(
        "create",
        f"--prefix={prefix}",
        "zlib",
        "--json",
        "--yes",
    )
    assert_json_parsable(stdout)
    assert not stderr

    json_obj = json.loads(stdout)
    dist_dump = json_obj["actions"]["LINK"][0]
    assert "dist_name" in dist_dump

    stdout, stderr, _ = conda_cli(
        "install",
        f"--prefix={prefix}",
        "ca-certificates<2023",
        "--json",
        "--yes",
    )
    assert_json_parsable(stdout)
    assert not stderr
    assert package_is_installed(prefix, "ca-certificates<2023")
    assert package_is_installed(prefix, "zlib")

    # Test force reinstall
    stdout, stderr, _ = conda_cli(
        "install",
        f"--prefix={prefix}",
        "--force-reinstall",
        "ca-certificates<2023",
        "--json",
        "--yes",
    )
    assert_json_parsable(stdout)
    assert not stderr
    assert package_is_installed(prefix, "ca-certificates<2023")
    assert package_is_installed(prefix, "zlib")

    stdout, stderr, _ = conda_cli(
        "update",
        f"--prefix={prefix}",
        "ca-certificates",
        "--json",
        "--yes",
    )
    assert_json_parsable(stdout)
    assert not stderr
    assert package_is_installed(prefix, "ca-certificates>=2023")
    assert package_is_installed(prefix, "zlib")

    stdout, stderr, _ = conda_cli(
        "remove",
        f"--prefix={prefix}",
        "ca-certificates",
        "--json",
        "--yes",
    )
    assert_json_parsable(stdout)
    assert not stderr
    assert not package_is_installed(prefix, "ca-certificates")
    assert package_is_installed(prefix, "zlib")

    # regression test for #5825
    # contents of LINK and UNLINK is expected to have Dist format
    json_obj = json.loads(stdout)
    dist_dump = json_obj["actions"]["UNLINK"][0]
    assert "dist_name" in dist_dump

    stdout, stderr, _ = conda_cli("list", f"--prefix={prefix}", "--revisions", "--json")
    assert not stderr
    json_obj = json.loads(stdout)
    assert len(json_obj) == 5
    assert json_obj[4]["rev"] == 4

    stdout, stderr, _ = conda_cli(
        "install",
        f"--prefix={prefix}",
        "--revision=0",
        "--json",
        "--yes",
    )
    assert_json_parsable(stdout)
    assert not stderr
    assert not package_is_installed(prefix, "ca-certificates")
    assert package_is_installed(prefix, "zlib")


def test_not_writable_env_raises_EnvironmentNotWritableError(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    """
    Make sure that an ``EnvironmentNotWritableError`` is raised when the ``PREFIX_MAGIC_FILE`` is
    not writable. This magic file is used to determined whether it's possible to write to an
    environment.
    """
    with tmp_env() as prefix:
        make_read_only(prefix / PREFIX_MAGIC_FILE)

        _, _, exc = conda_cli(
            "install",
            f"--prefix={prefix}",
            "ca-certificates",
            "--yes",
            raises=CondaMultiError,
        )

        assert len(exc.value.errors) == 1
        assert isinstance(exc.value.errors[0], EnvironmentNotWritableError)


def test_conda_update_package_not_installed(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    """
    Runs the update command twice with invalid input:

    1. Package is not currently installed (package should not exist)
    2. Invalid specification for a packaage
    """
    with tmp_env() as prefix:
        conda_cli(
            "update",
            f"--prefix={prefix}",
            "test-test-test",
            raises=PackageNotInstalledError,
        )

        with pytest.raises(CondaError, match="Invalid spec for 'conda update'"):
            conda_cli("update", f"--prefix={prefix}", "conda-forge::*")


def test_noarch_python_package_with_entry_points(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    """
    Makes sure that entry point file is installed.

    This test uses "pygments" as a Python package because it has no other dependencies and has an
    entry point script, "pygmentize".
    """
    with tmp_env("pygments") as prefix:
        py_ver = get_python_version_for_prefix(prefix)
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/pygments/__init__.py"
        pyc_file = pyc_path(py_file, py_ver)
        assert (prefix / py_file).is_file()
        assert (prefix / pyc_file).is_file()
        exe_path = (
            prefix / BIN_DIRECTORY / ("pygmentize.exe" if on_win else "pygmentize")
        )
        assert exe_path.is_file()
        output = check_output([exe_path, "--help"], text=True)
        assert "usage: pygmentize" in output

        conda_cli("remove", f"--prefix={prefix}", "pygments", "--yes")

        assert not (prefix / py_file).is_file()
        assert not (prefix / pyc_file).is_file()
        assert not exe_path.is_file()


def test_noarch_python_package_without_entry_points(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    """
    Regression test for issue:

    - https://github.com/conda/conda/issues/4546

    This test uses "itsdangerous" as a dependency because it is a relatively small package and
    has no entry point scripts.
    """
    with tmp_env("itsdangerous") as prefix:
        py_ver = get_python_version_for_prefix(prefix)
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/itsdangerous/__init__.py"
        pyc_file = pyc_path(py_file, py_ver)
        assert (prefix / py_file).is_file()
        assert (prefix / pyc_file).is_file()

        conda_cli("remove", f"--prefix={prefix}", "itsdangerous", "--yes")

        assert not (prefix / py_file).is_file()
        assert not (prefix / pyc_file).is_file()


def test_noarch_python_package_reinstall_on_pyver_change(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    """
    When Python changes versions (e.g. from 3.10 to 3.11) it is important to verify that all the previous
    dependencies were transferred over to the new version in ``lib/python3.x/site-packages/*``.
    """
    with tmp_env("itsdangerous", "python=3.10") as prefix:
        py_ver = get_python_version_for_prefix(prefix)
        assert py_ver.startswith("3.10")
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/itsdangerous/__init__.py"
        pyc_file_py310 = pyc_path(py_file, py_ver)
        assert (prefix / py_file).is_file()
        assert (prefix / pyc_file_py310).is_file()

        conda_cli("install", f"--prefix={prefix}", "python=3.11", "--yes")
        # python 3.10 pyc file should be gone
        assert not (prefix / pyc_file_py310).is_file()

        py_ver = get_python_version_for_prefix(prefix)
        assert py_ver.startswith("3.11")
        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = sp_dir + "/itsdangerous/__init__.py"
        pyc_file_py311 = pyc_path(py_file, py_ver)
        assert (prefix / py_file).is_file()
        assert (prefix / pyc_file_py311).is_file()


def test_noarch_generic_package(test_recipes_channel: Path, tmp_env: TmpEnvFixture):
    with tmp_env("font-ttf-inconsolata") as prefix:
        assert (prefix / "fonts" / "Inconsolata-Regular.ttf").is_file()


def test_override_channels_disabled(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
) -> None:
    monkeypatch.setenv("CONDA_OVERRIDE_CHANNELS_ENABLED", "no")
    reset_context()
    assert not context.override_channels_enabled

    conda_cli(
        "create",
        f"--prefix={path_factory()}",
        "--override-channels",
        "zlib",
        "--yes",
        raises=OperationNotAllowed,
    )

    conda_cli(
        "search",
        "--override-channels",
        "zlib",
        "--json",
        raises=OperationNotAllowed,
    )


def test_create_override_channels_enabled(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
) -> None:
    conda_cli(
        "create",
        f"--prefix={path_factory()}",
        "--override-channels",
        "zlib",
        "--yes",
        raises=ArgumentError,
    )

    stdout, stderr, code = conda_cli(
        "create",
        f"--prefix={path_factory()}",
        "--override-channels",
        "--channel=defaults",
        "zlib",
        "--yes",
    )
    assert stdout
    assert not stderr
    assert not code

    # should this case work?
    conda_cli(
        "create",
        f"--prefix={path_factory()}",
        "--override-channels",
        "defaults::zlib",
        "--yes",
        raises=ArgumentError,
    )


def test_search_override_channels_enabled(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
) -> None:
    conda_cli(
        "search",
        "--override-channels",
        "zlib",
        "--json",
        raises=ArgumentError,
    )

    stdout, stderr, code = conda_cli(
        "search",
        "--override-channels",
        "--channel=defaults",
        "zlib",
        "--json",
    )
    assert (parsed := json.loads(stdout))
    assert len(parsed) == 1
    assert len(parsed["zlib"]) > 0
    assert not stderr
    assert not code

    stdout, stderr, code = conda_cli(
        "search",
        "--override-channels",
        "defaults::zlib",
        "--json",
    )
    assert (parsed := json.loads(stdout))
    assert len(parsed) == 1
    assert len(parsed["zlib"]) > 0
    assert not stderr
    assert not code


def test_create_empty_env(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        assert (prefix / "conda-meta" / "history").exists()

        stdout, stderr, code = conda_cli("list", f"--prefix={prefix}")
        assert stdout == dals(
            f"""
            # packages in environment at {prefix}:
            #
            # Name                    Version                   Build  Channel
            """
        )
        assert not stderr
        assert not code

        stdout, stderr, code = conda_cli(
            "list",
            f"--prefix={prefix}",
            "--revisions",
            "--json",
        )
        revisions = json.loads(stdout)
        assert len(revisions) == 1
        assert datetime.fromisoformat(revisions[0]["date"])
        assert revisions[0]["downgrade"] == []
        assert revisions[0]["install"] == []
        assert revisions[0]["remove"] == []
        assert revisions[0]["rev"] == 0
        assert revisions[0]["upgrade"] == []
        assert not stderr
        assert not code


@pytest.mark.skipif(reason="conda-forge doesn't have a full set of packages")
def test_strict_channel_priority(
    conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    prefix = path_factory()
    stdout, stderr, code = conda_cli(
        "create",
        f"--prefix={prefix}",
        "--channel=conda-forge",
        "--channel=defaults",
        "python=3.6",
        "quaternion",
        "--strict-channel-priority",
        "--dry-run",
        "--json",
        "--yes",
    )
    assert not code
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
    channel_groups = set(groupby(lambda x: x["channel"], json_obj["actions"]["LINK"]))
    assert channel_groups == {"conda-forge"}


def test_strict_resolve_get_reduced_index(monkeypatch: MonkeyPatch):
    channels = (Channel("defaults"),)
    specs = (MatchSpec("anaconda"),)
    index = get_reduced_index(None, channels, context.subdirs, specs, "repodata.json")
    r = Resolve(index, channels=channels)

    monkeypatch.setenv("CONDA_CHANNEL_PRIORITY", "strict")
    reset_context()
    assert context.channel_priority == ChannelPriority.STRICT

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

    # cleanup
    monkeypatch.delenv("CONDA_CHANNEL_PRIORITY")
    reset_context()


def test_list_with_pip_no_binary(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    from conda.exports import rm_rf as _rm_rf

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


def test_install_tarball_from_file_based_channel(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    tmp_channel: TmpChannelFixture,
):
    with tmp_channel("ca-certificates") as (path, url):
        # regression test for #2812
        # handle file-based channels
        with tmp_env(
            "--override-channels",
            f"--channel={url}",
            "ca-certificates",
        ) as prefix:
            assert package_is_installed(prefix, f"{url}::ca-certificates")

        # regression test for #2970
        # install from build channel
        # mock CONDA_BLD_PATH by setting it to the temporary channel
        monkeypatch.setenv("CONDA_BLD_PATH", str(path))
        reset_context()
        assert context.bld_path == str(path)

        with tmp_env(
            "--override-channels",
            "--channel=local",
            "ca-certificates",
        ) as prefix:
            assert package_is_installed(prefix, "local::ca-certificates")

    # install from a local tarball
    # regression test for #462
    tar_path = next(
        PackageCacheData.query_all("ca-certificates")
    ).package_tarball_full_path
    with tmp_env(tar_path) as prefix2:
        assert package_is_installed(prefix2, "ca-certificates")


def test_tarball_install(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env(test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2") as prefix:
        assert package_is_installed(prefix, "dependent")
        assert not package_is_installed(prefix, "dependency")
        conda_cli("remove", f"--prefix={prefix}", "dependent", "--yes")
        assert not package_is_installed(prefix, "dependent")


def test_tarball_install_and_bad_metadata(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env("small-executable", "dependent", "another_dependent") as prefix:
        assert package_is_installed(prefix, "another_dependent")
        conda_cli("remove", f"--prefix={prefix}", "dependent", "--yes")
        assert package_is_installed(prefix, "small-executable")
        assert not package_is_installed(prefix, "dependent")
        # make sure all dependencies of "dependent" were removed
        assert not package_is_installed(prefix, "dependency")
        assert not package_is_installed(prefix, "another_dependent")

        tar_path = test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2"
        with pytest.raises(DryRunExit):
            conda_cli("install", f"--prefix={prefix}", tar_path, "--dry-run")

        conda_cli("install", f"--prefix={prefix}", tar_path, "--yes")
        assert package_is_installed(prefix, "dependent")

        bad_metadata = prefix / "bad_metadata.yml"
        bad_metadata.write_text(
            dals(
                """
                name: no-good-metadata
                dependencies:
                  - something-made-up
                """
            )
        )
        with pytest.raises(PackagesNotFoundError):
            conda_cli("install", f"--prefix={prefix}", bad_metadata, "--yes")
            assert not package_is_installed(prefix, "something-made-up")


def test_update_with_pinned_packages(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    """
    When a dependency is updated we update the dependent package too.

    Regression test for #6914
    """
    with tmp_env("dependent=1.0") as prefix:
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")

        # removing the history allows dependent to be updated too
        (prefix / "conda-meta" / "history").write_text("")

        conda_cli("update", f"--prefix={prefix}", "dependency", "--yes")

        PrefixData._cache_.clear()
        assert not package_is_installed(prefix, "dependent=1.0")
        assert not package_is_installed(prefix, "dependency=1.0")
        assert package_is_installed(prefix, "dependent=2.0")
        assert package_is_installed(prefix, "dependency=2.0")


def test_pinned_override_with_explicit_spec(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("dependent=1.0") as prefix:
        conda_cli(
            "config",
            f"--file={prefix / 'condarc'}",
            *("--add", "pinned_packages", "dependent=1.0"),
        )
        if context.solver == "libmamba":
            # LIBMAMBA ADJUSTMENT
            # Incompatible pin overrides forbidden in conda-libmamba-solver 23.9.0+
            # See https://github.com/conda/conda-libmamba-solver/pull/294
            with pytest.raises(SpecsConfigurationConflictError):
                conda_cli("install", f"--prefix={prefix}", "dependent=2.0", "--yes")
        else:
            conda_cli("install", f"--prefix={prefix}", "dependent=2.0", "--yes")
            assert package_is_installed(prefix, "dependent=2.0")


def test_allow_softlinks(
    test_recipes_channel: Path,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
):
    """
    When hardlinks are unsupported but softlinks are allowed we expect
    non-executables to always be symlinked.
    """
    mocker.patch("conda.core.link.hardlink_supported", return_value=False)

    monkeypatch.setenv("CONDA_ALLOW_SOFTLINKS", "true")
    reset_context()
    assert context.allow_softlinks

    with tmp_env("font-ttf-inconsolata") as prefix:
        assert (prefix / "fonts" / "Inconsolata-Bold.ttf").is_symlink()


def test_channel_usage_replacing_python(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    # Regression test for #2606
    with tmp_env("--channel=conda-forge", "python=3.10") as prefix:
        assert (prefix / PYTHON_BINARY).exists()
        assert package_is_installed(prefix, "conda-forge::python=3.10")

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "--channel=main",
            "decorator",
            "--yes",
        )
        PrefixData._cache_.clear()
        assert (prec := package_is_installed(prefix, "conda-forge::python=3.10"))
        assert package_is_installed(prefix, "main::decorator")

        with tmp_env(f"--clone={prefix}") as clone:
            assert package_is_installed(clone, "conda-forge::python=3.10")
            assert package_is_installed(clone, "main::decorator")

        # Regression test for #2645
        fn = prefix / "conda-meta" / f"{prec.name}-{prec.version}-{prec.build}.json"
        data = {
            field: value
            for field, value in json.loads(fn.read_text()).items()
            if field not in ("url", "channel", "schannel")
        }
        fn.write_text(json.dumps(data))
        PrefixData._cache_.clear()

        with tmp_env("--channel=conda-forge", f"--clone={prefix}") as clone:
            assert package_is_installed(clone, "conda-forge::python=3.10")
            assert package_is_installed(clone, "main::decorator")


def test_install_prune_flag(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python=3", "flask") as prefix:
        assert package_is_installed(prefix, "flask")
        assert package_is_installed(prefix, "python=3")
        conda_cli("remove", f"--prefix={prefix}", "flask", "--yes")
        assert not package_is_installed(prefix, "flask")
        # this should get pruned when flask is removed
        assert not package_is_installed(prefix, "itsdangerous")
        assert package_is_installed(prefix, "python=3")


@pytest.mark.skipif(on_win, reason="readline is only a python dependency on unix")
def test_remove_force_remove_flag(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python") as prefix:
        assert package_is_installed(prefix, "readline")
        assert package_is_installed(prefix, "python")

        conda_cli("remove", f"--prefix={prefix}", "readline", "--force-remove", "--yes")
        assert not package_is_installed(prefix, "readline")
        assert package_is_installed(prefix, "python")


def test_install_force_reinstall_flag(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("small-executable") as prefix:
        stdout, stderr, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "--json",
            "--dry-run",
            "--force-reinstall",
            "small-executable",
            raises=DryRunExit,
        )
        output_obj = json.loads(stdout.strip())
        unlink_actions = output_obj["actions"]["UNLINK"]
        link_actions = output_obj["actions"]["LINK"]
        assert len(unlink_actions) == len(link_actions) == 1
        assert unlink_actions[0] == link_actions[0]
        assert unlink_actions[0]["name"] == "small-executable"


def test_create_no_deps_flag(test_recipes_channel: Path, tmp_env: TmpEnvFixture):
    with tmp_env("dependent", "--no-deps") as prefix:
        assert package_is_installed(prefix, "dependent")
        assert not package_is_installed(prefix, "dependency")


def test_create_only_deps_flag(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    # ├─ dependent
    # │  └─ dependency
    # ├─ another_dependent
    # │  └─ dependent
    # │     └─ dependency
    # └─ other_dependent
    #    └─ dependent
    #       └─ dependency
    with tmp_env("dependent", "another_dependent", "--only-deps") as prefix:
        assert not package_is_installed(prefix, "another_dependent")
        assert package_is_installed(prefix, "dependent")
        assert package_is_installed(prefix, "dependency")
        assert not package_is_installed(prefix, "other_dependent")

        # test that a later install keeps the --only-deps packages around
        conda_cli("install", f"--prefix={prefix}", "other_dependent", "--yes")
        assert not package_is_installed(prefix, "another_dependent")
        assert package_is_installed(prefix, "dependent")
        assert package_is_installed(prefix, "dependency")
        assert package_is_installed(prefix, "other_dependent")

        # test that --only-deps installed stuff survives updates of unrelated packages
        conda_cli("update", f"--prefix={prefix}", "other_dependent", "--yes")
        assert not package_is_installed(prefix, "another_dependent")
        assert package_is_installed(prefix, "dependent")
        assert package_is_installed(prefix, "dependency")
        assert package_is_installed(prefix, "other_dependent")

        # test that --only-deps installed stuff survives removal of unrelated packages
        conda_cli("remove", f"--prefix={prefix}", "other_dependent", "--yes")
        assert not package_is_installed(prefix, "another_dependent")
        assert package_is_installed(prefix, "dependent")
        assert package_is_installed(prefix, "dependency")
        assert not package_is_installed(prefix, "other_dependent")


def test_install_update_deps_flag(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("dependent=1.0") as prefix:
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "dependent",
            "--update-deps",
            "--yes",
        )

        assert package_is_installed(prefix, "dependent=2.0")
        assert package_is_installed(prefix, "dependency=2.0")


def test_install_only_deps_flag(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        assert not package_is_installed(prefix, "dependent")
        assert not package_is_installed(prefix, "dependency")

        conda_cli("install", f"--prefix={prefix}", "dependent", "--only-deps", "--yes")

        assert not package_is_installed(prefix, "dependent")
        assert package_is_installed(prefix, "dependency")


def test_install_update_deps_only_deps_flags(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("another_dependent=1.0", "dependent=1.0") as prefix:
        assert package_is_installed(prefix, "another_dependent=1.0")
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "another_dependent",
            "--update-deps",
            "--only-deps",
            "--yes",
        )

        # another_dependnet isn't updated even though 2.0 is available
        assert package_is_installed(prefix, "another_dependent=1.0")
        assert package_is_installed(prefix, "dependent=2.0")
        assert package_is_installed(prefix, "dependency=2.0")


def test_clone_offline_simple(test_recipes_channel: Path, tmp_env: TmpEnvFixture):
    with tmp_env("small-executable") as prefix:
        assert package_is_installed(prefix, "small-executable")

        with tmp_env(f"--clone={prefix}", "--offline") as clone:
            assert package_is_installed(clone, "small-executable")


@pytest.mark.parametrize("use_sys_python", [True, False])
def test_compile_pyc(use_sys_python: bool, tmp_env: TmpEnvFixture):
    if use_sys_python:
        py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        packages = []
    else:
        # We force the use of 'the other' Python on Windows so that Windows
        # runtime / DLL incompatibilities will be readily apparent.
        py_ver = "3.10"
        packages = [f"python={py_ver}"]

    with tmp_env(*packages) as prefix:
        if use_sys_python:
            python_binary = Path(sys.executable)
        else:
            python_binary = prefix / PYTHON_BINARY
        assert python_binary.exists()

        sp_dir = get_python_site_packages_short_path(py_ver)
        py_file = prefix / sp_dir / "test_compile.py"
        pyc_file = prefix / pyc_path(str(py_file), py_ver)

        py_file.parent.mkdir(parents=True, exist_ok=True)
        py_file.write_text('__version__ = "1.0"')
        compile_multiple_pyc(
            str(python_binary),
            [str(py_file)],
            [str(pyc_file)],
            str(prefix),
            py_ver,
        )
        assert py_file.is_file()
        assert pyc_file.is_file()


def test_clone_offline_with_untracked(
    test_recipes_channel: Path,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
):
    with tmp_env("small-executable") as prefix:
        assert package_is_installed(prefix, "small-executable")
        (prefix / "magic").touch()  # untracked file

        with tmp_env(f"--clone={prefix}", "--offline") as clone:
            assert package_is_installed(clone, "small-executable")
            assert (clone / "magic").is_file()  # untracked file


def test_package_pinning(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("another_dependent=1.0", "dependent=1.0") as prefix:
        assert package_is_installed(prefix, "another_dependent=1.0")
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")

        (prefix / "conda-meta" / "pinned").write_text("dependent ==1.0")

        conda_cli("update", f"--prefix={prefix}", "--all", "--yes")
        assert package_is_installed(prefix, "another_dependent=2.0")
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")

        conda_cli("update", f"--prefix={prefix}", "--all", "--no-pin", "--yes")
        assert package_is_installed(prefix, "another_dependent=2.0")
        assert package_is_installed(prefix, "dependent=2.0")
        assert package_is_installed(prefix, "dependency=2.0")


def test_update_all_updates_pip_pkg(
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    monkeypatch.setenv("CONDA_PIP_INTEROP_ENABLED", "true")
    reset_context()
    assert context.pip_interop_enabled

    with tmp_env("python", "pip", "pytz<2023") as prefix:
        # install an old version of itsdangerous from pip
        stdout, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "install", "itsdangerous==1.*"),
        )

        # ensure installed version of itsdangerous is from PyPI
        PrefixData._cache_.clear()
        assert (prec := package_is_installed(prefix, "itsdangerous"))
        assert prec.dist_fields_dump() == {
            "base_url": "https://conda.anaconda.org/pypi",
            "build_number": 0,
            "build_string": "pypi_0",
            "channel": "pypi",
            "dist_name": f"itsdangerous-{prec.version}-pypi_0",
            "name": "itsdangerous",
            "platform": "pypi",
            "version": prec.version,
        }

        # updating all updates itsdangerous from a conda channel
        conda_cli("update", f"--prefix={prefix}", "--all", "--yes")
        assert (prec := package_is_installed(prefix, "itsdangerous>=2"))
        assert prec.subdir != "pypi"
        assert package_is_installed(prefix, "pytz>=2023")


def test_package_optional_pinning(
    test_recipes_channel: Path,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    monkeypatch.setenv("CONDA_PINNED_PACKAGES", "dependency=1.0")
    reset_context()
    assert context.pinned_packages == ("dependency=1.0",)

    with tmp_env() as prefix:
        conda_cli("install", f"--prefix={prefix}", "small-executable", "--yes")
        assert not package_is_installed(prefix, "python")

        conda_cli("install", f"--prefix={prefix}", "dependent", "--yes")
        assert package_is_installed(prefix, "dependency=1.0")


def test_update_deps_flag_absent(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("dependent=1.0") as prefix:
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")
        assert not package_is_installed(prefix, "another_dependent")

        conda_cli("install", f"--prefix={prefix}", "another_dependent", "--yes")
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")
        assert package_is_installed(prefix, "another_dependent")


def test_update_deps_flag_present(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("dependent=1.0") as prefix:
        assert package_is_installed(prefix, "dependent=1.0")
        assert package_is_installed(prefix, "dependency=1.0")
        assert not package_is_installed(prefix, "another_dependent")

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "another_dependent",
            "--update-deps",
            "--yes",
        )
        assert package_is_installed(prefix, "dependent=2.0")
        assert package_is_installed(prefix, "dependency=2.0")
        assert package_is_installed(prefix, "another_dependent")


@pytest.fixture
def shortcut_files(
    path_factory: PathFactoryFixture,
) -> Iterator[tuple[Path, Callable[[], tuple[Path, ...]]]]:
    prefix = path_factory()

    def get_shortcut() -> tuple[Path, ...]:
        shortcut_path = Path(get_shortcut_dir())
        return tuple(shortcut_path.glob(f"**/*Prompt ({basename(prefix)}).lnk"))

    assert not get_shortcut()

    yield (prefix, get_shortcut)

    for shortcut in get_shortcut():
        rmtree(shortcut.parent, ignore_errors=True)


@pytest.mark.xfail(not on_win, reason="console_shortcut is only on Windows")
def test_shortcut_creation_installs_shortcut(
    shortcut_files: tuple[Path, Callable[[], tuple[Path, ...]]],
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    prefix, get_shortcut = shortcut_files

    # depending on channel priorities match one of:
    #   - main::console_shortcut
    #   - conda-forge::miniforge_console_shortcut
    with tmp_env("*console_shortcut", prefix=prefix):
        assert (pkg := package_is_installed(prefix, "*console_shortcut"))

        assert get_shortcut()

        # make sure that cleanup without specifying --shortcuts still removes shortcuts
        if version("conda_libmamba_solver") <= "24.1.0":
            conda_cli("remove", f"--prefix={prefix}", pkg.name, "--yes")
        else:
            conda_cli("remove", f"--prefix={prefix}", "*console_shortcut", "--yes")
        assert not package_is_installed(prefix, "*console_shortcut")
        assert not get_shortcut()


@pytest.mark.xfail(not on_win, reason="console_shortcut is only on Windows")
def test_shortcut_absent_does_not_barf_on_uninstall(
    shortcut_files: tuple[Path, Callable[[], tuple[Path, ...]]],
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    prefix, get_shortcut = shortcut_files

    # depending on channel priorities match one of:
    #   - main::console_shortcut
    #   - conda-forge::miniforge_console_shortcut
    # including --no-shortcuts should not get shortcuts installed
    with tmp_env("*console_shortcut", "--no-shortcuts", prefix=prefix):
        assert (pkg := package_is_installed(prefix, "*console_shortcut"))
        assert not get_shortcut()

        # make sure that cleanup without specifying --shortcuts still removes shortcuts
        if version("conda_libmamba_solver") <= "24.1.0":
            conda_cli("remove", f"--prefix={prefix}", pkg.name, "--yes")
        else:
            conda_cli("remove", f"--prefix={prefix}", "*console_shortcut", "--yes")
        assert not package_is_installed(prefix, "*console_shortcut")
        assert not get_shortcut()


@pytest.mark.xfail(not on_win, reason="console_shortcut is only on Windows")
def test_shortcut_absent_when_condarc_set(
    shortcut_files: tuple[Path, Callable[[], tuple[Path, ...]]],
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    # mock condarc
    monkeypatch.setenv("CONDA_SHORTCUTS", "false")
    reset_context()
    assert not context.shortcuts

    prefix, get_shortcut = shortcut_files

    # depending on channel priorities match one of:
    #   - main::console_shortcut
    #   - conda-forge::miniforge_console_shortcut
    # shortcuts: False from condarc should not get shortcuts installed
    with tmp_env("*console_shortcut", prefix=prefix):
        assert (pkg := package_is_installed(prefix, "*console_shortcut"))
        assert not get_shortcut()

        # make sure that cleanup without specifying --shortcuts still removes shortcuts
        if version("conda_libmamba_solver") <= "24.1.0":
            conda_cli("remove", f"--prefix={prefix}", pkg.name, "--yes")
        else:
            conda_cli("remove", f"--prefix={prefix}", "*console_shortcut", "--yes")
        assert not package_is_installed(prefix, "*console_shortcut")
        assert not get_shortcut()


def test_menuinst_v2(
    mocker: MockerFixture,
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
    request: FixtureRequest,
):
    install = mocker.spy(menuinst, "install")

    (tmp_path / ".nonadmin").touch()
    shortcut_root = Path(get_shortcut_dir(prefix_for_unix=tmp_path))

    # shortcut_dirs are directories that need to be cleaned up
    # shortcut_files are files that need to be cleaned up
    if on_win:
        shortcut_dirs = [(shortcut_dir := shortcut_root / "Package 1")]
        shortcut_files = [shortcut_dir / "A.lnk", shortcut_dir / "B.lnk"]
    elif on_mac:
        shortcut_dirs = [
            (shortcut_dirA := shortcut_root / "A.app"),
            (shortcut_dirB := shortcut_root / "B.app"),
        ]
        shortcut_files = [
            shortcut_dirA / "Contents" / "MacOS" / "a",
            shortcut_dirB / "Contents" / "MacOS" / "b",
        ]
    elif on_linux:
        shortcut_dirs = []
        shortcut_files = [
            shortcut_root / "package-1_a.desktop",
            shortcut_root / "package-1_b.desktop",
        ]
    else:
        raise NotImplementedError(sys.platform)
    assert not any(path.exists() for path in shortcut_files)

    # register cleanup
    def finalizer():
        for path in shortcut_dirs:
            rmtree(path, ignore_errors=True)
        for path in shortcut_files:
            path.unlink(missing_ok=True)

    request.addfinalizer(finalizer)

    stdout, stderr, err = conda_cli(
        "create",
        f"--prefix={tmp_path}",
        "conda-test/label/menuinst-tests::package_1",
        "--no-deps",
        "--yes",
    )
    assert package_is_installed(tmp_path, "package_1")
    assert (tmp_path / "Menu" / "package_1.json").is_file()
    assert install.call_count == 1
    assert "menuinst Exception" not in stdout + stderr
    assert not err
    assert all(path.is_file() for path in shortcut_files)


def test_create_default_packages(
    test_recipes_channel: Path,
    monkeypatch: MonkeyPatch,
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
):
    # Regression test for #3453

    # mock condarc
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "small-executable,dependent")
    reset_context()
    assert context.create_default_packages == ("small-executable", "dependent")

    prefix = path_factory()
    assert not package_is_installed(prefix, "font-ttf-inconsolata")
    assert not package_is_installed(prefix, "small-executable")
    assert not package_is_installed(prefix, "dependent")

    with tmp_env("font-ttf-inconsolata", prefix=prefix):
        assert package_is_installed(prefix, "font-ttf-inconsolata")
        assert package_is_installed(prefix, "small-executable")
        assert package_is_installed(prefix, "dependent")


def test_create_default_packages_no_default_packages(
    test_recipes_channel: Path,
    monkeypatch: MonkeyPatch,
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
):
    # mock condarc
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "small-executable,dependent")
    reset_context()
    assert context.create_default_packages == ("small-executable", "dependent")

    prefix = path_factory()
    assert not package_is_installed(prefix, "font-ttf-inconsolata")
    assert not package_is_installed(prefix, "small-executable")
    assert not package_is_installed(prefix, "dependent")

    with tmp_env("font-ttf-inconsolata", "--no-default-packages", prefix=prefix):
        assert package_is_installed(prefix, "font-ttf-inconsolata")
        assert not package_is_installed(prefix, "small-executable")
        assert not package_is_installed(prefix, "dependent")


def test_create_dry_run(path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture):
    # regression test for #3453
    prefix = path_factory()

    stdout, stderr, _ = conda_cli(
        "create",
        f"--prefix={prefix}",
        "--dry-run",
        raises=DryRunExit,
    )
    assert str(prefix) in stdout
    assert not stderr

    stdout, stderr, _ = conda_cli(
        "create",
        f"--prefix={prefix}",
        "flask",
        "--dry-run",
        raises=DryRunExit,
    )
    assert ":flask" in stdout
    assert ":python" in stdout
    assert str(prefix) in stdout
    assert not stderr


def test_create_dry_run_json(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
):
    prefix = path_factory()

    stdout, stderr, _ = conda_cli(
        "create",
        f"--prefix={prefix}",
        "flask",
        "--dry-run",
        "--json",
        raises=DryRunExit,
    )
    names = {link["name"] for link in json.loads(stdout)["actions"]["LINK"]}
    assert "python" in names
    assert "flask" in names
    assert not stderr


def test_create_dry_run_yes_safety(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        with pytest.raises(CondaValueError):
            conda_cli("create", f"--prefix={prefix}", "--dry-run", "--yes")
        assert prefix.exists()


def test_packages_not_found(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        with pytest.raises(PackagesNotFoundError, match="not-a-real-package"):
            conda_cli("install", f"--prefix={prefix}", "not-a-real-package", "--yes")


# XXX this test fails for osx-arm64 or other platforms absent from old 'free' channel
@pytest.mark.skipif(
    context.subdir == "win-32" or platform.machine() == "arm64",
    reason="metadata is wrong; give python2.7 or no osx-arm64 package versions",
)
def test_conda_pip_interop_pip_clobbers_conda(
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    if "conda-forge" in context.channels:
        pytest.skip("This test is too slow with conda-forge as default channel.")
    # 1. conda install old six
    # 2. pip install -U six
    # 3. conda list shows new six and deletes old conda record
    # 4. probably need to purge something with the history file too?
    # Python 3.5 and PIP are not unicode-happy on Windows:
    #   File "C:\Users\builder\AppData\Local\Temp\f903_固ō한ñђáγßê家ôç_35\lib\site-packages\pip\_vendor\urllib3\util\ssl_.py", line 313, in ssl_wrap_socket
    #     context.load_verify_locations(ca_certs, ca_cert_dir)
    #   TypeError: cafile should be a valid filesystem path
    monkeypatch.setenv("CONDA_PIP_INTEROP_ENABLED", "true")
    reset_context()
    assert context.pip_interop_enabled

    with tmp_env(
        "--channel=https://repo.anaconda.com/pkgs/free",
        "six=1.9",
        "pip=9.0.3",
        "python=3.5",
    ) as prefix:
        assert package_is_installed(prefix, "six=1.9.0")
        assert package_is_installed(prefix, "pip=9.0.3")
        assert package_is_installed(prefix, "python=3.5")

        stdout, _, _ = conda_cli("run", f"--prefix={prefix}", which_or_where, "python")
        # on Windows `where` potentially returns multiple paths, filter for the first one
        py_path = next(filter(None, stdout.splitlines()), None)
        assert py_path and (prefix / PYTHON_BINARY).samefile(py_path)

        stdout, _, _ = conda_cli(
            "run",
            f"--prefix={prefix}",
            "python",
            "-m",
            "pip",
            "list",
            "--format=freeze",
        )
        assert any(pkg.strip() == "six==1.9.0" for pkg in stdout.splitlines())

        py_ver = get_python_version_for_prefix(prefix)
        sp_dir = get_python_site_packages_short_path(py_ver)

        PrefixData._cache_.clear()
        stdout, _, _ = conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "install", "--upgrade", "six==1.10"),
        )
        assert "Successfully installed six-1.10.0" in stdout

        stdout, _, _ = conda_cli("list", f"--prefix={prefix}", "--json")
        assert next(info for info in json.loads(stdout) if info["name"] == "six") == {
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
        stdout, _, _ = conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "list", "--format=freeze"),
        )
        assert any(pkg.strip() == "six==1.10.0" for pkg in stdout.splitlines())

        assert json.loads(json_dump(PrefixData(prefix).get("six"))) == {
            "build": "pypi_0",
            "build_number": 0,
            "channel": "https://conda.anaconda.org/pypi",
            "constrains": [],
            "depends": ["python 3.5.*"],
            "files": [
                sp_dir + "/__pycache__/six.cpython-35.pyc",
                sp_dir + "/six-1.10.0.dist-info/DESCRIPTION.rst",
                sp_dir + "/six-1.10.0.dist-info/INSTALLER",
                sp_dir + "/six-1.10.0.dist-info/METADATA",
                sp_dir + "/six-1.10.0.dist-info/RECORD",
                sp_dir + "/six-1.10.0.dist-info/WHEEL",
                sp_dir + "/six-1.10.0.dist-info/metadata.json",
                sp_dir + "/six-1.10.0.dist-info/top_level.txt",
                sp_dir + "/six.py",
            ],
            "fn": "six-1.10.0.dist-info",
            "name": "six",
            "package_type": "virtual_python_wheel",
            "paths_data": {
                "paths": [
                    {
                        "_path": sp_dir + "/__pycache__/six.cpython-35.pyc",
                        "path_type": "hardlink",
                        "sha256": None,
                        "size_in_bytes": None,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/DESCRIPTION.rst",
                        "path_type": "hardlink",
                        "sha256": "QWBtSTT2zzabwJv1NQbTfClSX13m-Qc6tqU4TRL1RLs",
                        "size_in_bytes": 774,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/INSTALLER",
                        "path_type": "hardlink",
                        "sha256": "zuuue4knoyJ-UwPPXg8fezS7VCrXJQrAP7zeNuwvFQg",
                        "size_in_bytes": 4,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/METADATA",
                        "path_type": "hardlink",
                        "sha256": "5HceJsUnHof2IRamlCKO2MwNjve1eSP4rLzVQDfwpCQ",
                        "size_in_bytes": 1283,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/RECORD",
                        "path_type": "hardlink",
                        "sha256": None,
                        "size_in_bytes": None,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/WHEEL",
                        "path_type": "hardlink",
                        "sha256": "GrqQvamwgBV4nLoJe0vhYRSWzWsx7xjlt74FT0SWYfE",
                        "size_in_bytes": 110,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/metadata.json",
                        "path_type": "hardlink",
                        "sha256": "jtOeeTBubYDChl_5Ql5ZPlKoHgg6rdqRIjOz1e5Ek2U",
                        "size_in_bytes": 658,
                    },
                    {
                        "_path": sp_dir + "/six-1.10.0.dist-info/top_level.txt",
                        "path_type": "hardlink",
                        "sha256": "_iVH_iYEtEXnD8nYGQYpYFUvkUW9sEO1GYbkeKSAais",
                        "size_in_bytes": 4,
                    },
                    {
                        "_path": sp_dir + "/six.py",
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

        stdout, _, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "six",
            "--satisfied-skip-solve",
            "--yes",
        )
        assert "All requested packages already installed." in stdout

        stdout, _, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "six",
            "--repodata-fn=repodata.json",
            "--yes",
        )
        assert package_is_installed(prefix, "six>=1.11")

        stdout, _, _ = conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "list", "--format=freeze"),
        )
        assert any(
            pkg.strip() == f"six=={PrefixData(prefix).get('six').version}"
            for pkg in stdout.splitlines()
        )
        assert len(list((prefix / "conda-meta").glob("six-*.json"))) == 1

        PrefixData._cache_.clear()
        stdout, _, _ = conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "install", "--upgrade", "six==1.10"),
        )
        assert "Successfully installed six-1.10.0" in stdout
        assert package_is_installed(prefix, "six=1.10.0")

        stdout, _, _ = conda_cli("remove", f"--prefix={prefix}", "six", "--yes")
        assert "six-1.10.0-pypi_0" in stdout
        assert not package_is_installed(prefix, "six")

        assert not list((prefix / sp_dir).glob("six*"))


def test_conda_pip_interop_conda_editable_package(
    clear_package_cache: None,
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "classic",
            reason="See https://github.com/conda/conda/issues/13529.",
        )
    )
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="conda-libmamba-solver does not implement pip interoperability",
        )
    )

    monkeypatch.setenv("CONDA_PIP_INTEROP_ENABLED", "true")
    reset_context()
    assert context.pip_interop_enabled

    with tmp_env("python=3.12", "pip", "git") as prefix:
        assert package_is_installed(prefix, "python")
        assert package_is_installed(prefix, "pip")
        assert package_is_installed(prefix, "git")

        # install an "editable" urllib3 that cannot be managed
        PrefixData._cache_.clear()
        conda_cli(
            "run",
            f"--prefix={prefix}",
            f"--cwd={prefix}",
            *(
                "python",
                "-m",
                "pip",
                "install",
                "--editable",
                "git+https://github.com/urllib3/urllib3.git@1.19.1#egg=urllib3",
            ),
        )
        assert (prefix / "src" / "urllib3" / "urllib3" / "__init__.py").is_file()
        assert not Path("src", "urllib3", "urllib3", "__init__.py").is_file()
        assert package_is_installed(prefix, "urllib3")
        prec_dump = PrefixData(prefix).get("urllib3").dump()
        prec_dump.pop("files")
        prec_dump.pop("paths_data")
        assert json.loads(json_dump(prec_dump)) == {
            "build": "dev_0",
            "build_number": 0,
            "channel": "https://conda.anaconda.org/<develop>",
            "constrains": [
                "cryptography >=1.3.4",
                "idna >=2.0.0",
                "pyopenssl >=0.14",
                "pysocks !=1.5.7,<2.0,>=1.5.6",
            ],
            "depends": ["python 3.12.*"],
            "fn": "urllib3-1.19.1-dev_0",
            "name": "urllib3",
            "package_type": "virtual_python_egg_link",
            "subdir": "pypi",
            "version": "1.19.1",
        }

        # the unmanageable urllib3 should prevent a new requests from being installed
        with pytest.raises(RuntimeError):
            conda_cli("install", f"--prefix={prefix}", "requests", "--json", "--yes")

        # should already be satisfied
        stdout, _, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "urllib3",
            "--satisfied-skip-solve",
            "--yes",
        )
        assert "All requested packages already installed." in stdout

        # should raise an error
        with pytest.raises(PackagesNotFoundError):
            # TODO: This raises PackagesNotFoundError, but the error should really explain
            #       that we can't install urllib3 because it's already installed and
            #       unmanageable. The error should suggest trying to use pip to uninstall it.
            conda_cli("install", f"--prefix={prefix}", "urllib3=1.20", "--yes")

        # Now install a manageable urllib3.
        PrefixData._cache_.clear()
        conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "install", "--upgrade", "urllib3==1.20"),
        )
        assert package_is_installed(prefix, "urllib3")
        prec_dump = PrefixData(prefix).get("urllib3").dump()
        prec_dump.pop("files")
        prec_dump.pop("paths_data")
        assert json.loads(json_dump(prec_dump)) == {
            "build": "pypi_0",
            "build_number": 0,
            "channel": "https://conda.anaconda.org/pypi",
            "constrains": ["pysocks >=1.5.6,<2.0,!=1.5.7"],
            "depends": ["python 3.12.*"],
            "fn": "urllib3-1.20.dist-info",
            "name": "urllib3",
            "package_type": "virtual_python_wheel",
            "subdir": "pypi",
            "version": "1.20",
        }

        # we should be able to install an unbundled requests that upgrades urllib3 in the process
        stdout, _, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "requests>=2.18",
            "--json",
            "--yes",
        )
        assert package_is_installed(prefix, "requests>=2.18")
        assert package_is_installed(prefix, "urllib3>=1.21")
        json_obj = json.loads(stdout)
        unlink_dists = [
            dist_obj
            for dist_obj in json_obj["actions"]["UNLINK"]
            if dist_obj.get("platform") == "pypi"
        ]  # filter out conda package upgrades like python and libffi
        assert len(unlink_dists) == 1
        assert unlink_dists[0]["name"] == "urllib3"
        assert unlink_dists[0]["channel"] == "pypi"


@pytest.mark.xfail(
    platform.machine() == "arm64", reason="packages missing for osx-arm64"
)
def test_conda_pip_interop_compatible_release_operator(
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    if "conda-forge" in context.channels:
        pytest.skip("This test is too slow with conda-forge as default channel.")
    # Regression test for #7776
    # important to start the env with six 1.9.  That version forces an upgrade later in the test
    monkeypatch.setenv("CONDA_PIP_INTEROP_ENABLED", "true")
    reset_context()
    assert context.pip_interop_enabled

    with tmp_env(
        "--channel=https://repo.anaconda.com/pkgs/free",
        "pip=10",
        "six=1.9",
        "appdirs",
    ) as prefix:
        assert package_is_installed(prefix, "pip=10")
        assert package_is_installed(prefix, "six=1.9")
        assert package_is_installed(prefix, "appdirs>=1.4.3")

        PrefixData._cache_.clear()
        _, stderr, err = conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "install", "fs==2.1.0"),
        )
        assert err
        assert "Cannot uninstall" in stderr

        conda_cli("remove", f"--prefix={prefix}", "six", "--yes")
        assert not package_is_installed(prefix, "six")

        PrefixData._cache_.clear()
        conda_cli(
            "run",
            f"--prefix={prefix}",
            *("python", "-m", "pip", "install", "fs==2.1.0"),
        )
        assert package_is_installed(prefix, "fs==2.1.0")
        assert package_is_installed(prefix, "six~=1.10")

        stdout, stderr, _ = conda_cli("list", f"--prefix={prefix}")
        assert not stderr
        assert (
            "fs                        2.1.0                    pypi_0    pypi"
            in stdout
        )

        with pytest.raises(DryRunExit):
            conda_cli(
                "install",
                f"--prefix={prefix}",
                "--channel=https://repo.anaconda.com/pkgs/free",
                "agate=1.6",
                "--dry-run",
            )


def test_use_index_cache(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    from conda.core.subdir_data import SubdirData
    from conda.gateways.connection.session import CondaSession

    # pretend the cache is always stale
    mocker.patch(
        "conda.gateways.repodata.RepodataCache.stale",
        return_value=True,
    )

    # mock CondaSession.get so we can check if it was called
    orig_get = CondaSession.get
    mock_get = mocker.patch(
        "conda.gateways.connection.session.CondaSession.get",
        autospec=True,
        side_effect=orig_get,
    )

    # populate the index cache
    SubdirData._cache_.clear()
    conda_cli("search", "flask")
    assert mock_get.called

    # update CondaSession.get mock to fail if called with a repodata URL
    def side_effect(self, url, **kwargs):
        if url.endswith(("/repodata.json", "/repodata.json.bz2", "/repodata.json.zst")):
            raise AssertionError("Index cache was not hit")
        return orig_get(self, url, **kwargs)

    mock_get.side_effect = side_effect

    # without --use-index-cache, the index cache should not be hit
    with pytest.raises(AssertionError, match="Index cache was not hit"):
        SubdirData._cache_.clear()
        conda_cli("search", "flask")

    # with --use-index-cache, the index cache should be hit
    SubdirData._cache_.clear()
    conda_cli("search", "flask", "--use-index-cache")


def test_offline_with_empty_index_cache(
    tmp_pkgs_dir: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    tmp_channel: TmpChannelFixture,
    path_factory: PathFactoryFixture,
):
    from conda.core.subdir_data import SubdirData
    from conda.gateways.connection.session import CondaSession

    SubdirData._cache_.clear()

    # mock index cache so it will be empty
    mocker.patch(
        "conda.base.context.Context.pkgs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(str(path_factory()),),
    )

    try:
        with tmp_env() as prefix, tmp_channel("zlib") as (_, channel):
            # Then attempt to install a package with --offline. The package (zlib) is
            # available in a local channel, however its dependencies are not. Make sure
            # that a) it fails because the dependencies are not available and b)
            # we don't try to download the repodata from non-local channels but we do
            # download repodata from local channels.

            orig_get = CondaSession.get
            local_channel_seen = False

            def side_effect(self, url, **kwargs):
                nonlocal local_channel_seen
                if not url.startswith("file://"):
                    raise AssertionError(f"Attempt to fetch repodata: {url}")
                if url.startswith(channel):
                    local_channel_seen = True
                return orig_get(self, url, **kwargs)

            mocker.patch(
                "conda.gateways.connection.session.CondaSession.get",
                autospec=True,
                side_effect=side_effect,
            )

            SubdirData._cache_.clear()

            assert not package_is_installed(prefix, "zlib")
            command = (
                "install",
                f"--prefix={prefix}",
                "--override-channels",
                f"--channel={channel}",
                "zlib",
                "--offline",
                "--yes",
            )
            if (
                context.solver == "libmamba"
                and version("conda-libmamba-solver") <= "23.12.0"
            ):
                # conda-libmamba-solver <=23.12.0 didn't load pkgs_dirs when offline
                with pytest.raises((RuntimeError, UnsatisfiableError)):
                    conda_cli(*command)
            else:
                # This first install passes because zlib and its dependencies are in the
                # package cache.
                conda_cli(*command)
                assert package_is_installed(prefix, "zlib")

                # The mock should have been called with our local channel URL though.
                if context.solver != "libmamba":
                    assert local_channel_seen

            # Fails because pytz cannot be found in available channels.
            # TODO: conda-libmamba-solver <=23.9.1 raises an ugly RuntimeError
            # We can remove it when 23.9.2 is out with a fix
            with pytest.raises((PackagesNotFoundError, RuntimeError)):
                conda_cli(
                    "install",
                    f"--prefix={prefix}",
                    "--override-channels",
                    f"--channel={channel}",
                    "pytz",
                    "--offline",
                    "--yes",
                )
            assert not package_is_installed(prefix, "pytz")
    finally:
        SubdirData._cache_.clear()


@pytest.mark.skipif(on_win, reason="python doesn't have dependencies on windows")
def test_disallowed_packages(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch
):
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_DISALLOWED_PACKAGES", "openssl&flask")
        reset_context()
        assert context.disallowed_packages == ("openssl", "flask")
        with pytest.raises(CondaMultiError) as exc:
            conda_cli("install", f"--prefix={prefix}", "python", "--yes")
        exc_val = exc.value.errors[0]
        assert isinstance(exc_val, DisallowedPackageError)
        assert exc_val.dump_map()["package_ref"]["name"] == "openssl"


def test_dont_remove_conda_1(
    monkeypatch: MonkeyPatch, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_ROOT_PREFIX", prefix)
        reset_context()
        assert context.root_prefix == str(prefix)
        conda_cli("install", f"--prefix={prefix}", "conda", "conda-build", "--yes")
        assert package_is_installed(prefix, "conda")
        assert package_is_installed(prefix, "pycosat")
        assert package_is_installed(prefix, "conda-build")

        with pytest.raises(CondaMultiError) as exc:
            conda_cli("remove", f"--prefix={prefix}", "conda", "--yes")

        assert any(isinstance(e, RemoveError) for e in exc.value.errors)
        assert package_is_installed(prefix, "conda")
        assert package_is_installed(prefix, "pycosat")

        with pytest.raises(CondaMultiError) as exc:
            conda_cli("remove", f"--prefix={prefix}", "pycosat", "--yes")

        assert any(isinstance(e, RemoveError) for e in exc.value.errors)
        assert package_is_installed(prefix, "conda")
        assert package_is_installed(prefix, "pycosat")
        assert package_is_installed(prefix, "conda-build")


def test_dont_remove_conda_2(
    conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture, monkeypatch: MonkeyPatch
):
    # regression test for #6904
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_ROOT_PREFIX", prefix)
        reset_context()
        assert context.root_prefix == str(prefix)

        conda_cli("install", f"--prefix={prefix}", "conda", "--yes")
        assert package_is_installed(prefix, "conda")
        assert package_is_installed(prefix, "pycosat")

        with pytest.raises(CondaMultiError) as exc:
            conda_cli("remove", f"--prefix={prefix}", "pycosat", "--yes")

        assert any(isinstance(e, RemoveError) for e in exc.value.errors)
        assert package_is_installed(prefix, "conda")
        assert package_is_installed(prefix, "pycosat")

        with pytest.raises(CondaMultiError) as exc:
            conda_cli("remove", f"--prefix={prefix}", "conda", "--yes")

        assert any(isinstance(e, RemoveError) for e in exc.value.errors)
        assert package_is_installed(prefix, "conda")
        assert package_is_installed(prefix, "pycosat")


def test_force_remove(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch
):
    with tmp_env("libarchive") as prefix:
        assert package_is_installed(prefix, "libarchive")
        assert package_is_installed(prefix, "bzip2")

        conda_cli("remove", f"--prefix={prefix}", "bzip2", "--force", "--yes")
        assert not package_is_installed(prefix, "bzip2")
        assert package_is_installed(prefix, "libarchive")

        conda_cli("remove", f"--prefix={prefix}", "libarchive", "--yes")
        assert not package_is_installed(prefix, "libarchive")


def test_download_only_flag(
    tmp_env: TmpEnvFixture, mocker: MockerFixture, conda_cli: CondaCLIFixture
):
    from conda.core.link import UnlinkLinkTransaction

    with tmp_env() as prefix:
        spy = mocker.spy(UnlinkLinkTransaction, "execute")

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "openssl",
            "--download-only",
            "--yes",
            raises=CondaExitZero,
        )
        assert spy.call_count == 0

        conda_cli("install", f"--prefix={prefix}", "openssl", "--yes")
        assert spy.call_count == 1


def test_transactional_rollback_simple(
    mocker: MockerFixture,
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
):
    mocker.patch(
        "conda.core.path_actions.CreatePrefixRecordAction.execute",
        side_effect=KeyError,
    )
    with pytest.raises(CondaMultiError):
        conda_cli("create", f"--prefix={path_factory()}", "small-executable", "--yes")


def test_transactional_rollback_upgrade_downgrade(
    mocker: MockerFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
):
    with tmp_env("dependent=1.0") as prefix:
        assert package_is_installed(prefix, "dependent=1.0")

        mocker.patch(
            "conda.core.path_actions.CreatePrefixRecordAction.execute",
            side_effect=KeyError,
        )
        with pytest.raises(CondaMultiError):
            conda_cli("install", f"--prefix={prefix}", "dependent=2.0", "--yes")
        assert package_is_installed(prefix, "dependent=1.0")


def test_directory_not_a_conda_environment(tmp_path: Path, conda_cli: CondaCLIFixture):
    (tmp_path / "tempfile.txt").write_text("hello world")

    with pytest.raises(DirectoryNotACondaEnvironmentError):
        conda_cli("install", f"--prefix={tmp_path}", "--yes")


@pytest.mark.parametrize("style", ["cli", "env"])
def test_create_env_different_platform(
    style: Literal["cli", "env"],
    test_recipes_channel: Path,
    monkeypatch: MonkeyPatch,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    platform = f"{context.subdir.split('-')[0]}-fake"

    # either set CONDA_SUBDIR or pass --platform
    if style == "cli":
        # --platforms has explicit choices, patch to use fake subdir
        monkeypatch.setattr("conda.base.constants.KNOWN_SUBDIRS", [platform])

        args = [f"--platform={platform}"]
    else:
        monkeypatch.setenv("CONDA_SUBDIR", platform)
        reset_context()
        assert context.subdir == platform

        args = []

    with tmp_env(*args) as prefix:
        # check that the subdir is defined in environment's condarc
        # which is generated during the `conda create` command (via tmp_env)
        assert (
            yaml_round_trip_load((prefix / ".condarc").read_text())["subdir"]
            == platform
        )

        stdout, stderr, excinfo = conda_cli(
            "install",
            f"--prefix={prefix}",
            "arch-package",
            "--dry-run",
            "--json",
            raises=DryRunExit,
        )
        assert stdout
        assert not stderr
        assert isinstance(excinfo.value, DryRunExit)

        # ensure the package to install is from the fake platform
        result = json.loads(stdout)
        assert result["success"]
        assert any(
            pkg["name"] == "arch-package" and pkg["platform"] == platform
            for pkg in result["actions"]["LINK"]
        )


def test_conda_downgrade(
    monkeypatch: MonkeyPatch, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    # Create an environment with the current conda under test, but include an earlier
    # version of conda and other packages in that environment.
    # Make sure we can flip back and forth.

    monkeypatch.setenv("CONDA_AUTO_UPDATE_CONDA", "false")
    monkeypatch.setenv("CONDA_ALLOW_CONDA_DOWNGRADES", "true")
    monkeypatch.setenv("CONDA_DLL_SEARCH_MODIFICATION_ENABLE", "1")

    # elevate verbosity so we can inspect subprocess' stdout/stderr
    monkeypatch.setenv("CONDA_VERBOSE", "2")

    with tmp_env("python=3.11", "conda") as prefix:  # rev 0
        python_exe = str(prefix / PYTHON_BINARY)
        conda_exe = str(prefix / BIN_DIRECTORY / ("conda.exe" if on_win else "conda"))
        assert (py_prec := package_is_installed(prefix, "python"))
        assert (conda_prec := package_is_installed(prefix, "conda"))

        # runs our current version of conda to install into the foreign env
        conda_cli("install", f"--prefix={prefix}", "filelock", "--yes")  # rev 1
        assert package_is_installed(prefix, "filelock")

        # runs the conda in the env to install something new into the env
        PrefixData._cache_.clear()
        subprocess_call_with_clean_env(
            [conda_exe, "install", f"--prefix={prefix}", "itsdangerous", "--yes"],
            path=prefix,
        )  # rev 2
        assert package_is_installed(prefix, "itsdangerous")

        # downgrade the version of conda in the env, using our dev version of conda
        PrefixData._cache_.clear()
        subprocess_call(
            [
                python_exe,
                "-m",
                "conda",
                "install",
                f"--prefix={prefix}",
                f"conda<{conda_prec.version}",
                "--yes",
            ],
            path=prefix,
            raise_on_error=False,
        )  # rev 3
        assert package_is_installed(prefix, f"conda<{conda_prec.version}")

        # undo the conda downgrade in the env (using our current outer conda version)
        conda_cli("install", f"--prefix={prefix}", "--rev=2", "--yes")
        assert package_is_installed(prefix, f"python={py_prec.version}")
        assert package_is_installed(prefix, f"conda={conda_prec.version}")
        assert package_is_installed(prefix, "filelock")
        assert package_is_installed(prefix, "itsdangerous")

        # use the conda in the env to revert to a previous state
        PrefixData._cache_.clear()
        subprocess_call_with_clean_env(
            [conda_exe, "install", f"--prefix={prefix}", "--rev=1", "--yes"],
            path=prefix,
        )
        assert package_is_installed(prefix, f"python={py_prec.version}")
        assert package_is_installed(prefix, f"conda={conda_prec.version}")
        assert package_is_installed(prefix, "filelock")
        assert not package_is_installed(prefix, "itsdangerous")

        result = subprocess_call_with_clean_env(
            [conda_exe, "info", "--json"],
            path=prefix,
        )
        assert json.loads(result.stdout)["conda_version"] == conda_prec.version


@pytest.mark.skipif(
    on_win or platform.machine() == "arm64",
    reason="openssl only has a postlink script on unix / package missing for osx-arm64",
)
def test_run_script_called(tmp_env: TmpEnvFixture):
    import conda.core.link

    with patch.object(conda.core.link, "subprocess_call") as rs:
        rs.return_value = Response(None, None, 0)
        with tmp_env(
            "--channel=http://repo.anaconda.com/pkgs/free",
            "openssl=1.0.2j",
            "--no-deps",
        ) as prefix:
            assert package_is_installed(prefix, "openssl")
            assert rs.call_count == 1


@pytest.mark.xfail(on_mac, reason="known broken; see #11127")
def test_post_link_run_in_env(tmp_env: TmpEnvFixture):
    test_pkg = "_conda_test_env_activated_when_post_link_executed"
    # a non-unicode name must be provided here as activate.d scripts
    # are not executed on windows, see https://github.com/conda/conda/issues/8241
    with tmp_env(test_pkg, "--channel=conda-test") as prefix:
        assert package_is_installed(prefix, test_pkg)


def test_package_cache_regression(
    test_recipes_channel: Path, tmp_pkgs_dir: Path, tmp_env: TmpEnvFixture
):
    with tmp_env("small-executable") as prefix:
        assert package_is_installed(prefix, "small-executable")


def test_remove_spellcheck(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env("dependent") as prefix:
        assert package_is_installed(prefix, "dependent")

    with pytest.raises(
        PackagesNotFoundError,
        match=r"The following packages are missing from the target environment:\s+- dependint",
    ):
        conda_cli("remove", f"--prefix={prefix}", "dependint", "--yes")


@pytest.mark.skipif(
    context.subdir == "win-32", reason="dependencies not available for win-32"
)
def test_cross_channel_incompatibility(conda_cli: CondaCLIFixture, tmp_path: Path):
    # regression test for https://github.com/conda/conda/issues/8772
    # conda-forge puts a run_constrains on libboost, which they don't have on conda-forge.
    #   This is a way of forcing libboost to be removed.  It's a way that they achieve
    #   mutual exclusivity with the boost from defaults that works differently.

    # if this test passes, we'll hit the DryRunExit exception, instead of an UnsatisfiableError
    with pytest.raises(DryRunExit):
        conda_cli(
            "create",
            f"--prefix={tmp_path}",
            "--dry-run",
            "--override-channels",
            "--channel=conda-forge",
            "--channel=defaults",
            "python",
            "boost==1.82.0",
            "boost-cpp==1.82.0",
            "--yes",
        )


# https://github.com/conda/conda/issues/9124
@pytest.mark.skipif(
    context.subdir != "linux-64",
    reason="lazy; package constraint here only valid on linux-64",
)
def test_neutering_of_historic_specs(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env("main::psutil=5.6.3=py37h7b6447c_0") as prefix:
        conda_cli("install", f"--prefix={prefix}", "python=3.6", "--yes")
        d = (prefix / "conda-meta" / "history").read_text()
        assert re.search(r"neutered specs:.*'psutil==5.6.3'\]", d)
        # this would be unsatisfiable if the neutered specs were not being factored in correctly.
        #    If this command runs successfully (does not raise), then all is well.
        conda_cli("install", f"--prefix={prefix}", "imagesize", "--yes")


# https://github.com/conda/conda/issues/10116
@pytest.mark.skipif(
    not context.subdir.startswith("linux"), reason="__glibc only available on linux"
)
def test_install_bound_virtual_package(tmp_env: TmpEnvFixture):
    with tmp_env("__glibc>0"):
        pass


@pytest.mark.parametrize(
    "spec,dry_run",
    [
        ("__glibc", on_linux),
        ("__unix", on_linux or on_mac),
        ("__linux", on_linux),
        ("__osx", on_mac),
        ("__win", on_win),
    ],
)
def test_install_virtual_packages(conda_cli: CondaCLIFixture, spec: str, dry_run: bool):
    """
    Ensures a solver knows how to deal with virtual specs in the CLI.
    This means succeeding only if the virtual package is available.
    https://github.com/conda/conda-libmamba-solver/issues/480
    """
    conda_cli(
        "create",
        "--dry-run",
        "--offline",
        spec,
        raises=DryRunExit if dry_run else (UnsatisfiableError, PackagesNotFoundError),
    )


@pytest.mark.integration
def test_remove_empty_env(tmp_path: Path, conda_cli: CondaCLIFixture):
    conda_cli("create", f"--prefix={tmp_path}", "--yes")
    conda_cli("remove", f"--prefix={tmp_path}", "--all", "--yes")


def test_remove_ignore_nonenv(tmp_path: Path, conda_cli: CondaCLIFixture):
    filename = tmp_path / "file.dat"
    filename.touch()

    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("remove", f"--prefix={tmp_path}", "--all", "--yes")

    assert filename.exists()
    assert tmp_path.exists()


def test_repodata_v2_base_url(
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    request: FixtureRequest,
):
    if context.solver == "libmamba" and VersionOrder(
        version("libmambapy")
    ) < VersionOrder("2.0a0"):
        request.applymarker(
            pytest.mark.xfail(
                context.solver == "libmamba",
                reason="Libmamba v1 does not support CEP-15.",
                strict=True,
                run=True,
            )
        )
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(tmp_path / "pkgs"))
    reset_context()
    prefix = tmp_path / "env"
    platform = (
        "linux-64"
        if context.subdir not in ("win-64", "linux-64", "osx-64")
        else context.subdir
    )
    conda_cli(
        "create",
        f"--prefix={prefix}",
        "--yes",
        "--override-channels",
        "-c",
        CHANNEL_DIR_V2,
        "ca-certificates",
        "--platform",
        platform,
    )
    assert package_is_installed(prefix, "ca-certificates")


def test_create_dry_run_without_prefix(
    conda_cli: CondaCLIFixture, capsys: CaptureFixture
):
    with pytest.raises(DryRunExit):
        conda_cli("create", "--dry-run", "--json", "ca-certificates")
    out, _ = capsys.readouterr()
    data = json.loads(out)
    assert any(
        pkg for pkg in data["actions"]["LINK"] if pkg["name"] == "ca-certificates"
    )


def test_create_without_prefix_raises_argument_error(conda_cli: CondaCLIFixture):
    conda_cli("create", "--json", "ca-certificates", raises=ArgumentError)


def test_nonadmin_file_untouched(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    channel = Path(__file__).parent / "test-recipes" / "noarch"
    with tmp_env() as prefix:
        nonadmin_file = prefix / ".nonadmin"
        nonadmin_file.touch()
        assert nonadmin_file.is_file()
        conda_cli(
            "install", "--yes", "--prefix", prefix, "--channel", channel, "dependency"
        )
        assert nonadmin_file.is_file(), ".nonadmin file removed after installation"
        conda_cli("remove", "--yes", "--prefix", prefix, "dependency")
        assert nonadmin_file.is_file(), ".nonadmin file removed after uninstallation"


@pytest.mark.skipif(on_win, reason="sample packages used unix style paths")
def test_python_site_packages_path(
    test_recipes_channel: Path,
    request: FixtureRequest,
    tmp_env: TmpEnvFixture,
):
    """
    When a python package that includes the optional python_site_packages_path repodata record is installed
    noarch: python packages should be installed into that path.

    Reference: https://github.com/conda/conda/issues/14053
    """
    # TODO update this to a version check once conda-libmamba-solver supports python_site_packages_path
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="conda-libmamba-solver does not support python_site_packages_path",
        )
    )
    with tmp_env("python=3.99.99", "sample_noarch_python=1.0.0") as prefix:
        sp_dir = "lib/python3.99t/site-packages"
        assert (prefix / sp_dir / "sample.py").is_file()
