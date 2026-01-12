# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import platform
from typing import TYPE_CHECKING

import pytest
from pytest import MonkeyPatch

import conda.core.index
from conda import __version__, plugins
from conda.auxlib import NULL
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
    from pytest_mock import MockerFixture

    from conda.models.records import PackageRecord


class VirtualPackagesPlugin:
    @plugins.hookimpl
    def conda_virtual_packages(self):
        yield CondaVirtualPackage(
            name="abc",
            version="123",
            build=None,
            override_entity=None,
        )
        yield CondaVirtualPackage(
            name="def",
            version="456",
            build=None,
            override_entity=None,
        )
        yield CondaVirtualPackage(
            name="ghi",
            version="789",
            build="xyz",
            override_entity=None,
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
    assert version is NULL or isinstance(version, str)


@pytest.mark.parametrize(
    "override_value,expected, expect_pkg",
    [
        pytest.param("4.5", "4.5", True, id="override-set"),
        pytest.param("", None, False, id="override-empty"),
    ],
)
def test_cuda_override(
    clear_cuda_version,
    override_value: str,
    expected: str | None,
    expect_pkg: bool,
    monkeypatch: MonkeyPatch,
):
    monkeypatch.setenv("CONDA_OVERRIDE_CUDA", override_value)
    reset_context()

    virtual_package = CondaVirtualPackage("cuda", "4.1", None, "version")
    pkg_record = virtual_package.to_virtual_package()

    if expect_pkg:
        assert pkg_record
        assert pkg_record.version == expected
    else:
        assert pkg_record is NULL


def test_no_gpu_cuda():
    """
    __cuda should not be exposed when there's no GPU detected
    """
    if cuda.cuda_version() or os.environ.get("CONDA_OVERRIDE_CUDA"):
        pytest.skip()
    pkg = next(cuda.conda_virtual_packages())
    assert pkg.to_virtual_package() is NULL


def test_no_gpu_cuda_patched(monkeypatch):
    """
    __cuda should not be exposed when there's no GPU detected
    """
    monkeypatch.setattr(cuda, "cuda_version", lambda: NULL)
    pkg = next(cuda.conda_virtual_packages())
    assert pkg.to_virtual_package() is NULL


def get_virtual_precs() -> Iterable[PackageRecord]:
    yield from conda.core.index.Index().system_packages.values()


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


@pytest.fixture
def virtual_package_plugin(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    request,
) -> CondaVirtualPackage:
    (
        version,
        build,
        override_entity,
        override_value,
        empty_override,
        version_validation,
    ) = request.param
    if override_value is not None:
        monkeypatch.setenv("CONDA_OVERRIDE_FOO", override_value)

    deferred_version = mocker.MagicMock(return_value=version)
    deferred_build = mocker.MagicMock(return_value=build)

    plugin = CondaVirtualPackage(
        name="foo",
        version=deferred_version,
        build=deferred_build,
        override_entity=override_entity,
        empty_override=empty_override,
        version_validation=version_validation,
    )

    return plugin


@pytest.mark.parametrize(
    "virtual_package_plugin, expected_null",
    [
        pytest.param(
            (NULL, "1-abc-2", None, None, None, None),
            True,
            id="`version=NULL` returns NULL package ",
        ),
        pytest.param(
            ("1.2", NULL, None, None, None, None),
            True,
            id="`build=NULL` returns NULL package",
        ),
        pytest.param(
            ("1.2", None, "build", "", NULL, None),
            True,
            id="`empty_override=NULL` returns NULL package",
        ),
        pytest.param(
            ("1.2", None, "version", "", None, None),
            False,
            id="`empty_override=None` returns valid package",
        ),
    ],
    indirect=["virtual_package_plugin"],
)
def test_package_is_NULL(
    virtual_package_plugin: CondaVirtualPackage,
    expected_null: bool,
):
    package = virtual_package_plugin.to_virtual_package()
    if expected_null:
        assert package is NULL
    else:
        assert package is not NULL


@pytest.mark.parametrize(
    "virtual_package_plugin, expected_version, expected_build",
    [
        pytest.param(
            ("1.2", "1-abc-2", None, None, None, None),
            "1.2",
            "1-abc-2",
            id="no override",
        ),  # no override
        pytest.param(
            ("1.2", "1-abc-2", "version", "override", None, None),
            "override",
            "1-abc-2",
            id="version override",
        ),
        pytest.param(
            ("1.2", "1-abc-2", "build", "override", None, None),
            "1.2",
            "override",
            id="build override",
        ),
        pytest.param(
            ("1.2", None, "version", "", None, None),
            "0",
            "0",
            id="version override with `empty_override=None`",
        ),
        pytest.param(
            (None, "1-abc-2", "build", "", None, None),
            "0",
            "0",
            id="build override with `empty_override=None`",
        ),
    ],
    indirect=["virtual_package_plugin"],
)
def test_override_package_values(
    virtual_package_plugin: CondaVirtualPackage,
    expected_version: str,
    expected_build: str,
):
    package = virtual_package_plugin.to_virtual_package()
    assert package.name == "__foo"
    assert package.version == expected_version
    assert package.build == expected_build


@pytest.mark.parametrize(
    "virtual_package_plugin, expect_version_called, expect_build_called",
    [
        pytest.param(
            ("1.2", "1-abc-2", "version", "override", None, None),
            False,
            True,
            id="version overriden",
        ),
        pytest.param(
            ("1.2", "1-abc-2", "build", "override", None, None),
            True,
            False,
            id="build overriden",
        ),
        pytest.param(
            ("1.2", "1-abc-2", None, None, None, None),
            True,
            True,
            id="base case, no override",
        ),
    ],
    indirect=["virtual_package_plugin"],
)
def test_override_mock_calls(
    virtual_package_plugin: CondaVirtualPackage,
    expect_version_called: bool,
    expect_build_called: bool,
):
    virtual_package_plugin.to_virtual_package()
    assert virtual_package_plugin.version.call_count == expect_version_called
    assert virtual_package_plugin.build.call_count == expect_build_called


@pytest.mark.parametrize(
    "virtual_package_plugin",
    [
        pytest.param(
            ("1.2", "0", None, "", None, None),
            id="no version validation, no override",
        ),
        pytest.param(
            ("1.2", "0", None, "", None, lambda version: "valid"),
            id="version validation, no override",
        ),
        pytest.param(
            ("1.2", "0", "version", "override", None, lambda version: "valid"),
            id="version validation, override",
        ),
    ],
    indirect=["virtual_package_plugin"],
)
def test_version_validation(virtual_package_plugin: CondaVirtualPackage):
    package = virtual_package_plugin.to_virtual_package()
    version = virtual_package_plugin.version.return_value
    version_validation = virtual_package_plugin.version_validation

    assert package.name == "__foo"
    if version_validation:
        assert package.version == "valid"
    else:
        assert package.version == (version or "0")


@pytest.mark.parametrize(
    "virtual_package_plugin, expected_version",
    [
        pytest.param(
            ("1.2", "0", "version", None, None, None),
            "overriden",
            id="`CONDA_OVERRIDE_FOO` not set, but `context.override_virtual_packages` is set",
        ),
        pytest.param(
            ("1.2", "0", "version", "priority_override", None, None),
            "priority_override",
            id="Both `CONDA_OVERRIDE_FOO` gets precedence and `context.override_virtual_packages` are set",
        ),
    ],
    indirect=["virtual_package_plugin"],
)
def test_context_override(
    virtual_package_plugin: CondaVirtualPackage,
    expected_version: str,
    mocker: MockerFixture,
):
    mocker.patch(
        "conda.base.context.Context.override_virtual_packages",
        new_callable=mocker.PropertyMock,
        return_value=({"foo": "overriden"}),
    )
    package = virtual_package_plugin.to_virtual_package()
    assert package.name == "__foo"
    assert package.version == expected_version
