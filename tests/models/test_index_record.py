# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
from unittest import TestCase

from conda.models.channel import Channel
from conda.models.index_record import PrefixRecord

log = getLogger(__name__)


class PrefixRecordTests(TestCase):

    def test_prefix_record_no_channel(self):
        pr = PrefixRecord(
            name='austin',
            version='1.2.3',
            build_string='py34_2',
            build_number=2,
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
            md5='0123456789',
            files=(),
        )
        assert pr.channel.canonical_name == 'defaults'
        assert pr.subdir == "win-32"
        assert pr.fn == "austin-1.2.3-py34_2.tar.bz2"
        assert dict(pr.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
            md5='0123456789',
            files=(),
            channel=Channel("https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2").dump(),
            subdir="win-32",
            fn="austin-1.2.3-py34_2.tar.bz2",

            auth=None,
            constrains=(),
            depends=(),
            noarch=None,
            preferred_env=None,
        )
