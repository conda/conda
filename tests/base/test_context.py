# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest
from conda._vendor.auxlib.ish import dals
from conda.base.context import context, reset_context
from conda.common.compat import odict
from conda.common.configuration import YamlRawParameter
from conda.common.yaml import yaml_load
from conda.models.channel import Channel
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
