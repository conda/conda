# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import re
from typing import Iterable

import pytest
from pytest import MonkeyPatch

import conda.core.index
from conda import plugins
from conda.__version__ import __version__
from conda.base.context import context, reset_context
from conda.common.io import env_var
from conda.exceptions import PluginError
from conda.models.records import PackageRecord
from conda.plugins.types import CondaVirtualPackage
from conda.plugins.virtual_packages import cuda
from conda.testing.solver_helpers import package_dict


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
    index = conda.core.index.get_reduced_index(
        context.default_prefix,
        context.default_channels,
        context.subdirs,
        (),
        context.repodata_fns[0],
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
        PluginError, match=re.escape("Conflicting `virtual_packages` plugins found")
    ):
        conda.core.index.get_reduced_index(
            context.default_prefix,
            context.default_channels,
            context.subdirs,
            (),
            context.repodata_fns[0],
        )


def test_cuda_detection(clear_cuda_version):
    # confirm that CUDA detection doesn't raise exception
    version = cuda.cuda_version()
    assert version is None or isinstance(version, str)


def test_cuda_override(clear_cuda_version):
    with env_var("CONDA_OVERRIDE_CUDA", "4.5"):
        version = cuda.cached_cuda_version()
        assert version == "4.5"


def test_cuda_override_none(clear_cuda_version):
    with env_var("CONDA_OVERRIDE_CUDA", ""):
        version = cuda.cuda_version()
        assert version is None


def get_virtual_precs() -> Iterable[PackageRecord]:
    yield from (
        prec
        for prec in conda.core.index.get_reduced_index(
            context.default_prefix,
            context.default_channels,
            context.subdirs,
            (),
            context.repodata_fns[0],
        )
        if prec.channel.name == "@" and prec.name.startswith("__")
    )


@pytest.mark.parametrize(
    "subdir,expected",
    [
        # see conda.base.constants.KNOWN_SUBDIRS
        ("emscripten-wasm32", []),
        ("freebsd-64", ["__archspec", "__unix"]),
        ("linux-32", ["__archspec", "__linux", "__unix"]),
        ("linux-64", ["__archspec", "__linux", "__unix"]),
        ("linux-aarch64", ["__archspec", "__linux", "__unix"]),
        ("linux-armv6l", ["__archspec", "__linux", "__unix"]),
        ("linux-armv7l", ["__archspec", "__linux", "__unix"]),
        ("linux-ppc64", ["__archspec", "__linux", "__unix"]),
        ("linux-ppc64le", ["__archspec", "__linux", "__unix"]),
        ("linux-riscv64", ["__archspec", "__linux", "__unix"]),
        ("linux-s390x", ["__archspec", "__linux", "__unix"]),
        ("osx-64", ["__archspec", "__osx", "__unix"]),
        ("osx-aarch64", ["__archspec", "__osx", "__unix"]),
        ("osx-arm64", ["__archspec", "__osx", "__unix"]),
        ("wasi-wasm32", []),
        ("win-32", ["__archspec", "__win"]),
        ("win-64", ["__archspec", "__win"]),
        ("win-64", ["__archspec", "__win"]),
        ("win-arm64", ["__archspec", "__win"]),
        ("zos-z", []),
    ],
)
def test_subdir_override(monkeypatch: MonkeyPatch, subdir: str, expected: list[str]):
    """
    Conda should create virtual packages for the appropriate platform, following
    context.subdir instead of the host operating system.
    """
    monkeypatch.setenv("CONDA_SUBDIR", subdir)
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


@pytest.mark.parametrize("version,expected", [(None, False), ("1.0", True)])
def test_glibc_override(monkeypatch: MonkeyPatch, version: str | None, expected: bool):
    """Conda should not produce a libc virtual package when CONDA_OVERRIDE_GLIBC=""."""
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    monkeypatch.setenv("CONDA_OVERRIDE_GLIBC", version or "")
    reset_context()
    assert context.subdir == "linux-64"
    assert any(prec.name == "__glibc" for prec in get_virtual_precs()) == expected


@pytest.mark.parametrize("version,expected", [(None, False), ("1.0", True)])
def test_osx_override(monkeypatch: MonkeyPatch, version: str | None, expected: bool):
    """Conda should not produce a osx virtual package when CONDA_OVERRIDE_OSX=""."""
    monkeypatch.setenv("CONDA_SUBDIR", "osx-64")
    monkeypatch.setenv("CONDA_OVERRIDE_OSX", version or "")
    reset_context()
    assert context.subdir == "osx-64"
    assert any(prec.name == "__osx" for prec in get_virtual_precs()) == expected


def test_conda_virtual_package():
    """Conda always produces a conda virtual package."""
    assert any(
        prec.name == "__conda" and prec.version == __version__
        for prec in get_virtual_precs()
    )
