# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
from unittest import TestCase

from conda.base.context import context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import text_type
from conda.common.io import env_unmodified
from conda.models.channel import Channel
from conda.models.records import PackageRecord, PrefixRecord

log = getLogger(__name__)

blas_value = 'accelerate' if context.subdir == 'osx-64' else 'openblas'

class PrefixRecordTests(TestCase):

    def test_prefix_record_no_channel(self):
        with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
            pr = PrefixRecord(
                name='austin',
                version='1.2.3',
                build_string='py34_2',
                build_number=2,
                url="https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2",
                subdir="win-32",
                md5='0123456789',
                files=(),
            )
            assert pr.url == "https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2"
            assert pr.channel.canonical_name == 'defaults'
            assert pr.subdir == "win-32"
            assert pr.fn == "austin-1.2.3-py34_2.tar.bz2"
            channel_str = text_type(Channel("https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2"))
            assert channel_str == "https://repo.anaconda.com/pkgs/main/win-32"
            assert dict(pr.dump()) == dict(
                name='austin',
                version='1.2.3',
                build='py34_2',
                build_number=2,
                url="https://repo.anaconda.com/pkgs/main/win-32/austin-1.2.3-py34_2.tar.bz2",
                md5='0123456789',
                files=(),
                channel=channel_str,
                subdir="win-32",
                fn="austin-1.2.3-py34_2.tar.bz2",
                constrains=(),
                depends=(),
            )

    def test_index_record_timestamp(self):
        # regression test for #6096
        ts_secs = 1507565728
        ts_millis = ts_secs * 1000
        rec = PackageRecord(
            name='test-package',
            version='1.2.3',
            build='2',
            build_number=2,
            timestamp=ts_secs
        )
        assert rec.timestamp == ts_secs
        assert rec.dump()['timestamp'] == ts_millis

        ts_millis = 1507565728999
        ts_secs = ts_millis / 1000
        rec = PackageRecord(
            name='test-package',
            version='1.2.3',
            build='2',
            build_number=2,
            timestamp=ts_secs
        )
        assert rec.timestamp == ts_secs
        assert rec.dump()['timestamp'] == ts_millis
