# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
import os
from os.path import join, abspath
from tempfile import gettempdir
from unittest import TestCase, mock

import pytest

from conda.auxlib.collection import AttrDict
from conda.auxlib.ish import dals
from conda._vendor.toolz.itertoolz import concat
from conda.base.constants import PathConflict, ChannelPriority
from conda.base.context import context, reset_context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import odict, iteritems
from conda.common.configuration import ValidationError, YamlRawParameter
from conda.common.io import env_var, env_vars
from conda.common.path import expand, win_path_backout
from conda.common.url import join_url, path_to_url
from conda.common.serialize import yaml_round_trip_load
from conda.core.package_cache_data import PackageCacheData
from conda.gateways.disk.create import mkdir_p, create_package_cache_directory
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.permissions import make_read_only
from conda.gateways.disk.update import touch
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.utils import on_win

from conda.testing.helpers import tempdir


class ContextCustomRcTests(TestCase):

    def setUp(self):
        string = dals("""
        custom_channels:
          darwin: https://some.url.somewhere/stuff
          chuck: http://another.url:8080/with/path
        custom_multichannels:
          michele:
            - https://do.it.with/passion
            - learn_from_every_thing
          steve:
            - more-downloads
        migrated_custom_channels:
          darwin: s3://just/cant
          chuck: file:///var/lib/repo/
        migrated_channel_aliases:
          - https://conda.anaconda.org
        channel_alias: ftp://new.url:8082
        conda-build:
          root-dir: /some/test/path
        proxy_servers:
          http: http://user:pass@corp.com:8080
          https: none
          ftp:
          sftp: ''
          ftps: false
          rsync: 'false'
        aggressive_update_packages: []
        channel_priority: false
        """)
        reset_context(())
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)

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

    def test_signing_metadata_url_base(self):
        SIGNING_URL_BASE = "https://conda.example.com/pkgs"
        string = f"signing_metadata_url_base: {SIGNING_URL_BASE}"
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        assert context.signing_metadata_url_base == SIGNING_URL_BASE

    def test_signing_metadata_url_base_empty_default_channels(self):
        string = dals("""
        default_channels: []
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        assert len(context.default_channels) is 0
        assert context.signing_metadata_url_base is None


    def test_client_ssl_cert(self):
        string = dals("""
        client_ssl_cert_key: /some/key/path
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        pytest.raises(ValidationError, context.validate_configuration)

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

    def test_conda_bld_path(self):
        conda_bld_path = join(gettempdir(), 'conda-bld')
        conda_bld_url = path_to_url(conda_bld_path)
        try:
            mkdir_p(conda_bld_path)
            with env_var('CONDA_BLD_PATH', conda_bld_path, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                assert len(context.conda_build_local_paths) >= 1
                assert context.conda_build_local_paths[0] == conda_bld_path

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
                urls = list(concat((
                               join_url(url, context.subdir),
                               join_url(url, 'noarch'),
                           ) for url in context.conda_build_local_urls))
                assert channel.urls() == urls

                channel = Channel(conda_bld_url)
                assert channel.canonical_name == "local"
                assert channel.platform is None
                assert channel.package_filename is None
                assert channel.auth is None
                assert channel.token is None
                assert channel.scheme == "file"
                assert channel.urls() == [
                    join_url(conda_bld_url, context.subdir),
                    join_url(conda_bld_url, 'noarch'),
                ]
                assert channel.url() == join_url(conda_bld_url, context.subdir)
                assert channel.channel_name.lower() == win_path_backout(conda_bld_path).lstrip('/').lower()
                assert channel.channel_location == ''  # location really is an empty string; all path information is in channel_name
                assert channel.canonical_name == "local"
        finally:
            rm_rf(conda_bld_path)

    def test_custom_multichannels(self):
        assert context.custom_multichannels['michele'] == (
            Channel('passion'),
            Channel('learn_from_every_thing'),
        )

    def test_restore_free_channel(self):
        assert 'https://repo.anaconda.com/pkgs/free' not in context.default_channels
        with env_var("CONDA_RESTORE_FREE_CHANNEL", 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert  context.default_channels.index('https://repo.anaconda.com/pkgs/free') == 1

    def test_proxy_servers(self):
        assert context.proxy_servers['http'] == 'http://user:pass@corp.com:8080'
        assert context.proxy_servers['https'] is None
        assert context.proxy_servers['ftp'] is None
        assert context.proxy_servers['sftp'] == ''
        assert context.proxy_servers['ftps'] == 'False'
        assert context.proxy_servers['rsync'] == 'false'

    def test_conda_build_root_dir(self):
        assert context.conda_build['root-dir'] == "/some/test/path"

    def test_clobber_enum(self):
        with env_var("CONDA_PATH_CONFLICT", 'prevent', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.path_conflict == PathConflict.prevent

    def test_context_parameter_map(self):
        all_parameter_names = context.list_parameters()
        all_mapped_parameter_names = tuple(chain.from_iterable(context.category_map.values()))

        unmapped_parameter_names = set(all_parameter_names) - set(all_mapped_parameter_names)
        assert not unmapped_parameter_names, unmapped_parameter_names

        assert len(all_parameter_names) == len(all_mapped_parameter_names)

    def test_context_parameters_have_descriptions(self):
        skip_categories = ('CLI-only', 'Hidden and Undocumented')
        documented_parameter_names = chain.from_iterable((
            parameter_names for category, parameter_names in iteritems(context.category_map)
            if category not in skip_categories
        ))

        from pprint import pprint
        for name in documented_parameter_names:
            description = context.get_descriptions()[name]
            pprint(context.describe_parameter(name))

    def test_local_build_root_custom_rc(self):
        assert context.local_build_root == abspath("/some/test/path")

        test_path_1 = join(os.getcwd(), 'test_path_1')
        with env_var("CONDA_CROOT", test_path_1, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.local_build_root == test_path_1

        test_path_2 = join(os.getcwd(), 'test_path_2')
        with env_var("CONDA_BLD_PATH", test_path_2, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.local_build_root == test_path_2

    def test_default_target_is_root_prefix(self):
        assert context.target_prefix == context.root_prefix

    def test_target_prefix(self):
        with tempdir() as prefix:
            mkdir_p(join(prefix, 'first', 'envs'))
            mkdir_p(join(prefix, 'second', 'envs'))
            create_package_cache_directory(join(prefix, 'first', 'pkgs'))
            create_package_cache_directory(join(prefix, 'second', 'pkgs'))
            envs_dirs = (join(prefix, 'first', 'envs'), join(prefix, 'second', 'envs'))
            with env_var('CONDA_ENVS_DIRS', os.pathsep.join(envs_dirs), stack_callback=conda_tests_ctxt_mgmt_def_pol):

                # with both dirs writable, choose first
                reset_context((), argparse_args=AttrDict(name='blarg', func='create'))
                assert context.target_prefix == join(envs_dirs[0], 'blarg')

                # with first dir read-only, choose second
                PackageCacheData._cache_.clear()
                make_read_only(join(envs_dirs[0], '.conda_envs_dir_test'))
                reset_context((), argparse_args=AttrDict(name='blarg', func='create'))
                assert context.target_prefix == join(envs_dirs[1], 'blarg')

                # if first dir is read-only but environment exists, choose first
                PackageCacheData._cache_.clear()
                mkdir_p(join(envs_dirs[0], 'blarg'))
                touch(join(envs_dirs[0], 'blarg', 'history'))
                reset_context((), argparse_args=AttrDict(name='blarg', func='create'))
                assert context.target_prefix == join(envs_dirs[0], 'blarg')

    def test_aggressive_update_packages(self):
        assert context.aggressive_update_packages == tuple()
        specs = ['certifi', 'openssl>=1.1']
        with env_var('CONDA_AGGRESSIVE_UPDATE_PACKAGES', ','.join(specs), stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.aggressive_update_packages == tuple(MatchSpec(s) for s in specs)

    def test_channel_priority(self):
        assert context.channel_priority == ChannelPriority.DISABLED

    def test_cuda_detection(self):
        # confirm that CUDA detection doesn't raise exception
        version = context.cuda_version
        assert version is None or isinstance(version, str)

    def test_cuda_override(self):
        with env_var('CONDA_OVERRIDE_CUDA', '4.5'):
            version = context.cuda_version
            assert version == '4.5'

    def test_cuda_override_none(self):
        with env_var('CONDA_OVERRIDE_CUDA', ''):
            version = context.cuda_version
            assert version is None

    def test_threads(self):
        default_value = None
        assert context.default_threads == default_value
        assert context.repodata_threads == default_value
        assert context.verify_threads == 1
        assert context.execute_threads == 1

        with env_var('CONDA_DEFAULT_THREADS', '3',
                     stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.default_threads == 3
            assert context.verify_threads == 3
            assert context.repodata_threads == 3
            assert context.execute_threads == 3

        with env_var('CONDA_VERIFY_THREADS', '3',
                     stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.default_threads == default_value
            assert context.verify_threads == 3
            assert context.repodata_threads == default_value
            assert context.execute_threads == 1

        with env_var('CONDA_REPODATA_THREADS', '3',
                     stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.default_threads == default_value
            assert context.verify_threads == 1
            assert context.repodata_threads == 3
            assert context.execute_threads == 1

        with env_var('CONDA_EXECUTE_THREADS', '3',
                     stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.default_threads == default_value
            assert context.verify_threads == 1
            assert context.repodata_threads == default_value
            assert context.execute_threads == 3

        with env_vars({'CONDA_EXECUTE_THREADS': '3',
                       'CONDA_DEFAULT_THREADS': '1'},
                      stack_callback=conda_tests_ctxt_mgmt_def_pol):

            assert context.default_threads == 1
            assert context.verify_threads == 1
            assert context.repodata_threads == 1
            assert context.execute_threads == 3

    def test_channels_defaults(self):
        """
        Test when no channels provided in cli
        """
        reset_context(())
        assert context.channels == ('defaults',)

    def test_channels_defaults_condarc(self):
        """
        Test when no channels provided in cli, but some in condarc
        """
        reset_context(())
        string = dals("""
        channels: ['defaults', 'conda-forge']
        """)
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        assert context.channels == ('defaults', 'conda-forge')

    def test_specify_channels_cli_adding_defaults_no_condarc(self):
        """
        When the channel haven't been specified in condarc, 'defaults'
        should be present when specifying channel in the cli
        """
        reset_context((), argparse_args=AttrDict(channel=['conda-forge']))
        assert context.channels == ('conda-forge', 'defaults')

    def test_specify_channels_cli_condarc(self):
        """
        When the channel have been specified in condarc, these channels
        should be used along with the one specified
        """
        reset_context((), argparse_args=AttrDict(channel=['conda-forge']))
        string = dals("""
        channels: ['defaults', 'conda-forge']
        """)
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        assert context.channels == ('defaults', 'conda-forge')

    def test_specify_different_channels_cli_condarc(self):
        """
        When the channel have been specified in condarc, these channels
        should be used along with the one specified
        In this test, the given channel in cli is different from condarc
        'defaults' should not be added
        """
        reset_context((), argparse_args=AttrDict(channel=['other']))
        string = dals("""
        channels: ['conda-forge']
        """)
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        assert context.channels == ('conda-forge', 'other')

    def test_specify_same_channels_cli_as_in_condarc(self):
        """
        When the channel have been specified in condarc, these channels
        should be used along with the one specified

        In this test, the given channel in cli is the same as in condarc
        'defaults' should not be added
        See https://github.com/conda/conda/issues/10732
        """
        reset_context((), argparse_args=AttrDict(channel=['conda-forge']))
        string = dals("""
        channels: ['conda-forge']
        """)
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
        context._set_raw_data(rd)
        assert context.channels == ('conda-forge',)

    def test_expandvars(self):
        """
        Environment variables should be expanded in settings that have expandvars=True.
        """
        def _get_expandvars_context(attr, config_expr, env_value):
            with mock.patch.dict(os.environ, {"TEST_VAR": env_value}):
                reset_context(())
                string = f"{attr}: {config_expr}"
                rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_round_trip_load(string)))
                context._set_raw_data(rd)
                return getattr(context, attr)

        ssl_verify = _get_expandvars_context("ssl_verify", "${TEST_VAR}", "yes")
        assert ssl_verify

        for attr, env_value in [
            ("client_ssl_cert", "foo"),
            ("client_ssl_cert_key", "foo"),
            ("channel_alias", "http://foo"),
        ]:
            value = _get_expandvars_context(attr, "${TEST_VAR}", env_value)
            assert value == env_value

        for attr in [
            "migrated_custom_channels",
            "proxy_servers",
        ]:
            value = _get_expandvars_context("proxy_servers", "{'x': '${TEST_VAR}'}", "foo")
            assert value == {"x": "foo"}

        for attr in [
            "channels",
            "default_channels",
            "whitelist_channels",
        ]:
            value = _get_expandvars_context(attr, "['${TEST_VAR}']", "foo")
            assert value == ("foo",)

        custom_channels = _get_expandvars_context("custom_channels", "{'x': '${TEST_VAR}'}", "http://foo")
        assert custom_channels["x"].location == "foo"

        custom_multichannels = _get_expandvars_context("custom_multichannels", "{'x': ['${TEST_VAR}']}", "http://foo")
        assert len(custom_multichannels["x"]) == 1
        assert custom_multichannels["x"][0].location == "foo"

        envs_dirs = _get_expandvars_context("envs_dirs", "['${TEST_VAR}']", "/foo")
        assert any("foo" in d for d in envs_dirs)

        pkgs_dirs = _get_expandvars_context("pkgs_dirs", "['${TEST_VAR}']", "/foo")
        assert any("foo" in d for d in pkgs_dirs)


class ContextDefaultRcTests(TestCase):

    def test_subdirs(self):
        assert context.subdirs == (context.subdir, 'noarch')

        subdirs = ('linux-highest', 'linux-64', 'noarch')
        with env_var('CONDA_SUBDIRS', ','.join(subdirs), stack_callback=conda_tests_ctxt_mgmt_def_pol):
            assert context.subdirs == subdirs

    def test_local_build_root_default_rc(self):
        if context.root_writable:
            assert context.local_build_root == join(context.root_prefix, 'conda-bld')
        else:
            assert context.local_build_root == expand('~/conda-bld')
