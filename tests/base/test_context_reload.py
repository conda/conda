# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from argparse import Namespace
from threading import Lock
from typing import TYPE_CHECKING

import pytest
from conda import CondaError
from conda.base.context import Context, reset_context
from conda.common.constants import NULL
from ruamel.yaml.error import YAMLError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


@pytest.mark.parametrize("target_argument", ["prefix", "name"])
def test_reload_preserves_complete_invocation_and_target(
    tmp_path: Path, monkeypatch: MonkeyPatch, target_argument: str
) -> None:
    envs = tmp_path / "envs"
    target = envs / "selected"
    (target / "conda-meta").mkdir(parents=True)
    (target / "conda-meta" / "history").write_text("")
    monkeypatch.setenv("CONDA_ENVS_PATH", str(envs))
    reset_context(search_path=())
    source = tmp_path / "config.yaml"
    source.write_text("channels: [original]\n")
    args = Namespace(
        **{target_argument: str(target) if target_argument == "prefix" else "selected"},
        packages=["python", "numpy"],
        file=["requirements.txt"],
        command="create",
        force_reinstall=True,
        no_deps=True,
        arbitrary_embedding_value={"key": ["value"]},
        optional=NULL,
    )
    context = Context(search_path=(source,), argparse_args=args)
    before = dict(context._argparse_args)
    assert context.target_prefix == str(target)
    source.write_text("channels: [updated]\n")

    assert context.reload() is context

    assert context.channels == ("updated",)
    assert context.target_prefix == str(target)
    assert context._argparse_args == before
    assert context._configuration_argparse_args.optional is NULL


def test_reload_discovers_new_files_from_original_search_specification(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "future.yaml"
    directory = tmp_path / "condarc.d"
    context = Context(search_path=(entry for entry in (missing, directory)))
    missing.write_text("channels: [first]\n")
    directory.mkdir()
    (directory / "vendor.yaml").write_text("channels: [second]\n")

    context.reload()

    assert context.channels == ("second", "first")
    assert set(context._search_path) == {missing, directory / "vendor.yaml"}


def test_reload_discovers_target_prefix_configuration(tmp_path: Path) -> None:
    target = tmp_path / "selected"
    context = Context(
        search_path=("$CONDA_PREFIX/condarc.d",),
        argparse_args=Namespace(prefix=str(target)),
    )
    directory = target / "condarc.d"
    directory.mkdir(parents=True)
    (directory / "new.yaml").write_text("channels: [organization]\n")
    context.reload()
    assert context.channels == ("organization",)
    assert context.target_prefix == str(target)


def test_reload_updates_environment_and_keeps_command_precedence(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    source = tmp_path / "config.yaml"
    source.write_text("channels: [original]\n")
    context = Context(search_path=(source,), argparse_args=Namespace(quiet=True))
    monkeypatch.setenv("CONDA_CHANNELS", "environment-channel")
    monkeypatch.setenv("CONDA_QUIET", "false")
    context.reload()
    assert context.channels == ("environment-channel", "original")
    assert context.quiet


@pytest.mark.parametrize(
    "invalid", ["channel_priority: unsupported\n", "channels: [\n"]
)
def test_reload_failure_preserves_current_configuration(
    tmp_path: Path, invalid: str
) -> None:
    source = tmp_path / "config.yaml"
    source.write_text("channels: [original]\n")
    context = Context(search_path=(source,))
    source.write_text(invalid)

    with pytest.raises((CondaError, YAMLError)):
        context.reload()

    assert context.channels == ("original",)


def test_reload_retains_reset_callbacks() -> None:
    context = Context(search_path=())
    called = []
    context.register_reset_callback(lambda: called.append(True))
    context.reload()
    assert called == [True]


def test_reload_invalidates_sessions_and_plugin_result_caches() -> None:
    from conda.gateways.connection.session import CondaSession

    context = Context(search_path=())
    session = CondaSession()
    manager = context.plugin_manager
    manager.get_cached_solver_backend("classic")
    manager.get_cached_session_headers("example.invalid")
    manager.get_cached_request_headers("example.invalid", "/channel")
    context.reload()
    assert CondaSession() is not session
    assert manager.get_cached_solver_backend.cache_info().currsize == 0
    assert manager.get_cached_session_headers.cache_info().currsize == 0
    assert manager.get_cached_request_headers.cache_info().currsize == 0


def test_reload_keeps_embedded_objects_without_copying_them() -> None:
    lock = Lock()
    args = Namespace(embedded_module=sys, embedded_lock=lock)
    context = Context(search_path=(), argparse_args=args)
    context.reload()
    assert context._argparse_args.embedded_module is sys
    assert context._argparse_args.embedded_lock is lock
