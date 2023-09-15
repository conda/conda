# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, ContextManager

import pytest

from conda.common.compat import on_win
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture


@pytest.fixture
def environment_yml(path_factory: PathFactoryFixture) -> Path:
    path = path_factory(name="environment.yml")
    path.write_text(
        "name: scratch\n"
        "channels:\n"
        "  - defaults\n"
        "dependencies:\n"
        "  - ca-certificates=2023\n"
    )
    return path


def test_clean(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("clean", "--all", "--yes")
    assert out
    assert not err
    assert not code


def test_create(conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture):
    out, err, code = conda_cli("create", "--prefix", path_factory(), "--yes")
    assert out
    assert not err
    assert not code


def test_compare(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    environment_yml: Path,
):
    with tmp_env() as prefix:
        out, err, code = conda_cli("compare", "--prefix", prefix, environment_yml)
        assert out
        assert not err
        assert code


def test_config(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("config", "--show-sources")
    assert out
    assert not err
    assert not code


def test_doctor(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("doctor")
    assert out
    assert not err
    assert not code


def test_info(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("info")
    assert out
    assert not err
    assert not code


def test_info_json(conda_cli: CondaCLIFixture):
    out1, err, code = conda_cli("info", "--json")
    assert json.loads(out1)
    assert not err
    assert not code

    out2, err, code = conda_cli("--json", "info")
    assert json.loads(out2)
    assert not err
    assert not code

    assert out1 == out2


def test_init(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("init", "--dry-run")
    assert out
    assert not err
    assert not code


def test_install(conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        out, err, code = conda_cli(
            "install",
            *("--prefix", prefix),
            "ca-certificates",
            "--yes",
        )
        assert out
        assert not err
        assert not code


def test_list(conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env("ca-certificates") as prefix:
        out, err, code = conda_cli("list", "--prefix", prefix)
        assert out
        assert not err
        assert not code


def test_notices(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("notices")
    assert out
    assert not err
    assert not code


def test_package(conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        out, err, code = conda_cli("package", "--prefix", prefix)
        assert out
        assert not err
        assert not code


@pytest.mark.parametrize("subcommand", ["remove", "uninstall"])
def test_remove(subcommand: str, conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        out, err, code = conda_cli(subcommand, "--prefix", prefix, "--all", "--yes")
        assert out
        assert not err
        assert not code


@pytest.mark.parametrize("subcommand", ["remove", "uninstall"])
def test_remove_all_json(
    subcommand: str, conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture
):
    # Test that the json output is valid
    # regression test for #13019
    with tmp_env("ca-certificates") as prefix:
        out, err, code = conda_cli(subcommand, "--prefix", prefix, "--all", "--json")
        json_obj = json.loads(out)
        assert "UNLINK" in json_obj["actions"]
        assert not err
        assert not code


def test_rename(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    path_factory: PathFactoryFixture,
):
    with tmp_env() as prefix:
        out, err, code = conda_cli("rename", "--prefix", prefix, path_factory())
        assert out
        assert not err
        assert not code


def test_run(conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env("m2-patch" if on_win else "patch") as prefix:
        out, err, code = conda_cli("run", "--prefix", prefix, "patch", "--help")
        assert out
        assert not err
        assert not code


def test_search(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("search", "python")
    assert out
    assert not err
    assert not code


@pytest.mark.parametrize("subcommand", ["update", "upgrade"])
def test_update(subcommand: str, conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env("ca-certificates<2023") as prefix:
        out, err, code = conda_cli(subcommand, "--prefix", prefix, "--all", "--yes")
        assert out
        assert not err
        assert not code


def test_env_list(conda_cli: CondaCLIFixture):
    assert conda_cli("env", "list") == conda_cli("info", "--envs")


def test_env_export(conda_cli: CondaCLIFixture):
    out, err, code = conda_cli("env", "export")
    assert out
    assert not err
    assert not code


def test_env_remove(conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        out, err, code = conda_cli("env", "remove", "--prefix", prefix, "--yes")
        assert out
        assert not err
        assert not code


def test_env_create(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    environment_yml: Path,
):
    out, err, code = conda_cli(
        "env",
        "create",
        *("--prefix", path_factory()),
        *("--file", environment_yml),
    )
    assert out
    assert not err
    assert not code


def test_env_update(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    environment_yml: Path,
):
    with tmp_env("ca-certificates<2023") as prefix:
        out, err, code = conda_cli(
            "env",
            "update",
            *("--prefix", prefix),
            *("--file", environment_yml),
        )
        assert out
        assert not err
        assert not code


def test_env_config_vars(conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        out, err, code = conda_cli(
            "env",
            "config",
            "vars",
            "set",
            *("--prefix", prefix),
            "FOO=foo",
        )
        assert not out
        assert not err
        assert not code

        out, err, code = conda_cli("env", "config", "vars", "list", "--prefix", prefix)
        assert out
        assert not err
        assert not code

        out, err, code = conda_cli(
            "env",
            "config",
            "vars",
            "unset",
            *("--prefix", prefix),
            "FOO",
        )
        assert not out
        assert not err
        assert not code
