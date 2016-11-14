# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import basename, dirname

import os

import pytest
from conda._vendor.auxlib.ish import dals
from conda.base.context import context, reset_context
from conda.common.compat import odict
from conda.common.configuration import YamlRawParameter
from conda.common.url import path_to_url, join_url
from conda.common.yaml import yaml_load
from conda.models.channel import Channel
from conda.utils import on_win
from unittest import TestCase


class ContextTests(TestCase):

    def setUp(self):
        string = dals("""
        custom_channels:
          darwin: https://some.url.somewhere/stuff
          chuck: http://another.url:8080/with/path
        migrated_custom_channels:
          darwin: s3://just/cant
          chuck: file:///var/lib/repo/
        migrated_channel_aliases:
          - https://conda.anaconda.org
        channel_alias: ftp://new.url:8082
        conda-build:
          root-dir: /some/test/path
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._add_raw_data(rd)
        Channel._reset_state()

    def tearDown(self):
        reset_context()

    def test_migrated_custom_channels(self):
        assert Channel('https://some.url.somewhere/stuff/darwin/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
        assert Channel('s3://just/cant/darwin/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
        assert Channel('s3://just/cant/darwin/noarch/a-mighty-fine.tar.bz2').urls() == [
            'https://some.url.somewhere/stuff/darwin/noarch']

    def test_old_channel_alias(self):
        platform = context.subdir

        cf_urls = ["ftp://new.url:8082/conda-forge/%s" % platform,
                   "ftp://new.url:8082/conda-forge/noarch"]
        assert Channel('conda-forge').urls() == cf_urls

        url = "https://conda.anaconda.org/conda-forge/osx-64/some-great-package.tar.bz2"
        assert Channel(url).canonical_name == 'conda-forge'
        assert Channel(url).base_url == 'ftp://new.url:8082/conda-forge'
        assert Channel(url).urls() == [
            'ftp://new.url:8082/conda-forge/osx-64',
            'ftp://new.url:8082/conda-forge/noarch'
        ]
        assert Channel("https://conda.anaconda.org/conda-forge/label/dev/linux-64/"
                       "some-great-package.tar.bz2").urls() == [
            "ftp://new.url:8082/conda-forge/label/dev/linux-64",
            "ftp://new.url:8082/conda-forge/label/dev/noarch",
        ]

    def test_conda_envs_path(self):
        saved_envs_path = os.environ.get('CONDA_ENVS_PATH')
        beginning = "C:" + os.sep if on_win else os.sep
        path1 = beginning + os.sep.join(['my', 'envs', 'dir', '1'])
        path2 = beginning + os.sep.join(['my', 'envs', 'dir', '2'])
        try:
            os.environ['CONDA_ENVS_PATH'] = path1
            reset_context()
            assert context.envs_dirs[0] == path1

            os.environ['CONDA_ENVS_PATH'] = os.pathsep.join([path1, path2])
            reset_context()
            assert context.envs_dirs[0] == path1
            assert context.envs_dirs[1] == path2
        finally:
            if saved_envs_path:
                os.environ['CONDA_ENVS_PATH'] = saved_envs_path
            else:
                del os.environ['CONDA_ENVS_PATH']


    def test_conda_bld_path_1(self):
        saved_envs_path = os.environ.get('CONDA_BLD_PATH')
        beginning = "C:" + os.sep if on_win else os.sep
        path = beginning + os.sep.join(['tmp', 'conda-bld'])
        url = path_to_url(path)
        try:
            os.environ['CONDA_BLD_PATH'] = path
            reset_context()

            channel = Channel('local')
            assert channel.channel_name == "local"
            assert channel.channel_location is None
            assert channel.platform is None
            assert channel.package_filename is None
            assert channel.auth is None
            assert channel.token is None
            assert channel.scheme is None
            assert channel.canonical_name == "local"
            assert channel.url() is None
            assert channel.urls() == [
                join_url(url, context.subdir),
                join_url(url, 'noarch'),
            ]

            channel = Channel(url)
            assert channel.canonical_name == "local"
            assert channel.platform is None
            assert channel.package_filename is None
            assert channel.auth is None
            assert channel.token is None
            assert channel.scheme == "file"
            assert channel.urls() == [
                join_url(url, context.subdir),
                join_url(url, 'noarch'),
            ]
            assert channel.url() == join_url(url, context.subdir)
            assert channel.channel_name == basename(path)
            assert channel.channel_location == path_to_url(dirname(path)).replace('file://', '', 1)
            assert channel.canonical_name == "local"

        finally:
            if saved_envs_path:
                os.environ['CONDA_BLD_PATH'] = saved_envs_path
            else:
                del os.environ['CONDA_BLD_PATH']

    def test_conda_bld_path_2(self):
        saved_envs_path = os.environ.get('CONDA_BLD_PATH')
        beginning = "C:" + os.sep if on_win else os.sep
        path = beginning + os.sep.join(['random', 'directory'])
        url = path_to_url(path)
        try:
            os.environ['CONDA_BLD_PATH'] = path
            reset_context()

            channel = Channel('local')
            assert channel.channel_name == "local"
            assert channel.channel_location is None
            assert channel.platform is None
            assert channel.package_filename is None
            assert channel.auth is None
            assert channel.token is None
            assert channel.scheme is None
            assert channel.canonical_name == "local"
            assert channel.url() is None
            assert channel.urls() == [
                join_url(url, context.subdir),
                join_url(url, 'noarch'),
            ]

            channel = Channel(url)
            assert channel.canonical_name == "local"
            assert channel.platform is None
            assert channel.package_filename is None
            assert channel.auth is None
            assert channel.token is None
            assert channel.scheme == "file"
            assert channel.urls() == [
                join_url(url, context.subdir),
                join_url(url, 'noarch'),
            ]
            assert channel.url() == join_url(url, context.subdir)
            assert channel.channel_name == basename(path)
            assert channel.channel_location == path_to_url(dirname(path)).replace('file://', '', 1)
            assert channel.canonical_name == "local"

        finally:
            if saved_envs_path:
                os.environ['CONDA_BLD_PATH'] = saved_envs_path
            else:
                del os.environ['CONDA_BLD_PATH']

    def test_conda_build_root_dir(self):
        assert context.conda_build['root-dir'] == "/some/test/path"
