# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
from unittest import TestCase

from conda.common.compat import text_type
from conda.models.channel import Channel
from conda.models.index_record import IndexJsonRecord
from conda.models.prefix_record import PrefixRecord

log = getLogger(__name__)


class PrefixRecordTests(TestCase):

    def test_prefix_record_no_channel(self):
        pr = PrefixRecord(
            name='austin',
            version='1.2.3',
            build_string='py34_2',
            build_number=2,
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
            subdir="win-32",
            md5='0123456789',
            files=(),
        )
        assert pr.url == "https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2"
        assert pr.channel.canonical_name == 'defaults'
        assert pr.subdir == "win-32"
        assert pr.fn == "austin-1.2.3-py34_2.tar.bz2"
        channel_str = text_type(Channel("https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2"))
        assert channel_str == "https://repo.continuum.io/pkgs/free"
        assert dict(pr.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
            md5='0123456789',
            files=(),
            channel=channel_str,
            subdir="win-32",
            fn="austin-1.2.3-py34_2.tar.bz2",
            constrains=(),
            depends=(),
        )

    def test_provides_features(self):
        base = IndexJsonRecord(
            name='austin',
            version='1.2.3',
            build_string='py34_2',
            build_number=2,
            subdir="win-32",
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
        )
        assert base.track_features == ()
        assert base.provides_features == {}
        assert dict(base.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            subdir="win-32",
            depends=(),
            constrains=(),
        )

        rec = IndexJsonRecord.from_objects(base, track_features='debug nomkl')
        assert rec.track_features == ('debug', 'nomkl')
        assert rec.provides_features == {'debug': 'true', 'blas': 'nomkl'}
        assert dict(rec.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            subdir="win-32",
            depends=(),
            constrains=(),
            track_features='debug nomkl',
            provides_features={'debug': 'true', 'blas': 'nomkl'},
        )

        rec = IndexJsonRecord.from_objects(base, track_features='debug nomkl',
                                           provides_features={'blas': 'openblas'})
        assert rec.track_features == ('debug', 'nomkl')
        assert rec.provides_features == {'blas': 'openblas'}
        assert dict(rec.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            subdir="win-32",
            depends=(),
            constrains=(),
            track_features='debug nomkl',
            provides_features={'blas': 'openblas'},
        )

        rec = IndexJsonRecord.from_objects(base, provides_features={'blas': 'openblas'})
        assert rec.track_features == ()
        assert rec.provides_features == {'blas': 'openblas'}
        assert dict(rec.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            subdir="win-32",
            depends=(),
            constrains=(),
            provides_features={'blas': 'openblas'},
        )

        base = IndexJsonRecord(
            name='python',
            version='1.2.3',
            build_string='2',
            build_number=2,
            subdir="win-32",
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
        )
        assert base.track_features == ()
        assert base.provides_features == {'python': '1.2'}


    def test_requires_features(self):
        rec = IndexJsonRecord(
            name='austin',
            version='1.2.3',
            build_string='py34_2',
            build_number=2,
            subdir="win-32",
            url="https://repo.continuum.io/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
            features='debug nomkl',
            depends=('python 2.7.*', 'numpy 1.11*'),
        )

        assert rec.features == ('debug', 'nomkl')
        assert rec.requires_features == {'debug': 'true', 'blas': 'nomkl',
                                         'python': '2.7', 'numpy': '1.11'}
        assert dict(rec.dump()) == dict(
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            subdir="win-32",
            depends=('python 2.7.*', 'numpy 1.11*'),
            constrains=(),
            features='debug nomkl',
            requires_features={'debug': 'true', 'blas': 'nomkl', 'python': '2.7', 'numpy': '1.11'},
        )

