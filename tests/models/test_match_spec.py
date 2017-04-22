from __future__ import absolute_import, print_function

import re
import unittest

from conda.models.dist import Dist
from conda.models.index_record import IndexRecord
from conda.models.match_spec import MatchSpec


def DPkg(s):
    d = Dist(s)
    return IndexRecord(
        fn=d.to_filename(),
        name=d.name,
        version=d.version,
        build=d.build_string,
        build_number=int(d.build_string.rsplit('_', 1)[-1]),
        schannel=d.channel)


class MatchSpecTests(unittest.TestCase):

    def test_match(self):
        for spec, result in [
            ('numpy 1.7*', True),          ('numpy 1.7.1', True),
            ('numpy 1.7', False),          ('numpy 1.5*', False),
            ('numpy >=1.5', True),         ('numpy >=1.5,<2', True),
            ('numpy >=1.8,<1.9', False),   ('numpy >1.5,<2,!=1.7.1', False),
            ('numpy >1.8,<2|==1.7', False),('numpy >1.8,<2|>=1.7.1', True),
            ('numpy >=1.8|1.7*', True),    ('numpy ==1.7', False),
            ('numpy >=1.5,>1.6', True),    ('numpy ==1.7.1', True),
            ('numpy >=1,*.7.*', True),     ('numpy *.7.*,>=1', True),
            ('numpy >=1,*.8.*', False),    ('numpy >=2,*.7.*', False),
            ('numpy 1.6*|1.7*', True),     ('numpy 1.6*|1.8*', False),
            ('numpy 1.6.2|1.7*', True),    ('numpy 1.6.2|1.7.1', True),
            ('numpy 1.6.2|1.7.0', False),  ('numpy 1.7.1 py27_0', True),
            ('numpy 1.7.1 py26_0', False), ('numpy >1.7.1a', True),
            ('python', False),
        ]:
            m = MatchSpec(spec)
            assert m.match(DPkg('numpy-1.7.1-py27_0.tar.bz2')) == result

        # both version numbers conforming to PEP 440
        assert not MatchSpec('numpy >=1.0.1').match(DPkg('numpy-1.0.1a-0.tar.bz2'))
        # both version numbers non-conforming to PEP 440
        assert not MatchSpec('numpy >=1.0.1.vc11').match(DPkg('numpy-1.0.1a.vc11-0.tar.bz2'))
        assert MatchSpec('numpy >=1.0.1*.vc11').match(DPkg('numpy-1.0.1a.vc11-0.tar.bz2'))
        # one conforming, other non-conforming to PEP 440
        assert MatchSpec('numpy <1.0.1').match(DPkg('numpy-1.0.1.vc11-0.tar.bz2'))
        assert MatchSpec('numpy <1.0.1').match(DPkg('numpy-1.0.1a.vc11-0.tar.bz2'))
        assert not MatchSpec('numpy >=1.0.1.vc11').match(DPkg('numpy-1.0.1a-0.tar.bz2'))
        assert MatchSpec('numpy >=1.0.1a').match(DPkg('numpy-1.0.1z-0.tar.bz2'))
        assert MatchSpec('numpy >=1.0.1a py27*').match(DPkg('numpy-1.0.1z-py27_1.tar.bz2'))
        assert MatchSpec('blas * openblas_0').match(DPkg('blas-1.0-openblas_0.tar.bz2'))

        assert MatchSpec('blas').is_simple()
        assert not MatchSpec('blas').is_exact()
        assert not MatchSpec('blas 1.0').is_simple()
        assert not MatchSpec('blas 1.0').is_exact()
        assert not MatchSpec('blas 1.0 1').is_simple()
        assert not MatchSpec('blas 1.0 1').is_exact()
        assert not MatchSpec('blas 1.0 *').is_exact()
        assert MatchSpec(Dist('blas-1.0-openblas_0.tar.bz2')).is_exact()
        assert MatchSpec(fn='blas-1.0-openblas_0.tar.bz2', schannel='defaults').is_exact()

        m = MatchSpec('blas 1.0', optional=True)
        m2 = MatchSpec(m, optional=False)
        m3 = MatchSpec(m2, target='blas-1.0-0.tar.bz2')
        m4 = MatchSpec(m3, target=None, optional=True)
        assert m.spec == m2.spec and m.optional != m2.optional
        assert m2.spec == m3.spec and m2.optional == m3.optional and m2.target != m3.target
        assert m == m4

        self.assertRaises(ValueError, MatchSpec, (1, 2, 3))

    def test_to_filename(self):
        m1 = MatchSpec(fn='foo-1.7-52.tar.bz2')
        m2 = MatchSpec(name='foo', version='1.7', build='52')
        m3 = MatchSpec(Dist('defaults::foo-1.7-52'))
        assert m1.to_filename() == 'foo-1.7-52.tar.bz2'
        assert m2.to_filename() == 'foo-1.7-52.tar.bz2'
        assert m3.to_filename() == 'foo-1.7-52.tar.bz2'

        for spec in 'bitarray', 'pycosat 0.6.0', 'numpy 1.6*':
            ms = MatchSpec(spec)
            assert ms.to_filename() is None

    def test_normalize(self):
        a = MatchSpec('numpy 1.7')
        b = MatchSpec('numpy 1.7', normalize=True)
        c = MatchSpec('numpy 1.7*')
        assert a != b
        assert b == c
        a = MatchSpec('numpy 1.7 1')
        b = MatchSpec('numpy 1.7 1', normalize=True)
        assert a == b

    def test_hash(self):
        a = MatchSpec('numpy 1.7*')
        b = MatchSpec('numpy 1.7*')
        c = MatchSpec(name='numpy', version='1.7*')
        # optional should not change the hash
        d = MatchSpec(c, optional=True)
        assert d.optional
        assert not c.optional
        assert a is not b
        assert a is not c
        assert a is not d
        assert a == b
        assert a == c
        assert a != d
        assert hash(a) == hash(b)
        assert hash(a) == hash(c)
        assert hash(a) == hash(d)
        c = MatchSpec('python')
        d = MatchSpec('python 2.7.4')
        e = MatchSpec('python', version='2.7.4')
        f = MatchSpec('* 2.7.4', name='python')
        assert d == e
        assert d == f
        assert a != c
        assert hash(a) != hash(c)
        assert c != d
        assert hash(c) != hash(d)

    def test_string(self):
        a = MatchSpec("foo1 >=1.3 2 (optional,target=burg,)")
        b = MatchSpec('* (name="foo1", version=">=1.3", build="2", optional, target=burg)')
        assert a.optional and a.target == 'burg'
        assert a == b
        c = MatchSpec("^foo1$ >=1.3 2 ")
        d = MatchSpec("* >=1.3 2", name=re.compile(u'^foo1$'))
        e = MatchSpec("* >=1.3 2", name='^foo1$')
        assert c == d
        assert c == e
        # build_number is not the same as build!
        f = MatchSpec('foo1 >=1.3 (optional,target=burg)', build_number=2)
        g = MatchSpec('foo1 >=1.3 (optional,target=burg,build_number=2)')
        assert a != f
        assert f == g
        assert a._to_string() == "foo1 >=1.3 2 (optional,target=burg)"
        assert g._to_string() == "foo1 >=1.3 (build_number=2,optional,target=burg)"
        self.assertRaises(ValueError, MatchSpec, 'blas (optional')
        self.assertRaises(ValueError, MatchSpec, 'blas (optional,test=)')
        self.assertRaises(ValueError, MatchSpec, 'blas (optional,invalid="1")')

    def test_dict(self):
        dst = Dist('defaults::foo-1.2.3-4.tar.bz2')
        a = MatchSpec(dst, optional=True, target='burg')
        b = MatchSpec(a.to_dict())
        c = MatchSpec(**a.to_dict())
        d = MatchSpec(a.to_dict(), build='5')
        e = MatchSpec(a.to_dict(args=False))
        assert a == b
        assert a == c
        assert a != d
        assert a != e
        assert hash(a) == hash(e)

    def test_index_record(self):
        dst = Dist('defaults::foo-1.2.3-4.tar.bz2')
        rec = DPkg(dst)
        a = MatchSpec(dst)
        b = MatchSpec(rec)
        assert b.match(rec)
        assert a.match(rec)

    def test_strictness(self):
        assert MatchSpec('foo').strictness == 1
        assert MatchSpec('foo 1.2').strictness == 2
        assert MatchSpec('foo 1.2 3').strictness == 3
        assert MatchSpec('foo 1.2 3 (optional,target=burg)').strictness == 3
        # Seems odd, but this is needed for compatibility
        assert MatchSpec('test* 1.2').strictness == 3
        assert MatchSpec('foo', build_number=2).strictness == 3

    def test_build_number_and_filename(self):
        ms = MatchSpec('zlib 1.2.7 0')
        assert ms.exact_field('name') == 'zlib'
        assert ms.exact_field('version') == '1.2.7'
        assert ms.exact_field('build') == '0'
        assert ms.to_filename() == 'zlib-1.2.7-0.tar.bz2'

