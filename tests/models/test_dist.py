# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import join
from tempfile import gettempdir

from conda.base.context import context, reset_context
from conda.common.io import env_var
from conda.common.url import join_url, path_to_url
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.models.dist import Dist
from logging import getLogger
from unittest import TestCase

log = getLogger(__name__)


class DistTests(TestCase):

    def test_dist(self):
        d = Dist.from_string("spyder-app-2.3.8-py27_0.tar.bz2")
        assert d.channel == 'defaults'
        assert d.quad[0] == "spyder-app"
        assert d.quad[1] == "2.3.8"
        assert d.quad[2] == "py27_0"
        assert d.build_number == 0
        assert d.dist_name == "spyder-app-2.3.8-py27_0"

        assert d == Dist.from_string("spyder-app-2.3.8-py27_0")
        assert d != Dist.from_string("spyder-app-2.3.8-py27_1.tar.bz2")

        d2 = Dist("spyder-app-2.3.8-py27_0.tar.bz2")
        assert d == d2

        d3 = Dist(d2)
        assert d3 is d2

    def test_with_feature_depends(self):
        d = Dist.from_string("spyder-app-2.3.8-py27_0[mkl]")
        assert d.with_features_depends == "mkl"

        d = Dist("mkl@")
        assert d.channel == "@"
        assert d.quad[0] == "mkl@"
        assert d.quad[1] == ""
        assert d.quad[2] == ""
        assert d.with_features_depends is None
        assert d.is_feature_package

    def test_channel(self):
        d = Dist.from_string("conda-forge::spyder-app-2.3.8-py27_0.tar.bz2")
        assert d.channel == 'conda-forge'
        assert d.quad[0] == "spyder-app"
        assert d.dist_name == "spyder-app-2.3.8-py27_0"

        d = Dist.from_string("s3://some/bucket/name::spyder-app-2.3.8-py27_0.tar.bz2")
        assert d.channel == 's3://some/bucket/name'
        assert d.quad[0] == "spyder-app"
        assert d.dist_name == "spyder-app-2.3.8-py27_0"
        assert d.to_url() == join_url("s3://some/bucket/name", context.subdir,
                                      "spyder-app-2.3.8-py27_0.tar.bz2")


class UrlDistTests(TestCase):

    def test_dist_with_channel_url(self):
        # standard named channel
        url = "https://repo.continuum.io/pkgs/anaconda/win-64/spyder-app-2.3.8-py27_0.tar.bz2"
        d = Dist(url)
        assert d.channel == 'defaults'
        assert d.name == 'spyder-app'
        assert d.version == '2.3.8'
        assert d.build_string == 'py27_0'

        assert d.to_url() == url
        assert d.is_channel is True

        # standard url channel
        url = "https://not.real.continuum.io/pkgs/anaconda/win-64/spyder-app-2.3.8-py27_0.tar.bz2"
        d = Dist(url)
        assert d.channel == 'defaults'  # because pkgs/anaconda is in defaults
        assert d.name == 'spyder-app'
        assert d.version == '2.3.8'
        assert d.build_string == 'py27_0'

        assert d.to_url() == url
        assert d.is_channel is True

        # another standard url channel
        url = "https://not.real.continuum.io/not/anaconda/win-64/spyder-app-2.3.8-py27_0.tar.bz2"
        d = Dist(url)
        assert d.channel == 'https://not.real.continuum.io/not/anaconda'
        assert d.name == 'spyder-app'
        assert d.version == '2.3.8'
        assert d.build_string == 'py27_0'

        assert d.to_url() == url
        assert d.is_channel is True

        # local file url that is a named channel
        conda_bld_path = join(gettempdir(), 'conda-bld')
        try:
            mkdir_p(conda_bld_path)
            with env_var('CONDA_BLD_PATH', conda_bld_path, reset_context):
                url = path_to_url(join_url(context.croot, 'osx-64', 'bcrypt-3.1.1-py35_2.tar.bz2'))
                d = Dist(url)
                assert d.channel == 'local'
                assert d.name == 'bcrypt'
                assert d.version == '3.1.1'
                assert d.build_string == 'py35_2'

                assert d.to_url() == url
                assert d.is_channel is True
        finally:
            rm_rf(conda_bld_path)

        # local file url that is not a named channel
        url = join_url('file:///some/location/on/disk', 'osx-64', 'bcrypt-3.1.1-py35_2.tar.bz2')
        d = Dist(url)
        assert d.channel == 'file:///some/location/on/disk'
        assert d.name == 'bcrypt'
        assert d.version == '3.1.1'
        assert d.build_string == 'py35_2'

        assert d.to_url() == url
        assert d.is_channel is True



    def test_dist_with_non_channel_url(self):
        # contrived url
        url = "https://repo.continuum.io/pkgs/anaconda/cffi-1.9.1-py34_0.tar.bz2"
        d = Dist(url)
        assert d.channel == '<unknown>'
        assert d.name == 'cffi'
        assert d.version == '1.9.1'
        assert d.build_string == 'py34_0'

        assert d.to_url() == url
        assert d.is_channel is False

        # file url that is not a channel
        url = path_to_url(join_url(context.croot, 'cffi-1.9.1-py34_0.tar.bz2'))
        d = Dist(url)
        assert d.channel == '<unknown>'
        assert d.name == 'cffi'
        assert d.version == '1.9.1'
        assert d.build_string == 'py34_0'

        assert d.to_url() == url
        assert d.is_channel is False

        # file url that is a package cache
        # TODO: maybe this should look up the channel in urls.txt?  or maybe that's too coupled?
        url = join_url(path_to_url(context.pkgs_dirs[0]), 'cffi-1.9.1-py34_0.tar.bz2')
        d = Dist(url)
        assert d.channel == '<unknown>'
        assert d.name == 'cffi'
        assert d.version == '1.9.1'
        assert d.build_string == 'py34_0'

        assert d.to_url() == url
        assert d.is_channel is False
