# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os

from conda._vendor.auxlib.ish import dals
from conda.base.context import context, reset_context
from conda.common.compat import odict
from conda.common.configuration import YamlRawParameter
from conda.common.yaml import yaml_load
from conda.models.channel import Channel
from logging import getLogger
from unittest import TestCase


log = getLogger(__name__)

platform = context.subdir


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
        anaconda_token: tk-123-456-cba
        """)
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._add_raw_data(rd)
        Channel._reset_state()

    def tearDown(self):
        reset_context()

    def test_migrated_custom_channels(self):
        assert Channel('https://some.url.somewhere/stuff/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
        assert Channel('s3://just/cant/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
        assert Channel('s3://just/cant/noarch/a-mighty-fine.tar.bz2').urls == [
            'https://some.url.somewhere/stuff/%s/' % platform,
            'https://some.url.somewhere/stuff/noarch/']

    def test_old_channel_alias(self):
        cf_urls = ["ftp://new.url:8082/conda-forge/%s/" % platform, "ftp://new.url:8082/conda-forge/noarch/"]
        assert Channel('conda-forge').urls == cf_urls

        url = "https://conda.anaconda.org/conda-forge/osx-64/some-great-package.tar.bz2"
        assert Channel(url).canonical_name == 'conda-forge'
        assert Channel(url).base_url == 'ftp://new.url:8082/conda-forge'
        assert Channel(url).urls == cf_urls
        assert Channel("https://conda.anaconda.org/conda-forge/label/dev/linux-64/"
                       "some-great-package.tar.bz2").urls == [
            "ftp://new.url:8082/conda-forge/label/dev/%s/" % platform,
            "ftp://new.url:8082/conda-forge/label/dev/noarch/"]

    def test_anaconda_token(self):
        try:
            assert context.anaconda_token == 'tk-123-456-cba'
            os.environ['CONDA_ANACONDA_TOKEN'] = 'tk-123-789-def'
            reset_context()
            assert context.anaconda_token == 'tk-123-789-def'
        finally:
            os.environ.pop('CONDA_ANACONDA_TOKEN', None)
