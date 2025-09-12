# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import platform
from typing import TYPE_CHECKING

import pytest
from pytest import MonkeyPatch

import conda.core.index
from conda import __version__, plugins
from conda.base.context import context, reset_context
from conda.common._os.osx import mac_ver
from conda.common.compat import on_linux, on_mac, on_win
from conda.exceptions import PluginError
from conda.plugins.types import CondaVirtualPackage
from conda.plugins.virtual_packages import cuda
from conda.testing.solver_helpers import package_dict

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytest import MonkeyPatch

    from conda.models.records import PackageRecord


class VirtualPackagesPlugin:
    @plugins.hookimpl
    def conda_virtual_packages(self):
        yield CondaVirtualPackage(
            name="abc",
            version="123",
            build=None,
        )
        yield CondaVirtualPackage(
            name="def",
            version="456",
            build=None,
        )
        yield CondaVirtualPackage(
            name="ghi",
            version="789",
            build="xyz",
        )


@pytest.fixture()
def plugin(plugin_manager):
    plugin = VirtualPackagesPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_invoked(plugin):
    index = conda.core.index.ReducedIndex(
        prefix=context.default_prefix,
        channels=context.default_channels,
        subdirs=context.subdirs,
        specs=(),
        repodata_fn=context.repodata_fns[0],
    )

    packages = package_dict(index)

    assert packages["__abc"].version == "123"
    assert packages["__def"].version == "456"
    assert packages["__ghi"].version == "789"
    assert packages["__ghi"].build == "xyz"


def test_duplicated(plugin_manager):
    plugin_manager.register(VirtualPackagesPlugin())
    plugin_manager.register(VirtualPackagesPlugin())

    with pytest.raises(
        PluginError, match=r"Conflicting plugins found for `virtual_packages`"
    ):
        conda.core.index.ReducedIndex(
            prefix=context.default_prefix,
            channels=context.default_channels,
            subdirs=context.subdirs,
            specs=(),
            repodata_fn=context.repodata_fns[0],
        )


def test_cuda_detection(clear_cuda_version):
    # confirm that CUDA detection doesn't raise exception
    version = cuda.cuda_version()
    assert version is None or isinstance(version, str)


@pytest.mark.parametrize(
    "override_value,expected",
    [
        pytest.param("4.5", "4.5", id="override-set"),
        pytest.param("", None, id="override-empty"),
    ],
)
def test_cuda_override(
    clear_cuda_version, override_value, expected, monkeypatch: MonkeyPatch
):
    monkeypatch.setenv("CONDA_OVERRIDE_CUDA", override_value)
    reset_context()

    version = cuda.cuda_version()
    assert version == expected


def get_virtual_precs() -> Iterable[PackageRecord]:
    index = conda.core.index.ReducedIndex(
        prefix=context.default_prefix,
        channels=context.default_channels,
        subdirs=context.subdirs,
        specs=(),
        repodata_fn=context.repodata_fns[0],
    )

    yield from (
        prec
        for prec in index
        if prec.channel.name == "@" and prec.name.startswith("__")
    )


@pytest.mark.parametrize(
    "subdir,expected",
    [
        # see conda.base.constants.KNOWN_SUBDIRS
        pytest.param("emscripten-wasm32", [], id="emscripten-wasm32"),
        pytest.param("freebsd-64", ["__unix"], id="freebsd-64"),
        pytest.param("linux-32", ["__linux", "__unix"], id="linux-32"),
        pytest.param("linux-64", ["__linux", "__unix"], id="linux-64"),
        pytest.param("linux-aarch64", ["__linux", "__unix"], id="linux-aarch64"),
        pytest.param("linux-armv6l", ["__linux", "__unix"], id="linux-armv6l"),
        pytest.param("linux-armv7l", ["__linux", "__unix"], id="linux-armv7l"),
        pytest.param("linux-ppc64", ["__linux", "__unix"], id="linux-ppc64"),
        pytest.param("linux-ppc64le", ["__linux", "__unix"], id="linux-ppc64le"),
        pytest.param("linux-riscv64", ["__linux", "__unix"], id="linux-riscv64"),
        pytest.param("linux-s390x", ["__linux", "__unix"], id="linux-s390x"),
        pytest.param("osx-64", ["__osx", "__unix"], id="osx-64"),
        pytest.param("osx-aarch64", ["__osx", "__unix"], id="osx-aarch64"),
        pytest.param("osx-arm64", ["__osx", "__unix"], id="osx-arm64"),
        pytest.param("wasi-wasm32", [], id="wasi-wasm32"),
        pytest.param("win-32", ["__win"], id="win-32"),
        pytest.param("win-64", ["__win"], id="win-64"),
        pytest.param("win-64", ["__win"], id="win-64"),
        pytest.param("win-arm64", ["__win"], id="win-arm64"),
        pytest.param("zos-z", [], id="zos-z"),
    ],
)
def test_subdir_override(
    monkeypatch: MonkeyPatch,
    subdir: str,
    expected: list[str],
    clear_cuda_version: None,
):
    """
    Conda should create virtual packages for the appropriate platform, following
    context.subdir instead of the host operating system.
    """
    monkeypatch.setenv("CONDA_SUBDIR", subdir)
    monkeypatch.setenv("CONDA_OVERRIDE_ARCHSPEC", "")
    monkeypatch.setenv("CONDA_OVERRIDE_CUDA", "")
    monkeypatch.setenv("CONDA_OVERRIDE_GLIBC", "")
    reset_context()
    assert context.subdir == subdir
    assert {prec.name for prec in get_virtual_precs()} == {
        "__conda",  # always present
        *expected,
    }


@pytest.mark.parametrize("version,expected", [(None, False), ("bla", True)])
def test_archspec_override(
    monkeypatch: MonkeyPatch,
    version: str | None,
    expected: bool,
):
    """Conda should not produce a archspec virtual package when CONDA_OVERRIDE_ARCHSPEC=""."""
    monkeypatch.setenv("CONDA_OVERRIDE_ARCHSPEC", version or "")
    reset_context()
    assert any(prec.name == "__archspec" for prec in get_virtual_precs()) is expected


@pytest.mark.parametrize("version,expected", [(None, True), ("1.0", True)])
def test_linux_override(monkeypatch: MonkeyPatch, version: str | None, expected: bool):
    """Conda will still produce a linux virtual package when CONDA_OVERRIDE_LINUX=""."""
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    monkeypatch.setenv("CONDA_OVERRIDE_LINUX", version or "")
    reset_context()
    assert context.subdir == "linux-64"
    assert any(prec.name == "__linux" for prec in get_virtual_precs()) is expected


def test_linux_value(monkeypatch: MonkeyPatch):
    """
    In non Linux systems, conda cannot know which __linux version to offer if subdir==linux-64;
    should be 0. In Linux systems, it should match the beginning of the value reported by
    platform.release().
    """
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    reset_context()
    assert context.subdir == "linux-64"
    for prec in get_virtual_precs():
        if prec.name == "__linux":
            if on_linux:
                assert platform.release().startswith(prec.version)
            else:
                assert prec.version == "0"
            break
    else:
        raise AssertionError("Should have found __linux")


@pytest.mark.parametrize("version,expected", [(None, False), ("1.0", True)])
def test_glibc_override(monkeypatch: MonkeyPatch, version: str | None, expected: bool):
    """Conda should not produce a libc virtual package when CONDA_OVERRIDE_GLIBC=""."""
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    monkeypatch.setenv("CONDA_OVERRIDE_GLIBC", version or "")
    reset_context()
    assert context.subdir == "linux-64"
    assert any(prec.name == "__glibc" for prec in get_virtual_precs()) is expected


@pytest.mark.parametrize("version,expected", [(None, False), ("1.0", True)])
def test_osx_override(monkeypatch: MonkeyPatch, version: str | None, expected: bool):
    """Conda should not produce a osx virtual package when CONDA_OVERRIDE_OSX=""."""
    monkeypatch.setenv("CONDA_SUBDIR", "osx-64")
    monkeypatch.setenv("CONDA_OVERRIDE_OSX", version or "")
    reset_context()
    assert context.subdir == "osx-64"
    assert any(prec.name == "__osx" for prec in get_virtual_precs()) is expected


@pytest.mark.parametrize("version,expected", [(None, False), ("1.0", True)])
def test_win_override(monkeypatch: MonkeyPatch, version: str | None, expected: bool):
    """Conda should not produce a win virtual package when CONDA_OVERRIDE_WIN=""."""
    monkeypatch.setenv("CONDA_SUBDIR", "win-64")
    monkeypatch.setenv("CONDA_OVERRIDE_WIN", version or "")
    reset_context()
    assert context.subdir == "win-64"
    assert any(prec.name == "__win" for prec in get_virtual_precs()) is expected


def test_win_value(monkeypatch: MonkeyPatch):
    """
    In non Windows systems, conda cannot know which __win version to offer if subdir==win-64;
    should be 0. In Windows systems, it should be set to whatever platform.version() reports.
    """
    monkeypatch.setenv("CONDA_SUBDIR", "win-64")
    reset_context()
    assert context.subdir == "win-64"
    for prec in get_virtual_precs():
        if prec.name == "__win":
            assert prec.version == (platform.version() if on_win else "0")
            break
    else:
        raise AssertionError("Should have found __win")


def test_osx_value(monkeypatch: MonkeyPatch):
    """
    In non macOS systems, conda cannot know which __osx version to offer if subdir==osx-64;
    should be 0. In macOS systems, it should be the value reported by platform.mac_ver()[0].
    """
    monkeypatch.setenv("CONDA_SUBDIR", "osx-64")
    reset_context()
    assert context.subdir == "osx-64"
    for prec in get_virtual_precs():
        if prec.name == "__osx":
            assert prec.version == (mac_ver() if on_mac else "0")
            break
    else:
        raise AssertionError("Should have found __osx")


def test_conda_virtual_package():
    """Conda always produces a conda virtual package."""
    assert any(
        prec.name == "__conda" and prec.version == __version__
        for prec in get_virtual_precs()
    )
