# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re

import pytest

import conda.core.index
from conda import plugins
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_var, env_vars
from conda.exceptions import PluginError
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


def test_subdir_override():
    """
    Conda should create virtual packages for the appropriate platform, following
    context.subdir instead of the host operating system.
    """
    platform_virtual_packages = ("__win", "__linux", "__osx")
    for subdir, expected in (
        ("win-64", "__win"),
        ("linux-64", "__linux"),
        ("osx-aarch64", "__osx"),
    ):
        with env_vars(
            {
                "CONDA_SUBDIR": subdir,
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            packages = conda.core.index.get_reduced_index(
                context.default_prefix,
                context.default_channels,
                context.subdirs,
                (),
                context.repodata_fns[0],
            )
            virtual = [p for p in packages if p.channel.name == "@"]
            assert any(p.name == expected for p in virtual)
            assert not any(
                (p.name in platform_virtual_packages and p.name != expected)
                for p in virtual
            )


def test_glibc_override():
    """Conda should not produce a libc virtual package when CONDA_OVERRIDE_GLIBC=""."""
    for version in "", "1.0":
        with env_vars(
            {"CONDA_SUBDIR": "linux-64", "CONDA_OVERRIDE_GLIBC": version},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            packages = conda.core.index.get_reduced_index(
                context.default_prefix,
                context.default_channels,
                context.subdirs,
                (),
                context.repodata_fns[0],
            )
            virtual = [p for p in packages if p.channel.name == "@"]
            libc_exported = any("libc" in p.name for p in virtual)
            assert libc_exported == bool(version)


def test_osx_override():
    """Conda should not produce a osx virtual package when CONDA_OVERRIDE_OSX=""."""
    for version in "", "1.0":
        with env_vars(
            {"CONDA_SUBDIR": "osx-64", "CONDA_OVERRIDE_OSX": version},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            packages = conda.core.index.get_reduced_index(
                context.default_prefix,
                context.default_channels,
                context.subdirs,
                (),
                context.repodata_fns[0],
            )
            virtual = [p for p in packages if p.channel.name == "@"]
            osx_exported = any("osx" in p.name for p in virtual)
            assert osx_exported == bool(version)
