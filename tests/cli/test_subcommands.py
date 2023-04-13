# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path
from typing import Callable, ContextManager

import pytest

from conda.common.compat import on_win


@pytest.fixture
def environment_yml(path_factory: Callable) -> Path:
    path = path_factory(name="environment.yml")
    path.write_text(
        "name: scratch\n"
        "channels:\n"
        "  - defaults\n"
        "dependencies:\n"
        "  - ca-certificates=2023\n"
    )
    return path


def test_clean(run: Callable):
    out, err, code = run("clean", "--all", "--yes")
    assert out
    assert not err
    assert not code


def test_create(run: Callable, path_factory: Callable):
    out, err, code = run("create", "--prefix", path_factory(), "--yes")
    assert out
    assert not err
    assert not code


def test_compare(run: Callable, tmp_env: ContextManager, environment_yml: Path):
    with tmp_env() as prefix:
        out, err, code = run("compare", "--prefix", prefix, environment_yml)
        assert out
        assert not err
        assert code


def test_config(run: Callable):
    out, err, code = run("config", "--show-sources")
    assert out
    assert not err
    assert not code


def test_info(run: Callable):
    out, err, code = run("info")
    assert out
    assert not err
    assert not code


def test_init(run: Callable):
    out, err, code = run("init", "--dry-run")
    assert out
    assert not err
    assert not code


def test_install(run: Callable, tmp_env: ContextManager):
    with tmp_env() as prefix:
        out, err, code = run("install", "--prefix", prefix, "ca-certificates", "--yes")
        assert out
        assert not err
        assert not code


def test_list(run: Callable):
    out, err, code = run("list")
    assert out
    assert not err
    assert not code


def test_notices(run: Callable):
    out, err, code = run("notices")
    assert out
    assert not err
    assert not code


def test_package(run: Callable, tmp_env: ContextManager):
    with tmp_env() as prefix:
        out, err, code = run("package", "--prefix", prefix)
        assert out
        assert not err
        assert not code


@pytest.mark.parametrize("subcommand", ["remove", "uninstall"])
def test_remove(subcommand: str, run: Callable, tmp_env: ContextManager):
    with tmp_env() as prefix:
        out, err, code = run(subcommand, "--prefix", prefix, "--all", "--yes")
        assert out
        assert not err
        assert not code


def test_rename(run: Callable, tmp_env: ContextManager, path_factory: Callable):
    with tmp_env() as prefix:
        out, err, code = run("rename", "--prefix", prefix, path_factory())
        assert out
        assert not err
        assert not code


def test_run(run: Callable, tmp_env: ContextManager):
    with tmp_env("m2-patch" if on_win else "patch") as prefix:
        out, err, code = run("run", "--prefix", prefix, "patch", "--help")
        assert out
        assert not err
        assert not code


def test_search(run: Callable):
    out, err, code = run("search", "python")
    assert out
    assert not err
    assert not code


@pytest.mark.parametrize("subcommand", ["update", "upgrade"])
def test_update(subcommand: str, run: Callable, tmp_env: ContextManager):
    with tmp_env("ca-certificates<2023") as prefix:
        out, err, code = run(subcommand, "--prefix", prefix, "--all", "--yes")
        assert out
        assert not err
        assert not code


def test_env_list(run: Callable):
    assert run("env", "list") == run("info", "--envs")


def test_env_export(run: Callable):
    out, err, code = run("env", "export")
    assert out
    assert not err
    assert not code


def test_env_remove(run: Callable, tmp_env: ContextManager):
    with tmp_env() as prefix:
        out, err, code = run("env", "remove", "--prefix", prefix, "--yes")
        assert out
        assert not err
        assert not code


def test_env_create(run: Callable, path_factory: Callable, environment_yml: Path):
    out, err, code = run(
        "env", "create", "--prefix", path_factory(), "--file", environment_yml
    )
    assert out
    assert not err
    assert not code


def test_env_update(run: Callable, tmp_env: ContextManager, environment_yml: Path):
    with tmp_env("ca-certificates<2023") as prefix:
        out, err, code = run(
            "env", "update", "--prefix", prefix, "--file", environment_yml
        )
        assert out
        assert not err
        assert not code


def test_env_config_vars(run: Callable, tmp_env: ContextManager):
    with tmp_env() as prefix:
        out, err, code = run(
            "env", "config", "vars", "set", "--prefix", prefix, "FOO=foo"
        )
        assert not out
        assert not err
        assert not code

        out, err, code = run("env", "config", "vars", "list", "--prefix", prefix)
        assert out
        assert not err
        assert not code

        out, err, code = run(
            "env", "config", "vars", "unset", "--prefix", prefix, "FOO"
        )
        assert not out
        assert not err
        assert not code
