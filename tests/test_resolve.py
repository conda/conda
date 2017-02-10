from __future__ import absolute_import, print_function

import json
import os
import unittest
from conda.base.constants import MAX_CHANNEL_PRIORITY
from conda.base.context import reset_context
from conda.common.compat import iteritems, text_type
from conda.exceptions import NoPackagesFoundError, UnsatisfiableError
from conda.models.dist import Dist
from conda.models.channel import Channel
from conda.models.index_record import IndexRecord
from conda.resolve import MatchSpec, Resolve
from conda.core.index import supplement_index_with_repodata, supplement_index_with_features
from os.path import dirname, join

import pytest

from conda.resolve import MatchSpec, Resolve, NoPackagesFound, Unsatisfiable
from tests.helpers import raises

with open(join(dirname(__file__), 'index.json')) as fi:
    repodata = json.load(fi)

index = {}
channel = Channel('defaults')
supplement_index_with_repodata(index, {'packages': repodata}, channel, 1)
supplement_index_with_features(index, ('mkl',))
r = Resolve(index)

f_mkl = set(['mkl'])


class TestMatchSpec(unittest.TestCase):

    def test_match(self):
        for spec, res in [
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
            self.assertEqual(m.match(Dist('numpy-1.7.1-py27_0.tar.bz2')), res)

        # both version numbers conforming to PEP 440
        self.assertFalse(MatchSpec('numpy >=1.0.1').match(Dist('numpy-1.0.1a-0.tar.bz2')))
        # both version numbers non-conforming to PEP 440
        self.assertFalse(MatchSpec('numpy >=1.0.1.vc11').match(Dist('numpy-1.0.1a.vc11-0.tar.bz2')))
        self.assertTrue(MatchSpec('numpy >=1.0.1*.vc11').match(Dist('numpy-1.0.1a.vc11-0.tar.bz2')))
        # one conforming, other non-conforming to PEP 440
        self.assertTrue(MatchSpec('numpy <1.0.1').match(Dist('numpy-1.0.1.vc11-0.tar.bz2')))
        self.assertTrue(MatchSpec('numpy <1.0.1').match(Dist('numpy-1.0.1a.vc11-0.tar.bz2')))
        self.assertFalse(MatchSpec('numpy >=1.0.1.vc11').match(Dist('numpy-1.0.1a-0.tar.bz2')))
        self.assertTrue(MatchSpec('numpy >=1.0.1a').match(Dist('numpy-1.0.1z-0.tar.bz2')))
        self.assertTrue(MatchSpec('numpy >=1.0.1a py27*').match(Dist('numpy-1.0.1z-py27_1.tar.bz2')))
        self.assertTrue(MatchSpec('blas * openblas').match(Dist('blas-1.0-openblas.tar.bz2')))

        self.assertTrue(MatchSpec('blas').is_simple())
        self.assertFalse(MatchSpec('blas').is_exact())
        self.assertFalse(MatchSpec('blas 1.0').is_simple())
        self.assertFalse(MatchSpec('blas 1.0').is_exact())
        self.assertFalse(MatchSpec('blas 1.0 1').is_simple())
        self.assertTrue(MatchSpec('blas 1.0 1').is_exact())
        self.assertFalse(MatchSpec('blas 1.0 *').is_exact())

        m = MatchSpec('blas 1.0', optional=True)
        m2 = MatchSpec(m, optional=False)
        m3 = MatchSpec(m2, target='blas-1.0-0.tar.bz2')
        m4 = MatchSpec(m3, target=None, optional=True)
        self.assertTrue(m.spec == m2.spec and m.optional != m2.optional)
        self.assertTrue(m2.spec == m3.spec and m2.optional == m3.optional and m2.target != m3.target)
        self.assertTrue(m == m4)

        self.assertRaises(ValueError, MatchSpec, 'blas (optional')
        self.assertRaises(ValueError, MatchSpec, 'blas (optional,test)')

    def test_to_filename(self):
        ms = MatchSpec('foo 1.7 52')
        self.assertEqual(ms.to_filename(), 'foo-1.7-52.tar.bz2')

        for spec in 'bitarray', 'pycosat 0.6.0', 'numpy 1.6*':
            ms = MatchSpec(spec)
            self.assertEqual(ms.to_filename(), None)

    def test_hash(self):
        a, b = MatchSpec('numpy 1.7*'), MatchSpec('numpy 1.7*')
        # optional should not change the hash
        d = MatchSpec('numpy 1.7* (optional)')
        self.assertTrue(a is not b)
        self.assertTrue(a is not d)
        self.assertEqual(a, b)
        self.assertNotEqual(a, d)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(hash(a), hash(d))
        c, d = MatchSpec('python'), MatchSpec('python 2.7.4')
        self.assertNotEqual(a, c)
        self.assertNotEqual(hash(a), hash(c))
        self.assertNotEqual(c, d)
        self.assertNotEqual(hash(c), hash(d))

    def test_string(self):
        a = MatchSpec("foo1 >=1.3 2 (optional,target=burg)")
        assert a.optional and a.target=='burg'


class TestSolve(unittest.TestCase):

    def assert_have_mkl(self, dists, names):
        for dist in dists:
            if dist.quad[0] in names:
                self.assertEqual(r.features(dist), f_mkl)

    def test_explicit0(self):
        self.assertEqual(r.explicit([]), [])

    def test_explicit1(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0']), None)
        self.assertEqual(r.explicit(['zlib']), None)
        self.assertEqual(r.explicit(['zlib 1.2.7']), None)
        # because zlib has no dependencies it is also explicit
        self.assertEqual(r.explicit(['zlib 1.2.7 0']),
                         [Dist('zlib-1.2.7-0.tar.bz2')])

    def test_explicit2(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
                                     'zlib 1.2.7 0']),
                         [Dist('pycosat-0.6.0-py27_0.tar.bz2'),
                          Dist('zlib-1.2.7-0.tar.bz2')])
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
                                     'zlib 1.2.7']), None)

    def test_explicitNone(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 notarealbuildstring']), None)

    def test_empty(self):
        self.assertEqual(r.install([]), [])

    def test_anaconda_14(self):
        specs = ['anaconda 1.4.0 np17py33_0']
        res = r.explicit(specs)
        self.assertEqual(len(res), 51)
        self.assertEqual(r.install(specs), res)
        specs.append('python 3.3*')
        self.assertEqual(r.explicit(specs), None)
        self.assertEqual(r.install(specs), res)

    def test_iopro_nomkl(self):
        installed = r.install(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'], returnall=True)
        installed = [[dist.to_filename() for dist in psol] for psol in installed]

        self.assertEqual(installed,
            [['iopro-1.4.3-np17py27_p0.tar.bz2',
              'numpy-1.7.1-py27_0.tar.bz2',
              'openssl-1.0.1c-0.tar.bz2',
              'python-2.7.5-0.tar.bz2',
              'readline-6.2-0.tar.bz2',
              'sqlite-3.7.13-0.tar.bz2',
              'system-5.8-1.tar.bz2',
              'tk-8.5.13-0.tar.bz2',
              'unixodbc-2.3.1-0.tar.bz2',
              'zlib-1.2.7-0.tar.bz2']])

    def test_iopro_mkl(self):
        installed = r.install(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*', 'mkl@'], returnall=True)
        installed = [[dist.to_filename() for dist in psol] for psol in installed]

        self.assertEqual(installed,
            [['iopro-1.4.3-np17py27_p0.tar.bz2',
              'mkl-rt-11.0-p0.tar.bz2',
              'numpy-1.7.1-py27_p0.tar.bz2',
              'openssl-1.0.1c-0.tar.bz2',
              'python-2.7.5-0.tar.bz2',
              'readline-6.2-0.tar.bz2',
              'sqlite-3.7.13-0.tar.bz2',
              'system-5.8-1.tar.bz2',
              'tk-8.5.13-0.tar.bz2',
              'unixodbc-2.3.1-0.tar.bz2',
              'zlib-1.2.7-0.tar.bz2']])

    def test_mkl(self):
        self.assertEqual(r.install(['mkl']),
                         r.install(['mkl 11*', 'mkl@']))

    def test_accelerate(self):
        self.assertEqual(
            r.install(['accelerate']),
            r.install(['accelerate', 'mkl@']))

    def test_scipy_mkl(self):
        dists = r.install(['scipy', 'python 2.7*', 'numpy 1.7*', 'mkl@'])
        self.assert_have_mkl(dists, ('numpy', 'scipy'))
        self.assertTrue(Dist('scipy-0.12.0-np17py27_p0.tar.bz2') in dists)

    def test_anaconda_nomkl(self):
        dists = r.install(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        self.assertEqual(len(dists), 107)
        self.assertTrue(Dist('scipy-0.12.0-np17py27_0.tar.bz2') in dists)

    def test_anaconda_mkl_2(self):
        # to test "with_features_depends"
        dists = r.install(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*', 'mkl@'])
        self.assert_have_mkl(dists, ('numpy', 'scipy', 'numexpr', 'scikit-learn'))
        self.assertTrue(Dist('scipy-0.12.0-np17py27_p0.tar.bz2') in dists)
        self.assertTrue(Dist('mkl-rt-11.0-p0.tar.bz2') in dists)
        self.assertEqual(len(dists), 108)

        dists2 = r.install(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*', 'mkl'])
        self.assertTrue(set(dists) <= set(dists2))
        self.assertEqual(len(dists2), 110)

    def test_anaconda_mkl_3(self):
        # to test "with_features_depends"
        dists = r.install(['anaconda 1.5.0', 'python 3*', 'mkl@'])
        self.assert_have_mkl(dists, ('numpy', 'scipy'))
        self.assertTrue(Dist('scipy-0.12.0-np17py33_p0.tar.bz2') in dists)
        self.assertTrue(Dist('mkl-rt-11.0-p0.tar.bz2') in dists)
        self.assertEqual(len(dists), 61)


def test_pseudo_boolean():
    # The latest version of iopro, 1.5.0, was not built against numpy 1.5
    assert r.install(['iopro', 'python 2.7*', 'numpy 1.5*'], returnall=True) == [[Dist(fn) for fn in [
        'iopro-1.4.3-np15py27_p0.tar.bz2',
        'numpy-1.5.1-py27_4.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'unixodbc-2.3.1-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]]

    assert r.install(['iopro', 'python 2.7*', 'numpy 1.5*', 'mkl@'], returnall=True) == [[Dist(fn) for fn in [
        'iopro-1.4.3-np15py27_p0.tar.bz2',
        'mkl-rt-11.0-p0.tar.bz2',
        'numpy-1.5.1-py27_p4.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'unixodbc-2.3.1-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]]


def test_get_dists():
    dists = r.get_reduced_index(["anaconda 1.5.0"])
    assert Dist('anaconda-1.5.0-np17py27_0.tar.bz2') in dists
    assert Dist('dynd-python-0.3.0-np17py33_0.tar.bz2') in dists


def test_generate_eq():
    dists = r.get_reduced_index(['anaconda'])
    r2 = Resolve(dists, True, True)
    C = r2.gen_clauses()
    eqv, eqb = r2.generate_version_metrics(C, list(r2.groups.keys()))
    # Should satisfy the following criteria:
    # - lower versions of the same package should should have higher
    #   coefficients.
    # - the same versions of the same package (e.g., different build strings)
    #   should have the same coefficients.
    # - a package that only has one version should not appear, unless
    #   include=True as it will have a 0 coefficient. The same is true of the
    #   latest version of a package.
    eqv = {Dist(key).to_filename(): value for key, value in iteritems(eqv)}
    eqb = {Dist(key).to_filename(): value for key, value in iteritems(eqb)}
    assert eqv == {
        'anaconda-1.4.0-np15py26_0.tar.bz2': 1,
        'anaconda-1.4.0-np15py27_0.tar.bz2': 1,
        'anaconda-1.4.0-np16py26_0.tar.bz2': 1,
        'anaconda-1.4.0-np16py27_0.tar.bz2': 1,
        'anaconda-1.4.0-np17py26_0.tar.bz2': 1,
        'anaconda-1.4.0-np17py27_0.tar.bz2': 1,
        'anaconda-1.4.0-np17py33_0.tar.bz2': 1,
        'astropy-0.2-np15py26_0.tar.bz2': 1,
        'astropy-0.2-np15py27_0.tar.bz2': 1,
        'astropy-0.2-np16py26_0.tar.bz2': 1,
        'astropy-0.2-np16py27_0.tar.bz2': 1,
        'astropy-0.2-np17py26_0.tar.bz2': 1,
        'astropy-0.2-np17py27_0.tar.bz2': 1,
        'astropy-0.2-np17py33_0.tar.bz2': 1,
        'biopython-1.60-np15py26_0.tar.bz2': 1,
        'biopython-1.60-np15py27_0.tar.bz2': 1,
        'biopython-1.60-np16py26_0.tar.bz2': 1,
        'biopython-1.60-np16py27_0.tar.bz2': 1,
        'biopython-1.60-np17py26_0.tar.bz2': 1,
        'biopython-1.60-np17py27_0.tar.bz2': 1,
        'bitarray-0.8.0-py26_0.tar.bz2': 1,
        'bitarray-0.8.0-py27_0.tar.bz2': 1,
        'bitarray-0.8.0-py33_0.tar.bz2': 1,
        'boto-2.8.0-py26_0.tar.bz2': 1,
        'boto-2.8.0-py27_0.tar.bz2': 1,
        'conda-1.4.4-py27_0.tar.bz2': 1,
        'cython-0.18-py26_0.tar.bz2': 1,
        'cython-0.18-py27_0.tar.bz2': 1,
        'cython-0.18-py33_0.tar.bz2': 1,
        'distribute-0.6.34-py26_1.tar.bz2': 1,
        'distribute-0.6.34-py27_1.tar.bz2': 1,
        'distribute-0.6.34-py33_1.tar.bz2': 1,
        'gevent-0.13.7-py26_0.tar.bz2': 1,
        'gevent-0.13.7-py27_0.tar.bz2': 1,
        'ipython-0.13.1-py26_1.tar.bz2': 1,
        'ipython-0.13.1-py27_1.tar.bz2': 1,
        'ipython-0.13.1-py33_1.tar.bz2': 1,
        'llvmpy-0.11.1-py26_0.tar.bz2': 1,
        'llvmpy-0.11.1-py27_0.tar.bz2': 1,
        'llvmpy-0.11.1-py33_0.tar.bz2': 1,
        'lxml-3.0.2-py26_0.tar.bz2': 1,
        'lxml-3.0.2-py27_0.tar.bz2': 1,
        'lxml-3.0.2-py33_0.tar.bz2': 1,
        'matplotlib-1.2.0-np15py26_1.tar.bz2': 1,
        'matplotlib-1.2.0-np15py27_1.tar.bz2': 1,
        'matplotlib-1.2.0-np16py26_1.tar.bz2': 1,
        'matplotlib-1.2.0-np16py27_1.tar.bz2': 1,
        'matplotlib-1.2.0-np17py26_1.tar.bz2': 1,
        'matplotlib-1.2.0-np17py27_1.tar.bz2': 1,
        'matplotlib-1.2.0-np17py33_1.tar.bz2': 1,
        'nose-1.2.1-py26_0.tar.bz2': 1,
        'nose-1.2.1-py27_0.tar.bz2': 1,
        'nose-1.2.1-py33_0.tar.bz2': 1,
        'numba-0.7.0-np16py26_1.tar.bz2': 1,
        'numba-0.7.0-np16py27_1.tar.bz2': 1,
        'numba-0.7.0-np17py26_1.tar.bz2': 1,
        'numba-0.7.0-np17py27_1.tar.bz2': 1,
        'numpy-1.5.1-py26_3.tar.bz2': 3,
        'numpy-1.5.1-py27_3.tar.bz2': 3,
        'numpy-1.6.2-py26_3.tar.bz2': 2,
        'numpy-1.6.2-py26_4.tar.bz2': 2,
        'numpy-1.6.2-py26_p4.tar.bz2': 2,
        'numpy-1.6.2-py27_3.tar.bz2': 2,
        'numpy-1.6.2-py27_4.tar.bz2': 2,
        'numpy-1.6.2-py27_p4.tar.bz2': 2,
        'numpy-1.7.0-py26_0.tar.bz2': 1,
        'numpy-1.7.0-py27_0.tar.bz2': 1,
        'numpy-1.7.0-py33_0.tar.bz2': 1,
        'pandas-0.10.0-np16py26_0.tar.bz2': 2,
        'pandas-0.10.0-np16py27_0.tar.bz2': 2,
        'pandas-0.10.0-np17py26_0.tar.bz2': 2,
        'pandas-0.10.0-np17py27_0.tar.bz2': 2,
        'pandas-0.10.1-np16py26_0.tar.bz2': 1,
        'pandas-0.10.1-np16py27_0.tar.bz2': 1,
        'pandas-0.10.1-np17py26_0.tar.bz2': 1,
        'pandas-0.10.1-np17py27_0.tar.bz2': 1,
        'pandas-0.10.1-np17py33_0.tar.bz2': 1,
        'pandas-0.8.1-np16py26_0.tar.bz2': 5,
        'pandas-0.8.1-np16py27_0.tar.bz2': 5,
        'pandas-0.8.1-np17py26_0.tar.bz2': 5,
        'pandas-0.8.1-np17py27_0.tar.bz2': 5,
        'pandas-0.9.0-np16py26_0.tar.bz2': 4,
        'pandas-0.9.0-np16py27_0.tar.bz2': 4,
        'pandas-0.9.0-np17py26_0.tar.bz2': 4,
        'pandas-0.9.0-np17py27_0.tar.bz2': 4,
        'pandas-0.9.1-np16py26_0.tar.bz2': 3,
        'pandas-0.9.1-np16py27_0.tar.bz2': 3,
        'pandas-0.9.1-np17py26_0.tar.bz2': 3,
        'pandas-0.9.1-np17py27_0.tar.bz2': 3,
        'pip-1.2.1-py26_1.tar.bz2': 1,
        'pip-1.2.1-py27_1.tar.bz2': 1,
        'pip-1.2.1-py33_1.tar.bz2': 1,
        'psutil-0.6.1-py26_0.tar.bz2': 1,
        'psutil-0.6.1-py27_0.tar.bz2': 1,
        'psutil-0.6.1-py33_0.tar.bz2': 1,
        'pyflakes-0.6.1-py26_0.tar.bz2': 1,
        'pyflakes-0.6.1-py27_0.tar.bz2': 1,
        'pyflakes-0.6.1-py33_0.tar.bz2': 1,
        'python-2.6.8-6.tar.bz2': 4,
        'python-2.7.3-7.tar.bz2': 3,
        'python-2.7.4-0.tar.bz2': 2,
        'python-3.3.0-4.tar.bz2': 1,
        'pytz-2012j-py26_0.tar.bz2': 1,
        'pytz-2012j-py27_0.tar.bz2': 1,
        'pytz-2012j-py33_0.tar.bz2': 1,
        'requests-0.13.9-py26_0.tar.bz2': 1,
        'requests-0.13.9-py27_0.tar.bz2': 1,
        'requests-0.13.9-py33_0.tar.bz2': 1,
        'scikit-learn-0.13-np15py26_1.tar.bz2': 1,
        'scikit-learn-0.13-np15py27_1.tar.bz2': 1,
        'scikit-learn-0.13-np16py26_1.tar.bz2': 1,
        'scikit-learn-0.13-np16py27_1.tar.bz2': 1,
        'scikit-learn-0.13-np17py26_1.tar.bz2': 1,
        'scikit-learn-0.13-np17py27_1.tar.bz2': 1,
        'scipy-0.11.0-np15py26_3.tar.bz2': 1,
        'scipy-0.11.0-np15py27_3.tar.bz2': 1,
        'scipy-0.11.0-np16py26_3.tar.bz2': 1,
        'scipy-0.11.0-np16py27_3.tar.bz2': 1,
        'scipy-0.11.0-np17py26_3.tar.bz2': 1,
        'scipy-0.11.0-np17py27_3.tar.bz2': 1,
        'scipy-0.11.0-np17py33_3.tar.bz2': 1,
        'six-1.2.0-py26_0.tar.bz2': 1,
        'six-1.2.0-py27_0.tar.bz2': 1,
        'six-1.2.0-py33_0.tar.bz2': 1,
        'spyder-2.1.13-py27_0.tar.bz2': 1,
        'sqlalchemy-0.7.8-py26_0.tar.bz2': 1,
        'sqlalchemy-0.7.8-py27_0.tar.bz2': 1,
        'sqlalchemy-0.7.8-py33_0.tar.bz2': 1,
        'sympy-0.7.1-py26_0.tar.bz2': 1,
        'sympy-0.7.1-py27_0.tar.bz2': 1,
        'tornado-2.4.1-py26_0.tar.bz2': 1,
        'tornado-2.4.1-py27_0.tar.bz2': 1,
        'tornado-2.4.1-py33_0.tar.bz2': 1,
        'xlrd-0.9.0-py26_0.tar.bz2': 1,
        'xlrd-0.9.0-py27_0.tar.bz2': 1,
        'xlrd-0.9.0-py33_0.tar.bz2': 1,
        'xlwt-0.7.4-py26_0.tar.bz2': 1,
        'xlwt-0.7.4-py27_0.tar.bz2': 1}
    assert eqb == {
        'cairo-1.12.2-0.tar.bz2': 1,
        'cubes-0.10.2-py27_0.tar.bz2': 1,
        'dateutil-2.1-py26_0.tar.bz2': 1,
        'dateutil-2.1-py27_0.tar.bz2': 1,
        'dateutil-2.1-py33_0.tar.bz2': 1,
        'gevent-websocket-0.3.6-py26_1.tar.bz2': 1,
        'gevent-websocket-0.3.6-py27_1.tar.bz2': 1,
        'gevent_zeromq-0.2.5-py26_1.tar.bz2': 1,
        'gevent_zeromq-0.2.5-py27_1.tar.bz2': 1,
        'libnetcdf-4.2.1.1-0.tar.bz2': 1,
        'numexpr-2.0.1-np16py26_1.tar.bz2': 2,
        'numexpr-2.0.1-np16py26_2.tar.bz2': 1,
        'numexpr-2.0.1-np16py26_ce0.tar.bz2': 3,
        'numexpr-2.0.1-np16py26_p1.tar.bz2': 2,
        'numexpr-2.0.1-np16py26_p2.tar.bz2': 1,
        'numexpr-2.0.1-np16py26_pro0.tar.bz2': 3,
        'numexpr-2.0.1-np16py27_1.tar.bz2': 2,
        'numexpr-2.0.1-np16py27_2.tar.bz2': 1,
        'numexpr-2.0.1-np16py27_ce0.tar.bz2': 3,
        'numexpr-2.0.1-np16py27_p1.tar.bz2': 2,
        'numexpr-2.0.1-np16py27_p2.tar.bz2': 1,
        'numexpr-2.0.1-np16py27_pro0.tar.bz2': 3,
        'numexpr-2.0.1-np17py26_1.tar.bz2': 2,
        'numexpr-2.0.1-np17py26_2.tar.bz2': 1,
        'numexpr-2.0.1-np17py26_ce0.tar.bz2': 3,
        'numexpr-2.0.1-np17py26_p1.tar.bz2': 2,
        'numexpr-2.0.1-np17py26_p2.tar.bz2': 1,
        'numexpr-2.0.1-np17py26_pro0.tar.bz2': 3,
        'numexpr-2.0.1-np17py27_1.tar.bz2': 2,
        'numexpr-2.0.1-np17py27_2.tar.bz2': 1,
        'numexpr-2.0.1-np17py27_ce0.tar.bz2': 3,
        'numexpr-2.0.1-np17py27_p1.tar.bz2': 2,
        'numexpr-2.0.1-np17py27_p2.tar.bz2': 1,
        'numexpr-2.0.1-np17py27_pro0.tar.bz2': 3,
        'numpy-1.6.2-py26_3.tar.bz2': 1,
        'numpy-1.6.2-py27_3.tar.bz2': 1,
        'py2cairo-1.10.0-py26_0.tar.bz2': 1,
        'py2cairo-1.10.0-py27_0.tar.bz2': 1,
        'pycurl-7.19.0-py26_0.tar.bz2': 1,
        'pycurl-7.19.0-py27_0.tar.bz2': 1,
        'pysal-1.5.0-np15py27_0.tar.bz2': 1,
        'pysal-1.5.0-np16py27_0.tar.bz2': 1,
        'pysal-1.5.0-np17py27_0.tar.bz2': 1,
        'pytest-2.3.4-py26_0.tar.bz2': 1,
        'pytest-2.3.4-py27_0.tar.bz2': 1,
        'pyzmq-2.2.0.1-py26_0.tar.bz2': 1,
        'pyzmq-2.2.0.1-py27_0.tar.bz2': 1,
        'pyzmq-2.2.0.1-py33_0.tar.bz2': 1,
        'scikit-image-0.8.2-np16py26_0.tar.bz2': 1,
        'scikit-image-0.8.2-np16py27_0.tar.bz2': 1,
        'scikit-image-0.8.2-np17py26_0.tar.bz2': 1,
        'scikit-image-0.8.2-np17py27_0.tar.bz2': 1,
        'scikit-image-0.8.2-np17py33_0.tar.bz2': 1,
        'sphinx-1.1.3-py26_2.tar.bz2': 1,
        'sphinx-1.1.3-py27_2.tar.bz2': 1,
        'sphinx-1.1.3-py33_2.tar.bz2': 1,
        'statsmodels-0.4.3-np16py26_0.tar.bz2': 1,
        'statsmodels-0.4.3-np16py27_0.tar.bz2': 1,
        'statsmodels-0.4.3-np17py26_0.tar.bz2': 1,
        'statsmodels-0.4.3-np17py27_0.tar.bz2': 1,
        'system-5.8-0.tar.bz2': 1,
        'theano-0.5.0-np15py26_0.tar.bz2': 1,
        'theano-0.5.0-np15py27_0.tar.bz2': 1,
        'theano-0.5.0-np16py26_0.tar.bz2': 1,
        'theano-0.5.0-np16py27_0.tar.bz2': 1,
        'theano-0.5.0-np17py26_0.tar.bz2': 1,
        'theano-0.5.0-np17py27_0.tar.bz2': 1,
        'zeromq-2.2.0-0.tar.bz2': 1}


def test_unsat():
    # scipy 0.12.0b1 is not built for numpy 1.5, only 1.6 and 1.7
    assert raises(UnsatisfiableError, lambda: r.install(['numpy 1.5*', 'scipy 0.12.0b1']))
    # numpy 1.5 does not have a python 3 package
    assert raises(UnsatisfiableError, lambda: r.install(['numpy 1.5*', 'python 3*']))
    assert raises(UnsatisfiableError, lambda: r.install(['numpy 1.5*', 'numpy 1.6*']))


def test_nonexistent():
    assert not r.find_matches(MatchSpec('notarealpackage 2.0*'))
    assert raises(NoPackagesFoundError, lambda: r.install(['notarealpackage 2.0*']))
    # This exact version of NumPy does not exist
    assert raises(NoPackagesFoundError, lambda: r.install(['numpy 1.5']))


def test_nonexistent_deps():
    index2 = index.copy()
    index2['mypackage-1.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    })
    index2['mypackage-1.1-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    })
    index2['anotherpackage-1.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.1'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.1'],
        'version': '1.0',
    })
    index2['anotherpackage-2.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    })
    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r = Resolve(index2)

    assert set(r.find_matches(MatchSpec('mypackage'))) == {
        Dist('mypackage-1.0-py33_0.tar.bz2'),
        Dist('mypackage-1.1-py33_0.tar.bz2'),
    }
    assert set(d.to_filename() for d in r.get_reduced_index(['mypackage']).keys()) == {
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.1.2-py33_0.tar.bz2',
        'nose-1.2.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.0-2.tar.bz2',
        'python-3.3.0-3.tar.bz2',
        'python-3.3.0-4.tar.bz2',
        'python-3.3.0-pro0.tar.bz2',
        'python-3.3.0-pro1.tar.bz2',
        'python-3.3.1-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2'}

    assert r.install(['mypackage']) == r.install(['mypackage 1.1']) == [Dist(dname) for dname in [
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]
    assert raises(NoPackagesFoundError, lambda: r.install(['mypackage 1.0']))
    assert raises(NoPackagesFoundError, lambda: r.install(['mypackage 1.0', 'burgertime 1.0']))

    assert r.install(['anotherpackage 1.0']) == [Dist(dname) for dname in [
        'anotherpackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]

    assert r.install(['anotherpackage']) == [Dist(dname) for dname in [
        'anotherpackage-2.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]

    # This time, the latest version is messed up
    index3 = index.copy()
    index3['mypackage-1.1-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    })
    index3['mypackage-1.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    })
    index3['anotherpackage-1.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.0'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.0'],
        'version': '1.0',
    })
    index3['anotherpackage-2.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    })
    index3 = {Dist(key): value for key, value in iteritems(index3)}
    r = Resolve(index3)

    assert set(d.to_filename() for d in r.find_matches(MatchSpec('mypackage'))) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        }
    assert set(d.to_filename() for d in r.get_reduced_index(['mypackage']).keys()) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.1.2-py33_0.tar.bz2',
        'nose-1.2.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.0-2.tar.bz2',
        'python-3.3.0-3.tar.bz2',
        'python-3.3.0-4.tar.bz2',
        'python-3.3.0-pro0.tar.bz2',
        'python-3.3.0-pro1.tar.bz2',
        'python-3.3.1-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2'}

    assert r.install(['mypackage']) == r.install(['mypackage 1.0']) == [Dist(dname) for dname in [
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]
    assert raises(NoPackagesFoundError, lambda: r.install(['mypackage 1.1']))

    assert r.install(['anotherpackage 1.0']) == [Dist(dname) for dname in [
        'anotherpackage-1.0-py33_0.tar.bz2',
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]

    # If recursive checking is working correctly, this will give
    # anotherpackage 2.0, not anotherpackage 1.0
    assert r.install(['anotherpackage']) == [Dist(dname) for dname in [
        'anotherpackage-2.0-py33_0.tar.bz2',
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]


def test_install_package_with_feature():
    index2 = index.copy()
    index2['mypackage-1.0-featurepy33_0.tar.bz2'] = IndexRecord(**{
        'build': 'featurepy33_0',
        'build_number': 0,
        'depends': ['python 3.3*'],
        'name': 'mypackage',
        'version': '1.0',
        'features': 'feature',
    })
    index2['feature-1.0-py33_0.tar.bz2'] = IndexRecord(**{
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['python 3.3*'],
        'name': 'feature',
        'version': '1.0',
        'track_features': 'feature',
    })

    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r = Resolve(index2)

    # It should not raise
    r.install(['mypackage','feature 1.0'])


def test_circular_dependencies():
    index2 = index.copy()
    index2['package1-1.0-0.tar.bz2'] = IndexRecord(**{
        'build': '0',
        'build_number': 0,
        'depends': ['package2'],
        'name': 'package1',
        'requires': ['package2'],
        'version': '1.0',
    })
    index2['package2-1.0-0.tar.bz2'] = IndexRecord(**{
        'build': '0',
        'build_number': 0,
        'depends': ['package1'],
        'name': 'package2',
        'requires': ['package1'],
        'version': '1.0',
    })
    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r = Resolve(index2)

    assert set(r.find_matches(MatchSpec('package1'))) == {
        Dist('package1-1.0-0.tar.bz2'),
    }
    assert set(r.get_reduced_index(['package1']).keys()) == {
        Dist('package1-1.0-0.tar.bz2'),
        Dist('package2-1.0-0.tar.bz2'),
    }
    assert r.install(['package1']) == r.install(['package2']) == \
        r.install(['package1', 'package2']) == [
        Dist('package1-1.0-0.tar.bz2'),
        Dist('package2-1.0-0.tar.bz2'),
    ]


def test_irrational_version():
    assert r.install(['pytz 2012d', 'python 3*'], returnall=True) == [[Dist(fname) for fname in [
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'pytz-2012d-py33_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2'
    ]]]


def test_no_features():
    # Without this, there would be another solution including 'scipy-0.11.0-np16py26_p3.tar.bz2'.
    assert r.install(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'],
        returnall=True) == [[Dist(fname) for fname in [
            'numpy-1.6.2-py26_4.tar.bz2',
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.6.8-6.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'scipy-0.11.0-np16py26_3.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]]

    assert r.install(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*', 'mkl@'],
        returnall=True) == [[Dist(fname) for fname in [
            'mkl-rt-11.0-p0.tar.bz2',           # This,
            'numpy-1.6.2-py26_p4.tar.bz2',      # this,
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.6.8-6.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'scipy-0.11.0-np16py26_p3.tar.bz2', # and this are different.
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]]

    index2 = index.copy()
    index2["pandas-0.12.0-np16py27_0.tar.bz2"] = IndexRecord(**{
            "build": "np16py27_0",
            "build_number": 0,
            "depends": [
              "dateutil",
              "numpy 1.6*",
              "python 2.7*",
              "pytz"
            ],
            "name": "pandas",
            "requires": [
              "dateutil 1.5",
              "numpy 1.6",
              "python 2.7",
              "pytz"
            ],
            "version": "0.12.0"
        })
    # Make it want to choose the pro version by having it be newer.
    index2["numpy-1.6.2-py27_p5.tar.bz2"] = IndexRecord(**{
            "build": "py27_p5",
            "build_number": 5,
            "depends": [
              "mkl-rt 11.0",
              "python 2.7*"
            ],
            "features": "mkl",
            "name": "numpy",
            "pub_date": "2013-04-29",
            "requires": [
              "mkl-rt 11.0",
              "python 2.7"
            ],
            "version": "1.6.2"
        })

    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r2 = Resolve(index2)

    # This should not pick any mkl packages (the difference here is that none
    # of the specs directly have mkl versions)
    assert r2.solve(['pandas 0.12.0 np16py27_0', 'python 2.7*'],
        returnall=True) == [[Dist(fname) for fname in [
            'dateutil-2.1-py27_1.tar.bz2',
            'numpy-1.6.2-py27_4.tar.bz2',
            'openssl-1.0.1c-0.tar.bz2',
            'pandas-0.12.0-np16py27_0.tar.bz2',
            'python-2.7.5-0.tar.bz2',
            'pytz-2013b-py27_0.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'six-1.3.0-py27_0.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]]

    assert r2.solve(['pandas 0.12.0 np16py27_0', 'python 2.7*', 'mkl@'],
        returnall=True)[0] == [[Dist(fname) for fname in [
            'dateutil-2.1-py27_1.tar.bz2',
            'mkl-rt-11.0-p0.tar.bz2',           # This
            'numpy-1.6.2-py27_p5.tar.bz2',      # and this are different.
            'openssl-1.0.1c-0.tar.bz2',
            'pandas-0.12.0-np16py27_0.tar.bz2',
            'python-2.7.5-0.tar.bz2',
            'pytz-2013b-py27_0.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'six-1.3.0-py27_0.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]][0]


def test_multiple_solution():
    index2 = index.copy()
    fn = 'pandas-0.11.0-np16py27_1.tar.bz2'
    res1 = set([fn])
    for k in range(1,15):
        fn2 = Dist('%s_%d.tar.bz2'%(fn[:-8],k))
        index2[fn2] = index[Dist(fn)]
        res1.add(fn2)
    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r = Resolve(index2)
    res = r.solve(['pandas', 'python 2.7*', 'numpy 1.6*'], returnall=True)
    res = set([y for x in res for y in x if r.package_name(y).startswith('pandas')])
    assert len(res) <= len(res1)


def test_broken_install():
    installed = r.install(['pandas', 'python 2.7*', 'numpy 1.6*'])
    assert installed == [Dist(fname) for fname in [
        'dateutil-2.1-py27_1.tar.bz2',
        'numpy-1.6.2-py27_4.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'pandas-0.11.0-np16py27_1.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'pytz-2013b-py27_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'scipy-0.12.0-np16py27_0.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2']]

    # Add an incompatible numpy; installation should be untouched
    installed1 = list(installed)
    installed1[1] = Dist('numpy-1.7.1-py33_p0.tar.bz2')
    assert set(r.install([], installed1)) == set(installed1)
    assert r.install(['numpy 1.6*'], installed1) == installed

    # Add an incompatible pandas; installation should be untouched, then fixed
    installed2 = list(installed)
    installed2[3] = Dist('pandas-0.11.0-np17py27_1.tar.bz2')
    assert set(r.install([], installed2)) == set(installed2)
    assert r.install(['pandas'], installed2) == installed

    # Removing pandas should fix numpy, since pandas depends on it
    installed3 = list(installed)
    installed3[1] = Dist('numpy-1.7.1-py33_p0.tar.bz2')
    installed3[3] = Dist('pandas-0.11.0-np17py27_1.tar.bz2')
    installed4 = r.remove(['pandas'], installed)
    assert r.bad_installed(installed4, [])[0] is None

    # Tests removed involving packages not in the index, because we
    # always insure installed packages _are_ in the index


def test_remove():
    installed = r.install(['pandas', 'python 2.7*'])
    assert installed == [Dist(fname) for fname in [
        'dateutil-2.1-py27_1.tar.bz2',
        'numpy-1.7.1-py27_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'pandas-0.11.0-np17py27_1.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'pytz-2013b-py27_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'scipy-0.12.0-np17py27_0.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2']]

    assert r.remove(['pandas'], installed=installed) == [Dist(fname) for fname in [
        'dateutil-2.1-py27_1.tar.bz2',
        'numpy-1.7.1-py27_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'pytz-2013b-py27_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'scipy-0.12.0-np17py27_0.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2']]

    # Pandas requires numpy
    assert r.remove(['numpy'], installed=installed) == [Dist(fname) for fname in [
        'dateutil-2.1-py27_1.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'pytz-2013b-py27_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2']]


def test_channel_priority():
    fn1 = 'pandas-0.10.1-np17py27_0.tar.bz2'
    fn2 = 'other::' + fn1
    spec = ['pandas', 'python 2.7*']
    index2 = index.copy()
    index2[Dist(fn2)] = index2[Dist(fn1)].copy()
    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r2 = Resolve(index2)
    rec = r2.index[Dist(fn2)]

    os.environ['CONDA_CHANNEL_PRIORITY'] = 'True'
    reset_context(())

    r2.index[Dist(fn2)] = IndexRecord.from_objects(r2.index[Dist(fn2)], priority=0)
    # Should select the "other", older package because it
    # has a lower channel priority number
    installed1 = r2.install(spec)
    # Should select the newer package because now the "other"
    # package has a higher priority number
    r2.index[Dist(fn2)] = IndexRecord.from_objects(r2.index[Dist(fn2)], priority=2)
    installed2 = r2.install(spec)
    # Should also select the newer package because we have
    # turned off channel priority altogether

    os.environ['CONDA_CHANNEL_PRIORITY'] = 'False'
    reset_context(())

    r2.index[Dist(fn2)] = IndexRecord.from_objects(r2.index[Dist(fn2)], priority=0)
    installed3 = r2.install(spec)
    assert installed1 != installed2
    assert installed1 != installed3
    assert installed2 == installed3


def test_dependency_sort():
    specs = ['pandas','python 2.7*','numpy 1.6*']
    installed = r.install(specs)
    must_have = {r.package_name(dist): dist for dist in installed}
    installed = r.dependency_sort(must_have)

    results_should_be = [
        'openssl-1.0.1c-0',
        'readline-6.2-0',
        'sqlite-3.7.13-0',
        'system-5.8-1',
        'tk-8.5.13-0',
        'zlib-1.2.7-0',
        'python-2.7.5-0',
        'numpy-1.6.2-py27_4',
        'pytz-2013b-py27_0',
        'six-1.3.0-py27_0',
        'dateutil-2.1-py27_1',
        'scipy-0.12.0-np16py27_0',
        'pandas-0.11.0-np16py27_1'
    ]
    assert len(installed) == len(results_should_be)
    assert [d.dist_name for d in installed] == results_should_be


def test_update_deps():
    installed = r.install(['python 2.7*', 'numpy 1.6*', 'pandas 0.10.1'])
    assert installed == [Dist(fn) for fn in [
        'dateutil-2.1-py27_1.tar.bz2',
        'numpy-1.6.2-py27_4.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'pandas-0.10.1-np16py27_0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'scipy-0.11.0-np16py27_3.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]

    # scipy, and pandas should all be updated here. pytz is a new
    # dependency of pandas. But numpy does not _need_ to be updated
    # to get the latest version of pandas, so it stays put.
    assert r.install(['pandas', 'python 2.7*'], installed=installed,
        update_deps=True, returnall=True) == [[Dist(fn) for fn in [
        'dateutil-2.1-py27_1.tar.bz2',
        'numpy-1.6.2-py27_4.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'pandas-0.11.0-np16py27_1.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'pytz-2013b-py27_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'scipy-0.12.0-np16py27_0.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2']]]

    # pandas should be updated here. However, it's going to try to not update
    # scipy, so it won't be updated to the latest version (0.11.0).
    assert r.install(['pandas', 'python 2.7*'], installed=installed,
        update_deps=False, returnall=True) == [[Dist(fn) for fn in [
        'dateutil-2.1-py27_1.tar.bz2',
        'numpy-1.6.2-py27_4.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'pandas-0.10.1-np16py27_0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'scipy-0.11.0-np16py27_3.tar.bz2',
        'six-1.3.0-py27_0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]]]
