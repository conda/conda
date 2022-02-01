# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import join
from tempfile import gettempdir

from conda.base.constants import UNKNOWN_CHANNEL

from conda.base.context import context, conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.common.url import join_url, path_to_url
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.models.dist import Dist
from logging import getLogger
from unittest import TestCase

import pytest

log = getLogger(__name__)


@pytest.mark.parametrize("fmt", [".conda", ".tar.bz2"])
def test_dist(fmt):
    d = Dist.from_string("spyder-app-2.3.8-py27_0{}".format(fmt))
    assert d.channel == UNKNOWN_CHANNEL
    assert d.quad[0] == "spyder-app"
    assert d.quad[1] == "2.3.8"
    assert d.quad[2] == "py27_0"
    assert d.build_number == 0
    assert d.dist_name == "spyder-app-2.3.8-py27_0"
    assert d.fmt == fmt

    assert d == Dist.from_string("spyder-app-2.3.8-py27_0")
    assert d != Dist.from_string("spyder-app-2.3.8-py27_1{}".format(fmt))

    d2 = Dist("spyder-app-2.3.8-py27_0{}".format(fmt))
    assert d == d2

    d3 = Dist(d2)
    assert d3 is d2

@pytest.mark.parametrize("fmt", [".conda", ".tar.bz2"])
def test_channel(fmt):
    d = Dist.from_string("conda-forge::spyder-app-2.3.8-py27_0{}".format(fmt))
    assert d.channel == 'conda-forge'
    assert d.quad[0] == "spyder-app"
    assert d.dist_name == "spyder-app-2.3.8-py27_0"
    assert d.fmt == fmt

    d = Dist.from_string("s3://some/bucket/name::spyder-app-2.3.8-py27_0{}".format(fmt))
    assert d.channel == 's3://some/bucket/name'
    assert d.quad[0] == "spyder-app"
    assert d.dist_name == "spyder-app-2.3.8-py27_0"
    assert d.to_url() == join_url("s3://some/bucket/name", context.subdir,
                                    "spyder-app-2.3.8-py27_0{}".format(fmt))


@pytest.mark.parametrize("fmt", [".conda", ".tar.bz2"])
def test_dist_with_channel_url(fmt):
    # standard named channel
    url = "https://repo.anaconda.com/pkgs/main/win-64/spyder-app-2.3.8-py27_0{}".format(fmt)
    d = Dist(url)
    assert d.channel == 'defaults'
    assert d.name == 'spyder-app'
    assert d.version == '2.3.8'
    assert d.build_string == 'py27_0'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is True

    # standard url channel
    url = "https://not.real.continuum.io/pkgs/main/win-64/spyder-app-2.3.8-py27_0{}".format(fmt)
    d = Dist(url)
    assert d.channel == 'defaults'  # because pkgs/anaconda is in defaults
    assert d.name == 'spyder-app'
    assert d.version == '2.3.8'
    assert d.build_string == 'py27_0'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is True

    # another standard url channel
    url = "https://not.real.continuum.io/not/anaconda/win-64/spyder-app-2.3.8-py27_0{}".format(fmt)
    d = Dist(url)
    assert d.channel == 'https://not.real.continuum.io/not/anaconda'
    assert d.name == 'spyder-app'
    assert d.version == '2.3.8'
    assert d.build_string == 'py27_0'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is True

    # local file url that is a named channel
    conda_bld_path = join(gettempdir(), 'conda-bld')
    try:
        mkdir_p(conda_bld_path)
        with env_var('CONDA_BLD_PATH', conda_bld_path, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            url = path_to_url(join_url(context.croot, 'osx-64', 'bcrypt-3.1.1-py35_2{}'.format(fmt)))
            d = Dist(url)
            assert d.channel == 'local'
            assert d.name == 'bcrypt'
            assert d.version == '3.1.1'
            assert d.build_string == 'py35_2'
            assert d.fmt == fmt

            assert d.to_url() == url
            assert d.is_channel is True
    finally:
        rm_rf(conda_bld_path)

    # local file url that is not a named channel
    url = join_url('file:///some/location/on/disk', 'osx-64', 'bcrypt-3.1.1-py35_2{}'.format(fmt))
    d = Dist(url)
    assert d.channel == 'file:///some/location/on/disk'
    assert d.name == 'bcrypt'
    assert d.version == '3.1.1'
    assert d.build_string == 'py35_2'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is True



@pytest.mark.parametrize("fmt", [".conda", ".tar.bz2"])
def test_dist_with_non_channel_url(fmt):
    # contrived url
    url = "https://repo.anaconda.com/pkgs/anaconda/cffi-1.9.1-py34_0{}".format(fmt)
    d = Dist(url)
    assert d.channel == '<unknown>'
    assert d.name == 'cffi'
    assert d.version == '1.9.1'
    assert d.build_string == 'py34_0'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is False

    # file url that is not a channel
    url = path_to_url(join_url(context.croot, 'cffi-1.9.1-py34_0{}'.format(fmt)))
    d = Dist(url)
    assert d.channel == '<unknown>'
    assert d.name == 'cffi'
    assert d.version == '1.9.1'
    assert d.build_string == 'py34_0'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is False

    # file url that is a package cache
    # TODO: maybe this should look up the channel in urls.txt?  or maybe that's too coupled?
    url = join_url(path_to_url(context.pkgs_dirs[0]), 'cffi-1.9.1-py34_0{}'.format(fmt))
    d = Dist(url)
    assert d.channel == '<unknown>'
    assert d.name == 'cffi'
    assert d.version == '1.9.1'
    assert d.build_string == 'py34_0'
    assert d.fmt == fmt

    assert d.to_url() == url
    assert d.is_channel is False
