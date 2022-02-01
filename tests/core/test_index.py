# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from unittest import TestCase

import pytest

from conda.base.constants import DEFAULT_CHANNELS
from conda.base.context import context, Context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import iteritems, on_win, on_mac, on_linux
from conda.common.io import env_vars
from conda.core.index import check_whitelist, get_index, get_reduced_index, _supplement_index_with_system
from conda.exceptions import ChannelNotAllowed
from conda.models.channel import Channel
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from tests.core.test_subdir_data import platform_in_record

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)

def test_check_whitelist():
    whitelist = (
        'defaults',
        'conda-forge',
        'https://beta.conda.anaconda.org/conda-test'
    )
    with env_vars({'CONDA_WHITELIST_CHANNELS': ','.join(whitelist)}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with pytest.raises(ChannelNotAllowed):
            get_index(("conda-canary",))

        with pytest.raises(ChannelNotAllowed):
            get_index(("https://repo.anaconda.com/pkgs/denied",))

        check_whitelist(("defaults",))
        check_whitelist((DEFAULT_CHANNELS[0], DEFAULT_CHANNELS[1]))
        check_whitelist(("https://conda.anaconda.org/conda-forge/linux-64",))

    check_whitelist(("conda-canary",))


def test_supplement_index_with_system_cuda():
    index = {}
    with env_vars({'CONDA_OVERRIDE_CUDA': '3.2'}):
        _supplement_index_with_system(index)

    cuda_pkg = next(iter(_ for _ in index if _.name == '__cuda'))
    assert cuda_pkg.version == '3.2'
    assert cuda_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.skipif(not on_mac, reason="osx-only test")
def test_supplement_index_with_system_osx():
      index = {}
      with env_vars({'CONDA_OVERRIDE_OSX': '0.15'}):
          _supplement_index_with_system(index)

      osx_pkg = next(iter(_ for _ in index if _.name == '__osx'))
      assert osx_pkg.version == '0.15'
      assert osx_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.skipif(not on_linux, reason="linux-only test")
@pytest.mark.parametrize("release_str,version", [
        ("1.2.3.4", "1.2.3.4"), # old numbering system
        ("4.2", "4.2"),
        ("4.2.1", "4.2.1"),
        ("4.2.0-42-generic", "4.2.0"),
        ("5.4.89+", "5.4.89"),
        ("5.5-rc1", "5.5"),
        ("9.1.a", "9.1"),       # should probably be "0"
        ("9.1.a.2", "9.1"),     # should probably be "0"
        ("9.a.1", "0"),
    ])
def test_supplement_index_with_system_linux(release_str, version):
    index = {}
    with env_vars({'CONDA_OVERRIDE_LINUX': release_str}):
        _supplement_index_with_system(index)

    linux_pkg = next(iter(_ for _ in index if _.name == '__linux'))
    assert linux_pkg.version == version
    assert linux_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.skipif(on_win or on_mac, reason="linux-only test")
def test_supplement_index_with_system_glibc():
    index = {}
    with env_vars({'CONDA_OVERRIDE_GLIBC': '2.10'}):
        _supplement_index_with_system(index)

    glibc_pkg = next(iter(_ for _ in index if _.name == '__glibc'))
    assert glibc_pkg.version == '2.10'
    assert glibc_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.integration
class GetIndexIntegrationTests(TestCase):

    def test_get_index_linux64_platform(self):
        linux64 = 'linux-64'
        index = get_index(platform=linux64)
        for dist, record in iteritems(index):
            assert platform_in_record(linux64, record), (linux64, record.url)

    def test_get_index_osx64_platform(self):
        osx64 = 'osx-64'
        index = get_index(platform=osx64)
        for dist, record in iteritems(index):
            assert platform_in_record(osx64, record), (osx64, record.url)

    def test_get_index_win64_platform(self):
        win64 = 'win-64'
        index = get_index(platform=win64)
        for dist, record in iteritems(index):
            assert platform_in_record(win64, record), (win64, record.url)


@pytest.mark.integration
class ReducedIndexTests(TestCase):

    def test_basic_get_reduced_index(self):
        get_reduced_index(None, (Channel('defaults'), Channel('conda-test')), context.subdirs,
                          (MatchSpec('flask'), ), 'repodata.json')
