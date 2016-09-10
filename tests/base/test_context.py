# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda._vendor.auxlib.ish import dals
from conda.base.context import context, reset_context
from conda.common.compat import odict
from conda.common.configuration import YamlRawParameter
from conda.common.yaml import yaml_load
from conda.models.channel import Channel
from logging import getLogger
from unittest import TestCase


log = getLogger(__name__)


class ContextTests(TestCase):

    def test_old_custom_channels(self):
        string = dals("""
        custom_channels:
          darwin: https://some.url.somewhere/stuff
          chuck: http://another.url:8080/with/path
        mapped_custom_channels:
          darwin: s3://just/cant
          chuck: file:///var/lib/repo/
        old_channel_alias: https://conda.anaconda.org
        channel_alias: ftp://new.url:8082
        """)
        platform = context.subdir
        reset_context()
        rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load(string)))
        context._add_raw_data(rd)

        assert Channel('https://some.url.somewhere/stuff/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
        assert Channel('s3://just/cant/noarch/a-mighty-fine.tar.bz2').canonical_name == 'darwin'
        assert Channel('s3://just/cant/noarch/a-mighty-fine.tar.bz2').urls == [
            'https://some.url.somewhere/stuff/%s/' % platform,
            'https://some.url.somewhere/stuff/noarch/']

    def test_old_channel_alias(self):
        assert False


