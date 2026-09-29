# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.exceptions import EnvironmentLocationNotFound

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture
    from tests.plugins.subcommands.conftest import EnvFixture


def test_conda_doctor_happy_path(conda_cli: CondaCLIFixture):
    """Make sure that we are able to call the ``conda doctor`` command"""

    out, err, code = conda_cli("doctor")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_verbose(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run ``conda doctor`` command with the --verbose flag"""

    out, err, code = conda_cli("doctor", "--verbose")

    assert not err  # no error message
    assert not code  # successful exit code


def test_conda_doctor_happy_path_show_help(conda_cli: CondaCLIFixture):
    """Make sure that we are able to run ``conda doctor`` command with the --help flag"""
    out, err, exc = conda_cli("doctor", "--help", raises=SystemExit)

    assert "conda doctor" in out
    assert "--override-frozen" in out
    assert "--list" in out
    assert "--fix, --heal" in out
    assert not err
    assert exc.value.code == 0


def test_conda_doctor_with_test_environment(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure that we are able to call ``conda doctor`` command for a specific environment"""

    with tmp_env() as prefix:
        out, err, code = conda_cli("doctor", f"--prefix={prefix}")

        assert "There are no packages with missing files." in out
        assert not err  # no error message
        assert not code  # successful exit code


def test_conda_doctor_with_non_existent_environment(conda_cli: CondaCLIFixture):
    """Make sure that ``conda doctor`` detects a non existent environment path"""
    # with pytest.raises(EnvironmentLocationNotFound):
    out, err, exc = conda_cli(
        "doctor",
        "--prefix=non/existent/path",
        raises=EnvironmentLocationNotFound,
    )
    assert not out
    assert not err  # no error message
    assert exc


def test_conda_doctor_list(conda_cli: CondaCLIFixture):
    """Make sure --list shows available health checks."""
    out, err, code = conda_cli("doctor", "--list")

    assert "Available health checks:" in out
    assert "missing-files" in out  # built-in check
    assert not err
    assert not code


def test_conda_doctor_specific_check(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure we can run a specific health check by id."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("doctor", "missing-files", f"--prefix={prefix}")

        assert "There are no packages with missing files." in out
        # Should NOT run other checks like altered files
        assert (
            "altered" not in out.lower()
            or "no packages with altered files" in out.lower()
        )
        assert not err
        assert not code


def test_conda_doctor_fix_dry_run(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure --fix --dry-run doesn't make actual changes."""
    with tmp_env() as prefix:
        out, err, code = conda_cli("doctor", "--fix", "--dry-run", f"--prefix={prefix}")
        # Dry run triggers DryRunExit which results in exit code 1
        # The important thing is that no actual changes are made
        assert "Running fixes" in out
        # Verify dry-run was triggered (logged as warning)
        assert "Dry run" in err


def test_conda_doctor_fix_yes(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """Make sure --fix --yes skips confirmation prompts."""
    with tmp_env() as prefix:
        out, err, code = conda_cli(
            "doctor",
            "--fix",
            "--yes",
            f"--prefix={prefix}",
        )
        # Should complete without prompting
        assert not err
        assert not code


def test_conda_doctor_fix_accepts_override_frozen(
    conda_cli: CondaCLIFixture,
    env_missing_files: EnvFixture,
    mocker: MockerFixture,
):
    """Make sure --fix can bypass frozen environment protection."""
    (env_missing_files.prefix / "conda-meta" / "history").touch()
    (env_missing_files.prefix / "conda-meta" / "frozen").touch()

    def reinstall_packages(args, specs, force_reinstall=False):
        assert context.protect_frozen_envs is False
        assert specs == [f"{env_missing_files.package}=1.0=0"]
        assert force_reinstall is True
        return 0

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.missing_files.reinstall_packages",
        side_effect=reinstall_packages,
    )

    out, err, code = conda_cli(
        "doctor",
        "missing-files",
        "--fix",
        "--yes",
        f"--prefix={env_missing_files.prefix}",
        "--override-frozen",
    )

    assert "Running fixes" in out
    assert not err
    assert code == 0
    mock_reinstall.assert_called_once()


@pytest.mark.parametrize(
    ("check", "module"),
    [
        pytest.param("missing-files", "missing_files", id="missing-files"),
        pytest.param("altered-files", "altered_files", id="altered-files"),
    ],
)
def test_conda_doctor_fix_invalid_json(
    conda_cli: CondaCLIFixture,
    env_ok: EnvFixture,
    mocker: MockerFixture,
    check: str,
    module: str,
):
    """Test that invalid package metadata makes the fixer fail."""
    (env_ok.prefix / "conda-meta" / "history").touch()
    metadata = env_ok.prefix / "conda-meta" / f"{env_ok.package}.json"
    metadata.write_text("{")

    mock_reinstall = mocker.patch(
        f"conda.plugins.subcommands.doctor.health_checks.{module}.reinstall_packages"
    )

    _, _, code = conda_cli(
        "doctor",
        check,
        "--fix",
        "--yes",
        f"--prefix={env_ok.prefix}",
    )

    assert code == 1
    mock_reinstall.assert_not_called()


def test_conda_doctor_fix_missing_files_malformed_meta(
    conda_cli: CondaCLIFixture,
    env_missing_files: EnvFixture,
    mocker: MockerFixture,
):
    """Test that malformed metadata leads to reinstall failure"""
    meta = env_missing_files.prefix / "conda-meta" / f"{env_missing_files.package}.json"
    (env_missing_files.prefix / "conda-meta" / "history").touch()
    data = json.loads(meta.read_text())
    del data["version"]
    meta.write_text(json.dumps(data))

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.missing_files.reinstall_packages",
        return_value=0,
    )

    out, err, code = conda_cli(
        "doctor",
        "missing-files",
        "--fix",
        "--yes",
        f"--prefix={env_missing_files.prefix}",
    )

    assert code == 1
    mock_reinstall.assert_not_called()


def test_conda_doctor_fix_missing_files_mixed_meta(
    conda_cli: CondaCLIFixture,
    env_missing_files: EnvFixture,
    mocker: MockerFixture,
):
    """Test fixer reinstalls valid packages but exits nonzero when some conda-meta records are malformed."""

    (env_missing_files.prefix / "conda-meta" / "history").touch()

    bad_meta = (
        env_missing_files.prefix / "conda-meta" / f"{env_missing_files.package}.json"
    )
    data = json.loads(bad_meta.read_text())
    del data["build"]
    bad_meta.write_text(json.dumps(data))

    (env_missing_files.prefix / "conda-meta" / "goodpkg.json").write_text(
        json.dumps(
            {
                "name": "goodpkg",
                "version": "2.0",
                "build": "1",
                "files": ["bin/goodpkg"],
            }
        )
    )

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.missing_files.reinstall_packages",
        return_value=0,
    )

    _, _, code = conda_cli(
        "doctor",
        "missing-files",
        "--fix",
        "--yes",
        f"--prefix={env_missing_files.prefix}",
    )

    assert code == 1
    mock_reinstall.assert_called_once_with(
        mocker.ANY, ["goodpkg=2.0=1"], force_reinstall=True
    )


def test_conda_doctor_fix_altered_files_malformed_meta(
    conda_cli: CondaCLIFixture,
    env_altered_files: EnvFixture,
    mocker: MockerFixture,
):
    """Test that incomplete metadata prevents an altered package reinstall."""
    (env_altered_files.prefix / "conda-meta" / "history").touch()
    metadata = (
        env_altered_files.prefix / "conda-meta" / f"{env_altered_files.package}.json"
    )
    data = json.loads(metadata.read_text())
    del data["build"]
    metadata.write_text(json.dumps(data))

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.altered_files.reinstall_packages"
    )

    _, _, code = conda_cli(
        "doctor",
        "altered-files",
        "--fix",
        "--yes",
        f"--prefix={env_altered_files.prefix}",
    )

    assert code == 1
    mock_reinstall.assert_not_called()


def test_conda_doctor_fix_altered_files_mixed_meta(
    conda_cli: CondaCLIFixture,
    env_altered_files: EnvFixture,
    mocker: MockerFixture,
):
    """Test that valid altered packages are reinstalled after another is skipped."""
    (env_altered_files.prefix / "conda-meta" / "history").touch()

    bad_metadata = (
        env_altered_files.prefix / "conda-meta" / f"{env_altered_files.package}.json"
    )
    data = json.loads(bad_metadata.read_text())
    del data["build"]
    bad_metadata.write_text(json.dumps(data))

    good_path = "lib/goodpkg.py"
    (env_altered_files.prefix / good_path).write_text("altered")
    (env_altered_files.prefix / "conda-meta" / "goodpkg.json").write_text(
        json.dumps(
            {
                "name": "goodpkg",
                "version": "2.0",
                "build": "1",
                "files": [good_path],
                "paths_data": {
                    "paths_version": 1,
                    "paths": [
                        {
                            "_path": good_path,
                            "sha256_in_prefix": "0" * 64,
                        }
                    ],
                },
            }
        )
    )

    mock_reinstall = mocker.patch(
        "conda.plugins.subcommands.doctor.health_checks.altered_files.reinstall_packages",
        return_value=0,
    )

    _, _, code = conda_cli(
        "doctor",
        "altered-files",
        "--fix",
        "--yes",
        f"--prefix={env_altered_files.prefix}",
    )

    assert code == 1
    mock_reinstall.assert_called_once_with(
        mocker.ANY,
        ["goodpkg=2.0=1"],
        force_reinstall=True,
    )
