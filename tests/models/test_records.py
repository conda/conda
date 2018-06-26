# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from unittest import TestCase

from conda.base.context import context
from conda.common.compat import text_type
from conda.models.channel import Channel
from conda.models.records import PackageRecord, PrefixRecord

log = getLogger(__name__)

blas_value = 'accelerate' if context.subdir == 'osx-64' else 'openblas'


def test_legacy_name_overrides_name():
    perl_graphviz_1 = {
        'arch': 'x86_64',
        'build': '1',
        'build_number': 1,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'graphviz',
            'perl-file-which',
            'perl-ipc-run',
            'perl-libwww-perl',
            'perl-parse-recdescent',
            'perl-test-pod',
            'perl-threaded',
            'perl-xml-twig',
            'perl-xml-xpath',
            'perl 5.22.0*',
        ),
        'fn': 'perl-graphviz-2.20-1.tar.bz2',
        'legacy_name': 'perl-graphviz',
        'license': 'artistic_2',
        'md5': '487fc7a046c37ba607c14761e9bdac4b',
        'name': 'graphviz',
        'namespace': 'perl',
        'platform': 'darwin',
        'size': 23230,
        'subdir': 'osx-64',
        'url': 'https://conda.anaconda.org/channel-4/osx-64/perl-graphviz-2.20-1.tar.bz2',
        'version': '2.20',
    }
    prec = PackageRecord.from_objects(perl_graphviz_1)
    assert prec.name == 'graphviz'
    assert prec.namespace == 'perl'
    assert prec.legacy_name == 'perl-graphviz'

    # 'legacy_name' is not in dump, but 'namespace' is
    assert prec.dump() == {
        'arch': 'x86_64',
        'build': '1',
        'build_number': 1,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'graphviz',
            'perl-file-which',
            'perl-ipc-run',
            'perl-libwww-perl',
            'perl-parse-recdescent',
            'perl-test-pod',
            'perl-threaded',
            'perl-xml-twig',
            'perl-xml-xpath',
            'perl 5.22.0*',
        ),
        'fn': 'perl-graphviz-2.20-1.tar.bz2',
        'license': 'artistic_2',
        'md5': '487fc7a046c37ba607c14761e9bdac4b',
        'name': 'perl-graphviz',
        'namespace': 'perl',
        'platform': 'darwin',
        'size': 23230,
        'subdir': 'osx-64',
        'url': 'https://conda.anaconda.org/channel-4/osx-64/perl-graphviz-2.20-1.tar.bz2',
        'version': '2.20',
    }

    prec2 = PackageRecord.from_objects(prec.dump())
    assert prec.dump() == prec2.dump()
    assert prec2.name == 'graphviz'
    assert prec2.namespace == 'perl'
    assert prec2.legacy_name == 'perl-graphviz'


def test_namespace_gets_pulled_from_name():
    perl_graphviz_2 = {
        'arch': 'x86_64',
        'build': '1',
        'build_number': 1,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'graphviz',
            'perl-file-which',
            'perl-ipc-run',
            'perl-libwww-perl',
            'perl-parse-recdescent',
            'perl-test-pod',
            'perl-threaded',
            'perl-xml-twig',
            'perl-xml-xpath',
            'perl 5.22.0*',
        ),
        'fn': 'perl-graphviz-2.20-1.tar.bz2',
        'license': 'artistic_2',
        'md5': '487fc7a046c37ba607c14761e9bdac4b',
        'name': 'perl-graphviz',
        'platform': 'darwin',
        'size': 23230,
        'subdir': 'osx-64',
        'url': 'https://conda.anaconda.org/channel-4/osx-64/perl-graphviz-2.20-1.tar.bz2',
        'version': '2.20',
    }
    prec = PackageRecord.from_objects(perl_graphviz_2)
    assert prec.name == 'graphviz'
    assert prec.namespace == 'perl'
    assert prec.legacy_name == 'perl-graphviz'

    # namespace gets added, but everything else is the same
    assert prec.dump() == {
        'arch': 'x86_64',
        'build': '1',
        'build_number': 1,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'graphviz',
            'perl-file-which',
            'perl-ipc-run',
            'perl-libwww-perl',
            'perl-parse-recdescent',
            'perl-test-pod',
            'perl-threaded',
            'perl-xml-twig',
            'perl-xml-xpath',
            'perl 5.22.0*',
        ),
        'fn': 'perl-graphviz-2.20-1.tar.bz2',
        'license': 'artistic_2',
        'md5': '487fc7a046c37ba607c14761e9bdac4b',
        'name': 'perl-graphviz',
        'namespace': 'perl',
        'platform': 'darwin',
        'size': 23230,
        'subdir': 'osx-64',
        'url': 'https://conda.anaconda.org/channel-4/osx-64/perl-graphviz-2.20-1.tar.bz2',
        'version': '2.20',
    }


def test_namespace_override():
    perl_graphviz_3 = {
        'arch': 'x86_64',
        'build': '1',
        'build_number': 1,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'graphviz',
            'perl-file-which',
            'perl-ipc-run',
            'perl-libwww-perl',
            'perl-parse-recdescent',
            'perl-test-pod',
            'perl-threaded',
            'perl-xml-twig',
            'perl-xml-xpath',
            'perl 5.22.0*',
        ),
        'fn': 'perl-graphviz-2.20-1.tar.bz2',
        'license': 'artistic_2',
        'md5': '487fc7a046c37ba607c14761e9bdac4b',
        'name': 'perl-graphviz',
        'namespace': 'perl',
        'platform': 'darwin',
        'size': 23230,
        'subdir': 'osx-64',
        'url': 'https://conda.anaconda.org/channel-4/osx-64/perl-graphviz-2.20-1.tar.bz2',
        'version': '2.20',
    }
    prec = PackageRecord.from_objects(perl_graphviz_3)
    assert prec.name == 'graphviz'
    assert prec.namespace == 'perl'
    assert prec.legacy_name == 'perl-graphviz'
    assert perl_graphviz_3 == prec.dump()

    # Contrived case to enforce behavior (with namespace 'python')
    perl_graphviz_4 = {
        'arch': 'x86_64',
        'build': '1',
        'build_number': 1,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'graphviz',
            'perl-file-which',
            'perl-ipc-run',
            'perl-libwww-perl',
            'perl-parse-recdescent',
            'perl-test-pod',
            'perl-threaded',
            'perl-xml-twig',
            'perl-xml-xpath',
            'perl 5.22.0*',
        ),
        'fn': 'perl-graphviz-2.20-1.tar.bz2',
        'license': 'artistic_2',
        'md5': '487fc7a046c37ba607c14761e9bdac4b',
        'name': 'perl-graphviz',
        'namespace': 'python',
        'platform': 'darwin',
        'size': 23230,
        'subdir': 'osx-64',
        'url': 'https://conda.anaconda.org/channel-4/osx-64/perl-graphviz-2.20-1.tar.bz2',
        'version': '2.20',
    }
    prec = PackageRecord.from_objects(perl_graphviz_4)
    assert prec.name == 'perl-graphviz'
    assert prec.namespace == 'python'
    assert prec.legacy_name == 'perl-graphviz'
    assert perl_graphviz_4 == prec.dump()


def test_global_namespace():
    global_graphviz_record = {
        'arch': 'x86_64',
        'build': 'h25d223c_0',
        'build_number': 0,
        'channel': 'https://conda.anaconda.org/channel-4/osx-64',
        'constrains': (),
        'depends': (
            'cairo',
            'cairo >=1.14.12,<2.0a0',
            'expat',
            'expat >=2.2.5,<3.0a0',
            'freetype',
            'freetype >=2.8,<2.9.0a0',
            'jpeg',
            'jpeg >=9b,<10a',
            'libgcc-ng >=7.2.0',
            'libpng',
            'libpng >=1.6.34,<1.7.0a0',
            'libstdcxx-ng >=7.2.0',
            'libtiff',
            'libtiff >=4.0.9,<5.0a0',
            'libtool',
            'pango',
            'pango >=1.41.0,<2.0a0',
            'zlib',
            'zlib >=1.2.11,<1.3.0a0',
        ),
        'fn': 'graphviz-2.40.1-h25d223c_0.tar.bz2',
        'license': 'EPL v1.0',
        'license_family': 'Other',
        'md5': '5895ef7dabee348bfa1bdcc3c018e2f7',
        'name': 'graphviz',
        'platform': 'darwin',
        'size': 7263943,
        'subdir': 'osx-64',
        'timestamp': 1516896801372,
        'url': 'https://conda.anaconda.org/channel-4/osx-64/graphviz-2.40.1-h25d223c_0.tar.bz2',
        'version': '2.40.1',
    }
    prec = PackageRecord.from_objects(global_graphviz_record)

    assert prec.name == 'graphviz'
    assert prec.namespace == 'global'
    assert prec.legacy_name == 'graphviz'

    global_graphviz_record['namespace'] = 'global'  # namespace gets added on dump
    assert global_graphviz_record == prec.dump()

    combined_depends = tuple(str(s) for s in prec.combined_depends)
    assert combined_depends == (
        "cairo[version='>=1.14.12,<2.0a0']",
        "expat[version='>=2.2.5,<3.0a0']",
        "freetype[version='>=2.8,<2.9.0a0']",
        "jpeg[version='>=9b,<10a']",
        "libgcc-ng[version='>=7.2.0']",
        "libpng[version='>=1.6.34,<1.7.0a0']",
        "libstdcxx-ng[version='>=7.2.0']",
        "libtiff[version='>=4.0.9,<5.0a0']",
        'libtool',
        "pango[version='>=1.41.0,<2.0a0']",
        "zlib[version='>=1.2.11,<1.3.0a0']"
    )


class PrefixRecordTests(TestCase):

    def test_prefix_record_no_channel(self):
        pr = PrefixRecord(
            name='austin',
            version='1.2.3',
            build_string='py34_2',
            build_number=2,
            url="https://repo.anaconda.com/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
            subdir="win-32",
            md5='0123456789',
            files=(),
        )
        assert pr.url == "https://repo.anaconda.com/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2"
        assert pr.channel.canonical_name == 'defaults'
        assert pr.subdir == "win-32"
        assert pr.fn == "austin-1.2.3-py34_2.tar.bz2"
        channel_str = text_type(Channel("https://repo.anaconda.com/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2"))
        assert channel_str == "https://repo.anaconda.com/pkgs/free/win-32"
        assert dict(pr.dump()) == dict(
            namespace='global',
            name='austin',
            version='1.2.3',
            build='py34_2',
            build_number=2,
            url="https://repo.anaconda.com/pkgs/free/win-32/austin-1.2.3-py34_2.tar.bz2",
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
        ts = 1507565728
        new_ts = ts * 1000
        rec = PackageRecord(
            name='test-package',
            version='1.2.3',
            build='2',
            build_number=2,
            timestamp=ts
        )
        assert rec.timestamp == new_ts
        assert rec.dump()['timestamp'] == new_ts

        ts = 1507565728999
        new_ts = ts
        rec = PackageRecord(
            name='test-package',
            version='1.2.3',
            build='2',
            build_number=2,
            timestamp=ts
        )
        assert rec.timestamp == new_ts
        assert rec.dump()['timestamp'] == new_ts
