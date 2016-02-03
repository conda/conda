from __future__ import print_function, absolute_import
import json
import unittest
from os.path import dirname, join

import pytest

from conda.resolve import MatchSpec, Package, Resolve, NoPackagesFound

from tests.helpers import raises


with open(join(dirname(__file__), 'index.json')) as fi:
    index = json.load(fi)

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
            self.assertEqual(m.match('numpy-1.7.1-py27_0.tar.bz2'), res)

        # both version numbers conforming to PEP 440
        self.assertFalse(MatchSpec('numpy >=1.0.1').match('numpy-1.0.1a-0.tar.bz2'))
        # both version numbers non-conforming to PEP 440
        self.assertFalse(MatchSpec('numpy >=1.0.1.vc11').match('numpy-1.0.1a.vc11-0.tar.bz2'))
        self.assertTrue(MatchSpec('numpy >=1.0.1*.vc11').match('numpy-1.0.1a.vc11-0.tar.bz2'))
        # one conforming, other non-conforming to PEP 440
        self.assertTrue(MatchSpec('numpy <1.0.1').match('numpy-1.0.1.vc11-0.tar.bz2'))
        self.assertTrue(MatchSpec('numpy <1.0.1').match('numpy-1.0.1a.vc11-0.tar.bz2'))
        self.assertFalse(MatchSpec('numpy >=1.0.1.vc11').match('numpy-1.0.1a-0.tar.bz2'))
        self.assertTrue(MatchSpec('numpy >=1.0.1a').match('numpy-1.0.1z-0.tar.bz2'))

    def test_to_filename(self):
        ms = MatchSpec('foo 1.7 52')
        self.assertEqual(ms.to_filename(), 'foo-1.7-52.tar.bz2')

        for spec in 'bitarray', 'pycosat 0.6.0', 'numpy 1.6*':
            ms = MatchSpec(spec)
            self.assertEqual(ms.to_filename(), None)

    def test_hash(self):
        a, b = MatchSpec('numpy 1.7*'), MatchSpec('numpy 1.7*')
        self.assertTrue(a is not b)
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        c, d = MatchSpec('python'), MatchSpec('python 2.7.4')
        self.assertNotEqual(a, c)
        self.assertNotEqual(hash(a), hash(c))
        self.assertNotEqual(c, d)
        self.assertNotEqual(hash(c), hash(d))



class TestPackage(unittest.TestCase):

    def test_llvm(self):
        ms = MatchSpec('llvm')
        pkgs = [Package(fn, r.index[fn]) for fn in r.find_matches(ms)]
        pkgs.sort()
        self.assertEqual([p.fn for p in pkgs],
                         ['llvm-3.1-0.tar.bz2',
                          'llvm-3.1-1.tar.bz2',
                          'llvm-3.2-0.tar.bz2'])

    def test_different_names(self):
        pkgs = [Package(fn, r.index[fn]) for fn in [
                'llvm-3.1-1.tar.bz2', 'python-2.7.5-0.tar.bz2']]
        self.assertRaises(TypeError, pkgs.sort)


class TestSolve(unittest.TestCase):

    def setUp(self):
        r.msd_cache = {}

    def assert_have_mkl(self, dists, names):
        for fn in dists:
            if fn.rsplit('-', 2)[0] in names:
                self.assertEqual(r.features(fn), f_mkl)

    def test_explicit0(self):
        self.assertEqual(r.explicit([]), [])

    def test_explicit1(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0']), None)
        self.assertEqual(r.explicit(['zlib']), None)
        self.assertEqual(r.explicit(['zlib 1.2.7']), None)
        # because zlib has no dependencies it is also explicit
        self.assertEqual(r.explicit(['zlib 1.2.7 0']),
                         ['zlib-1.2.7-0.tar.bz2'])

    def test_explicit2(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
                                     'zlib 1.2.7 0']),
                         ['pycosat-0.6.0-py27_0.tar.bz2',
                          'zlib-1.2.7-0.tar.bz2'])
        self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
                                     'zlib 1.2.7']), None)

    def test_explicitNone(self):
        self.assertEqual(r.explicit(['pycosat 0.6.0 notarealbuildstring']), None)

    def test_empty(self):
        self.assertEqual(r.solve([]), [])

    def test_anaconda_14(self):
        specs = ['anaconda 1.4.0 np17py33_0']
        res = r.explicit(specs)
        self.assertEqual(len(res), 51)
        self.assertEqual(r.solve(specs), res)
        specs.append('python 3.3*')
        self.assertEqual(r.explicit(specs), None)
        self.assertEqual(r.solve(specs), res)

    def test_iopro_nomkl(self):
        self.assertEqual(
            r.solve2(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
                     set(), returnall=True),
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
        self.assertEqual(
            r.solve2(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
                    f_mkl, returnall=True),
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
        self.assertEqual(r.solve(['mkl'], set()),
                         r.solve(['mkl'], f_mkl))

    def test_accelerate(self):
        self.assertEqual(
            r.solve(['accelerate'], set()),
            r.solve(['accelerate'], f_mkl))

    def test_scipy_mkl(self):
        dists = r.solve(['scipy', 'python 2.7*', 'numpy 1.7*'],
                        features=f_mkl)
        self.assert_have_mkl(dists, ('numpy', 'scipy'))
        self.assertTrue('scipy-0.12.0-np17py27_p0.tar.bz2' in dists)

    def test_anaconda_nomkl(self):
        dists = r.solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        self.assertEqual(len(dists), 107)
        self.assertTrue('scipy-0.12.0-np17py27_0.tar.bz2' in dists)

    def test_anaconda_mkl_2(self):
        # to test "with_features_depends"
        dists = r.solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'],
                        features=f_mkl)
        self.assert_have_mkl(dists,
                             ('numpy', 'scipy', 'numexpr', 'scikit-learn'))
        self.assertTrue('scipy-0.12.0-np17py27_p0.tar.bz2' in dists)
        self.assertTrue('mkl-rt-11.0-p0.tar.bz2' in dists)
        self.assertEqual(len(dists), 108)

        dists2 = r.solve(['anaconda 1.5.0',
                          'python 2.7*', 'numpy 1.7*', 'mkl'])
        self.assertTrue(set(dists) <= set(dists2))
        self.assertEqual(len(dists2), 110)

    def test_anaconda_mkl_3(self):
        # to test "with_features_depends"
        dists = r.solve(['anaconda 1.5.0', 'python 3*'], features=f_mkl)
        self.assert_have_mkl(dists, ('numpy', 'scipy'))
        self.assertTrue('scipy-0.12.0-np17py33_p0.tar.bz2' in dists)
        self.assertTrue('mkl-rt-11.0-p0.tar.bz2' in dists)
        self.assertEqual(len(dists), 61)


class TestFindSubstitute(unittest.TestCase):

    def setUp(self):
        r.msd_cache = {}

    def test1(self):
        installed = r.solve(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'],
                            features=f_mkl)
        for old, new in [('numpy-1.7.1-py27_p0.tar.bz2',
                          'numpy-1.7.1-py27_0.tar.bz2'),
                         ('scipy-0.12.0-np17py27_p0.tar.bz2',
                          'scipy-0.12.0-np17py27_0.tar.bz2'),
                         ('mkl-rt-11.0-p0.tar.bz2', None)]:
            self.assertTrue(old in installed)
            self.assertEqual(r.find_substitute(installed, f_mkl, old), new)


@pytest.mark.slow
def test_pseudo_boolean():
    # The latest version of iopro, 1.5.0, was not built against numpy 1.5
    for alg in ['sorter', 'BDD']: #, 'BDD_recursive']:
        assert r.solve2(['iopro', 'python 2.7*', 'numpy 1.5*'], set(),
            alg=alg, returnall=True) == [[
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
        ]]

    for alg in ['sorter', 'BDD']: #, 'BDD_recursive']:
        assert r.solve2(['iopro', 'python 2.7*', 'numpy 1.5*'], f_mkl,
            alg=alg, returnall=True) == [[
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
        ]]

def test_get_dists():
    r.msd_cache = {}
    dists = r.get_dists(["anaconda 1.5.0"])
    assert 'anaconda-1.5.0-np17py27_0.tar.bz2' in dists
    assert 'dynd-python-0.3.0-np17py33_0.tar.bz2' in dists
    for d in dists:
        assert dists[d].fn == d

def test_generate_eq():
    r.msd_cache = {}

    specs = ['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*']
    dists = r.get_dists(specs)
    v = {}
    w = {}
    for i, fn in enumerate(sorted(dists)):
        v[fn] = i + 1
        w[i + 1] = fn

    eq, max_rhs = r.generate_version_eq(v, dists, [], specs, include0=True)
    e = [(i, w[j]) for i, j in eq]
    # Should satisfy the following criteria:
    # - lower versions of the same package should should have higher
    #   coefficients.
    # - the same versions of the same package (e.g., different build strings)
    #   should have the same coefficients.
    # - a package that only has one version should not appear, unless
    #   include=True as it will have a 0 coefficient. The same is true of the
    #   latest version of a package.
    assert e == [
        (0, u'_license-1.1-py27_0.tar.bz2'),
        (0, u'anaconda-1.5.0-np16py26_0.tar.bz2'),
        (0, u'anaconda-1.5.0-np16py27_0.tar.bz2'),
        (0, u'anaconda-1.5.0-np17py26_0.tar.bz2'),
        (0, u'anaconda-1.5.0-np17py27_0.tar.bz2'),
        (0, u'anaconda-1.5.0-np17py33_0.tar.bz2'),
        (0, u'argparse-1.2.1-py26_0.tar.bz2'),
        (0, u'astropy-0.2.1-np16py26_0.tar.bz2'),
        (0, u'astropy-0.2.1-np16py27_0.tar.bz2'),
        (0, u'astropy-0.2.1-np17py26_0.tar.bz2'),
        (0, u'astropy-0.2.1-np17py27_0.tar.bz2'),
        (0, u'astropy-0.2.1-np17py33_0.tar.bz2'),
        (0, u'atom-0.2.3-py26_0.tar.bz2'),
        (0, u'atom-0.2.3-py27_0.tar.bz2'),
        (0, u'biopython-1.61-np16py26_0.tar.bz2'),
        (0, u'biopython-1.61-np16py27_0.tar.bz2'),
        (0, u'biopython-1.61-np17py26_0.tar.bz2'),
        (0, u'biopython-1.61-np17py27_0.tar.bz2'),
        (0, u'bitarray-0.8.1-py26_0.tar.bz2'),
        (0, u'bitarray-0.8.1-py27_0.tar.bz2'),
        (0, u'bitarray-0.8.1-py33_0.tar.bz2'),
        (0, u'boto-2.9.2-py26_0.tar.bz2'),
        (0, u'boto-2.9.2-py27_0.tar.bz2'),
        (0, u'cairo-1.12.2-1.tar.bz2'),
        (1, u'cairo-1.12.2-0.tar.bz2'),
        (0, u'casuarius-1.1-py26_0.tar.bz2'),
        (0, u'casuarius-1.1-py27_0.tar.bz2'),
        (0, u'conda-1.5.2-py27_0.tar.bz2'),
        (0, u'cubes-0.10.2-py27_1.tar.bz2'),
        (0, u'curl-7.30.0-0.tar.bz2'),
        (0, u'cython-0.19-py26_0.tar.bz2'),
        (0, u'cython-0.19-py27_0.tar.bz2'),
        (0, u'cython-0.19-py33_0.tar.bz2'),
        (0, u'dateutil-2.1-py26_1.tar.bz2'),
        (0, u'dateutil-2.1-py27_1.tar.bz2'),
        (0, u'dateutil-2.1-py33_1.tar.bz2'),
        (1, u'dateutil-2.1-py26_0.tar.bz2'),
        (1, u'dateutil-2.1-py27_0.tar.bz2'),
        (1, u'dateutil-2.1-py33_0.tar.bz2'),
        (2, u'dateutil-1.5-py26_0.tar.bz2'),
        (2, u'dateutil-1.5-py27_0.tar.bz2'),
        (2, u'dateutil-1.5-py33_0.tar.bz2'),
        (0, u'disco-0.4.4-py26_0.tar.bz2'),
        (0, u'disco-0.4.4-py27_0.tar.bz2'),
        (0, u'distribute-0.6.36-py26_1.tar.bz2'),
        (0, u'distribute-0.6.36-py27_1.tar.bz2'),
        (0, u'distribute-0.6.36-py33_1.tar.bz2'),
        (1, u'distribute-0.6.34-py26_1.tar.bz2'),
        (1, u'distribute-0.6.34-py27_1.tar.bz2'),
        (1, u'distribute-0.6.34-py33_1.tar.bz2'),
        (2, u'distribute-0.6.34-py26_0.tar.bz2'),
        (2, u'distribute-0.6.34-py27_0.tar.bz2'),
        (3, u'distribute-0.6.30-py26_0.tar.bz2'),
        (3, u'distribute-0.6.30-py27_0.tar.bz2'),
        (3, u'distribute-0.6.30-py33_0.tar.bz2'),
        (0, u'docutils-0.10-py26_0.tar.bz2'),
        (0, u'docutils-0.10-py27_0.tar.bz2'),
        (0, u'docutils-0.10-py33_0.tar.bz2'),
        (1, u'docutils-0.9.1-py26_1.tar.bz2'),
        (1, u'docutils-0.9.1-py27_1.tar.bz2'),
        (2, u'docutils-0.9.1-py26_0.tar.bz2'),
        (2, u'docutils-0.9.1-py27_0.tar.bz2'),
        (0, u'dynd-python-0.3.0-np17py26_0.tar.bz2'),
        (0, u'dynd-python-0.3.0-np17py27_0.tar.bz2'),
        (0, u'dynd-python-0.3.0-np17py33_0.tar.bz2'),
        (0, u'enaml-0.7.6-py27_0.tar.bz2'),
        (0, u'erlang-R15B01-0.tar.bz2'),
        (0, u'flask-0.9-py26_0.tar.bz2'),
        (0, u'flask-0.9-py27_0.tar.bz2'),
        (0, u'freetype-2.4.10-0.tar.bz2'),
        (0, u'gevent-0.13.8-py26_0.tar.bz2'),
        (0, u'gevent-0.13.8-py27_0.tar.bz2'),
        (0, u'gevent-websocket-0.3.6-py26_2.tar.bz2'),
        (0, u'gevent-websocket-0.3.6-py27_2.tar.bz2'),
        (0, u'gevent_zeromq-0.2.5-py26_2.tar.bz2'),
        (0, u'gevent_zeromq-0.2.5-py27_2.tar.bz2'),
        (0, u'greenlet-0.4.0-py26_0.tar.bz2'),
        (0, u'greenlet-0.4.0-py27_0.tar.bz2'),
        (0, u'greenlet-0.4.0-py33_0.tar.bz2'),
        (0, u'grin-1.2.1-py26_1.tar.bz2'),
        (0, u'grin-1.2.1-py27_1.tar.bz2'),
        (0, u'h5py-2.1.1-np16py26_0.tar.bz2'),
        (0, u'h5py-2.1.1-np16py27_0.tar.bz2'),
        (0, u'h5py-2.1.1-np17py26_0.tar.bz2'),
        (0, u'h5py-2.1.1-np17py27_0.tar.bz2'),
        (0, u'hdf5-1.8.9-0.tar.bz2'),
        (0, u'imaging-1.1.7-py26_2.tar.bz2'),
        (0, u'imaging-1.1.7-py27_2.tar.bz2'),
        (0, u'ipython-0.13.2-py26_0.tar.bz2'),
        (0, u'ipython-0.13.2-py27_0.tar.bz2'),
        (0, u'ipython-0.13.2-py33_0.tar.bz2'),
        (0, u'jinja2-2.6-py26_0.tar.bz2'),
        (0, u'jinja2-2.6-py27_0.tar.bz2'),
        (0, u'jinja2-2.6-py33_0.tar.bz2'),
        (0, u'jpeg-8d-0.tar.bz2'),
        (0, u'libdynd-0.3.0-0.tar.bz2'),
        (0, u'libevent-2.0.20-0.tar.bz2'),
        (0, u'libnetcdf-4.2.1.1-1.tar.bz2'),
        (1, u'libnetcdf-4.2.1.1-0.tar.bz2'),
        (0, u'libpng-1.5.13-1.tar.bz2'),
        (1, u'libpng-1.5.13-0.tar.bz2'),
        (0, u'libxml2-2.9.0-0.tar.bz2'),
        (0, u'libxslt-1.1.28-0.tar.bz2'),
        (0, u'llvm-3.2-0.tar.bz2'),
        (0, u'llvmpy-0.11.2-py26_0.tar.bz2'),
        (0, u'llvmpy-0.11.2-py27_0.tar.bz2'),
        (0, u'llvmpy-0.11.2-py33_0.tar.bz2'),
        (0, u'lxml-3.2.0-py26_0.tar.bz2'),
        (0, u'lxml-3.2.0-py27_0.tar.bz2'),
        (0, u'lxml-3.2.0-py33_0.tar.bz2'),
        (0, u'matplotlib-1.2.1-np16py26_1.tar.bz2'),
        (0, u'matplotlib-1.2.1-np16py27_1.tar.bz2'),
        (0, u'matplotlib-1.2.1-np17py26_1.tar.bz2'),
        (0, u'matplotlib-1.2.1-np17py27_1.tar.bz2'),
        (0, u'matplotlib-1.2.1-np17py33_1.tar.bz2'),
        (0, u'mdp-3.3-np16py26_0.tar.bz2'),
        (0, u'mdp-3.3-np16py27_0.tar.bz2'),
        (0, u'mdp-3.3-np17py26_0.tar.bz2'),
        (0, u'mdp-3.3-np17py27_0.tar.bz2'),
        (0, u'mdp-3.3-np17py33_0.tar.bz2'),
        (0, u'meta-0.4.2.dev-py26_0.tar.bz2'),
        (0, u'meta-0.4.2.dev-py27_0.tar.bz2'),
        (0, u'meta-0.4.2.dev-py33_0.tar.bz2'),
        (0, u'mkl-10.3-p2.tar.bz2'),
        (1, u'mkl-10.3-p1.tar.bz2'),
        (2, u'mkl-10.3-0.tar.bz2'),
        (0, u'mkl-rt-11.0-p0.tar.bz2'),
        (0, u'mpi4py-1.3-py26_0.tar.bz2'),
        (0, u'mpi4py-1.3-py27_0.tar.bz2'),
        (0, u'mpich2-1.4.1p1-0.tar.bz2'),
        (0, u'netcdf4-1.0.4-np16py26_0.tar.bz2'),
        (0, u'netcdf4-1.0.4-np16py27_0.tar.bz2'),
        (0, u'netcdf4-1.0.4-np17py26_0.tar.bz2'),
        (0, u'netcdf4-1.0.4-np17py27_0.tar.bz2'),
        (0, u'netcdf4-1.0.4-np17py33_0.tar.bz2'),
        (0, u'networkx-1.7-py26_0.tar.bz2'),
        (0, u'networkx-1.7-py27_0.tar.bz2'),
        (0, u'networkx-1.7-py33_0.tar.bz2'),
        (0, u'nltk-2.0.4-np16py26_0.tar.bz2'),
        (0, u'nltk-2.0.4-np16py27_0.tar.bz2'),
        (0, u'nltk-2.0.4-np17py26_0.tar.bz2'),
        (0, u'nltk-2.0.4-np17py27_0.tar.bz2'),
        (0, u'nose-1.3.0-py26_0.tar.bz2'),
        (0, u'nose-1.3.0-py27_0.tar.bz2'),
        (0, u'nose-1.3.0-py33_0.tar.bz2'),
        (1, u'nose-1.2.1-py26_0.tar.bz2'),
        (1, u'nose-1.2.1-py27_0.tar.bz2'),
        (1, u'nose-1.2.1-py33_0.tar.bz2'),
        (2, u'nose-1.1.2-py26_0.tar.bz2'),
        (2, u'nose-1.1.2-py27_0.tar.bz2'),
        (2, u'nose-1.1.2-py33_0.tar.bz2'),
        (0, u'numba-0.8.1-np16py26_0.tar.bz2'),
        (0, u'numba-0.8.1-np16py27_0.tar.bz2'),
        (0, u'numba-0.8.1-np17py26_0.tar.bz2'),
        (0, u'numba-0.8.1-np17py27_0.tar.bz2'),
        (0, u'numba-0.8.1-np17py33_0.tar.bz2'),
        (0, u'numexpr-2.0.1-np16py26_3.tar.bz2'),
        (0, u'numexpr-2.0.1-np16py26_p3.tar.bz2'),
        (0, u'numexpr-2.0.1-np16py27_3.tar.bz2'),
        (0, u'numexpr-2.0.1-np16py27_p3.tar.bz2'),
        (0, u'numexpr-2.0.1-np17py26_3.tar.bz2'),
        (0, u'numexpr-2.0.1-np17py26_p3.tar.bz2'),
        (0, u'numexpr-2.0.1-np17py27_3.tar.bz2'),
        (0, u'numexpr-2.0.1-np17py27_p3.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py26_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py26_p2.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py27_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py27_p2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py26_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py26_p2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py27_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py27_p2.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py26_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py26_p1.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py27_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py27_p1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py26_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py26_p1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py27_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py27_p1.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py26_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py26_pro0.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py27_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py27_pro0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py26_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py26_pro0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py27_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py27_pro0.tar.bz2'),
        (0, u'numpy-1.7.1-py26_0.tar.bz2'),
        (0, u'numpy-1.7.1-py26_p0.tar.bz2'),
        (0, u'numpy-1.7.1-py27_0.tar.bz2'),
        (0, u'numpy-1.7.1-py27_p0.tar.bz2'),
        (0, u'numpy-1.7.1-py33_0.tar.bz2'),
        (0, u'numpy-1.7.1-py33_p0.tar.bz2'),
        (1, u'numpy-1.7.0-py26_0.tar.bz2'),
        (1, u'numpy-1.7.0-py26_p0.tar.bz2'),
        (1, u'numpy-1.7.0-py27_0.tar.bz2'),
        (1, u'numpy-1.7.0-py27_p0.tar.bz2'),
        (1, u'numpy-1.7.0-py33_0.tar.bz2'),
        (1, u'numpy-1.7.0-py33_p0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py26_0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py26_p0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py27_0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py27_p0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py33_0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py33_p0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py26_ce0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py26_pro0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py27_ce0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py27_pro0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py33_pro0.tar.bz2'),
        (4, u'numpy-1.6.2-py26_4.tar.bz2'),
        (4, u'numpy-1.6.2-py26_p4.tar.bz2'),
        (4, u'numpy-1.6.2-py27_4.tar.bz2'),
        (4, u'numpy-1.6.2-py27_p4.tar.bz2'),
        (5, u'numpy-1.6.2-py26_3.tar.bz2'),
        (5, u'numpy-1.6.2-py26_p3.tar.bz2'),
        (5, u'numpy-1.6.2-py27_3.tar.bz2'),
        (5, u'numpy-1.6.2-py27_p3.tar.bz2'),
        (6, u'numpy-1.6.2-py26_1.tar.bz2'),
        (6, u'numpy-1.6.2-py26_p1.tar.bz2'),
        (6, u'numpy-1.6.2-py27_1.tar.bz2'),
        (6, u'numpy-1.6.2-py27_p1.tar.bz2'),
        (7, u'numpy-1.6.2-py26_ce0.tar.bz2'),
        (7, u'numpy-1.6.2-py26_pro0.tar.bz2'),
        (7, u'numpy-1.6.2-py27_ce0.tar.bz2'),
        (7, u'numpy-1.6.2-py27_pro0.tar.bz2'),
        (8, u'numpy-1.5.1-py26_4.tar.bz2'),
        (8, u'numpy-1.5.1-py26_p4.tar.bz2'),
        (8, u'numpy-1.5.1-py27_4.tar.bz2'),
        (8, u'numpy-1.5.1-py27_p4.tar.bz2'),
        (9, u'numpy-1.5.1-py26_3.tar.bz2'),
        (9, u'numpy-1.5.1-py26_p3.tar.bz2'),
        (9, u'numpy-1.5.1-py27_3.tar.bz2'),
        (9, u'numpy-1.5.1-py27_p3.tar.bz2'),
        (10, u'numpy-1.5.1-py26_1.tar.bz2'),
        (10, u'numpy-1.5.1-py26_p1.tar.bz2'),
        (10, u'numpy-1.5.1-py27_1.tar.bz2'),
        (10, u'numpy-1.5.1-py27_p1.tar.bz2'),
        (11, u'numpy-1.5.1-py26_ce0.tar.bz2'),
        (11, u'numpy-1.5.1-py26_pro0.tar.bz2'),
        (11, u'numpy-1.5.1-py27_ce0.tar.bz2'),
        (11, u'numpy-1.5.1-py27_pro0.tar.bz2'),
        (0, u'opencv-2.4.2-np16py26_1.tar.bz2'),
        (0, u'opencv-2.4.2-np16py27_1.tar.bz2'),
        (0, u'opencv-2.4.2-np17py26_1.tar.bz2'),
        (0, u'opencv-2.4.2-np17py27_1.tar.bz2'),
        (0, u'openssl-1.0.1c-0.tar.bz2'),
        (0, u'ordereddict-1.1-py26_0.tar.bz2'),
        (0, u'pandas-0.11.0-np16py26_1.tar.bz2'),
        (0, u'pandas-0.11.0-np16py27_1.tar.bz2'),
        (0, u'pandas-0.11.0-np17py26_1.tar.bz2'),
        (0, u'pandas-0.11.0-np17py27_1.tar.bz2'),
        (0, u'pandas-0.11.0-np17py33_1.tar.bz2'),
        (1, u'pandas-0.10.1-np16py26_0.tar.bz2'),
        (1, u'pandas-0.10.1-np16py27_0.tar.bz2'),
        (1, u'pandas-0.10.1-np17py26_0.tar.bz2'),
        (1, u'pandas-0.10.1-np17py27_0.tar.bz2'),
        (1, u'pandas-0.10.1-np17py33_0.tar.bz2'),
        (2, u'pandas-0.10.0-np16py26_0.tar.bz2'),
        (2, u'pandas-0.10.0-np16py27_0.tar.bz2'),
        (2, u'pandas-0.10.0-np17py26_0.tar.bz2'),
        (2, u'pandas-0.10.0-np17py27_0.tar.bz2'),
        (3, u'pandas-0.9.1-np16py26_0.tar.bz2'),
        (3, u'pandas-0.9.1-np16py27_0.tar.bz2'),
        (3, u'pandas-0.9.1-np17py26_0.tar.bz2'),
        (3, u'pandas-0.9.1-np17py27_0.tar.bz2'),
        (4, u'pandas-0.9.0-np16py26_0.tar.bz2'),
        (4, u'pandas-0.9.0-np16py27_0.tar.bz2'),
        (4, u'pandas-0.9.0-np17py26_0.tar.bz2'),
        (4, u'pandas-0.9.0-np17py27_0.tar.bz2'),
        (5, u'pandas-0.8.1-np16py26_0.tar.bz2'),
        (5, u'pandas-0.8.1-np16py27_0.tar.bz2'),
        (5, u'pandas-0.8.1-np17py26_0.tar.bz2'),
        (5, u'pandas-0.8.1-np17py27_0.tar.bz2'),
        (0, u'pip-1.3.1-py26_1.tar.bz2'),
        (0, u'pip-1.3.1-py27_1.tar.bz2'),
        (0, u'pip-1.3.1-py33_1.tar.bz2'),
        (0, u'pixman-0.26.2-0.tar.bz2'),
        (0, u'ply-3.4-py26_0.tar.bz2'),
        (0, u'ply-3.4-py27_0.tar.bz2'),
        (0, u'ply-3.4-py33_0.tar.bz2'),
        (0, u'psutil-0.7.1-py26_0.tar.bz2'),
        (0, u'psutil-0.7.1-py27_0.tar.bz2'),
        (0, u'psutil-0.7.1-py33_0.tar.bz2'),
        (0, u'py-1.4.12-py26_0.tar.bz2'),
        (0, u'py-1.4.12-py27_0.tar.bz2'),
        (0, u'py-1.4.12-py33_0.tar.bz2'),
        (0, u'py2cairo-1.10.0-py26_1.tar.bz2'),
        (0, u'py2cairo-1.10.0-py27_1.tar.bz2'),
        (1, u'py2cairo-1.10.0-py26_0.tar.bz2'),
        (1, u'py2cairo-1.10.0-py27_0.tar.bz2'),
        (0, u'pycosat-0.6.0-py26_0.tar.bz2'),
        (0, u'pycosat-0.6.0-py27_0.tar.bz2'),
        (0, u'pycosat-0.6.0-py33_0.tar.bz2'),
        (0, u'pycparser-2.9.1-py26_0.tar.bz2'),
        (0, u'pycparser-2.9.1-py27_0.tar.bz2'),
        (0, u'pycparser-2.9.1-py33_0.tar.bz2'),
        (0, u'pycrypto-2.6-py26_0.tar.bz2'),
        (0, u'pycrypto-2.6-py27_0.tar.bz2'),
        (0, u'pycrypto-2.6-py33_0.tar.bz2'),
        (0, u'pycurl-7.19.0-py26_2.tar.bz2'),
        (0, u'pycurl-7.19.0-py27_2.tar.bz2'),
        (0, u'pyflakes-0.7.2-py26_0.tar.bz2'),
        (0, u'pyflakes-0.7.2-py27_0.tar.bz2'),
        (0, u'pyflakes-0.7.2-py33_0.tar.bz2'),
        (0, u'pygments-1.6-py26_0.tar.bz2'),
        (0, u'pygments-1.6-py27_0.tar.bz2'),
        (0, u'pygments-1.6-py33_0.tar.bz2'),
        (0, u'pyparsing-1.5.6-py26_0.tar.bz2'),
        (0, u'pyparsing-1.5.6-py27_0.tar.bz2'),
        (0, u'pysal-1.5.0-np16py27_1.tar.bz2'),
        (0, u'pysal-1.5.0-np17py27_1.tar.bz2'),
        (0, u'pysam-0.6-py26_0.tar.bz2'),
        (0, u'pysam-0.6-py27_0.tar.bz2'),
        (0, u'pyside-1.1.2-py26_0.tar.bz2'),
        (0, u'pyside-1.1.2-py27_0.tar.bz2'),
        (0, u'pytables-2.4.0-np16py26_0.tar.bz2'),
        (0, u'pytables-2.4.0-np16py27_0.tar.bz2'),
        (0, u'pytables-2.4.0-np17py26_0.tar.bz2'),
        (0, u'pytables-2.4.0-np17py27_0.tar.bz2'),
        (0, u'pytest-2.3.4-py26_1.tar.bz2'),
        (0, u'pytest-2.3.4-py27_1.tar.bz2'),
        (0, u'python-3.3.2-0.tar.bz2'),
        (1, u'python-3.3.1-0.tar.bz2'),
        (2, u'python-3.3.0-4.tar.bz2'),
        (3, u'python-3.3.0-3.tar.bz2'),
        (4, u'python-3.3.0-2.tar.bz2'),
        (5, u'python-3.3.0-pro1.tar.bz2'),
        (6, u'python-3.3.0-pro0.tar.bz2'),
        (7, u'python-2.7.5-0.tar.bz2'),
        (8, u'python-2.7.4-0.tar.bz2'),
        (9, u'python-2.7.3-7.tar.bz2'),
        (10, u'python-2.7.3-6.tar.bz2'),
        (11, u'python-2.7.3-5.tar.bz2'),
        (12, u'python-2.7.3-4.tar.bz2'),
        (13, u'python-2.7.3-3.tar.bz2'),
        (14, u'python-2.7.3-2.tar.bz2'),
        (15, u'python-2.6.8-6.tar.bz2'),
        (16, u'python-2.6.8-5.tar.bz2'),
        (17, u'python-2.6.8-4.tar.bz2'),
        (18, u'python-2.6.8-3.tar.bz2'),
        (19, u'python-2.6.8-2.tar.bz2'),
        (20, u'python-2.6.8-1.tar.bz2'),
        (0, u'pytz-2013b-py26_0.tar.bz2'),
        (0, u'pytz-2013b-py27_0.tar.bz2'),
        (0, u'pytz-2013b-py33_0.tar.bz2'),
        (1, u'pytz-2012j-py26_0.tar.bz2'),
        (1, u'pytz-2012j-py27_0.tar.bz2'),
        (1, u'pytz-2012j-py33_0.tar.bz2'),
        (2, u'pytz-2012d-py26_0.tar.bz2'),
        (2, u'pytz-2012d-py27_0.tar.bz2'),
        (2, u'pytz-2012d-py33_0.tar.bz2'),
        (0, u'pyyaml-3.10-py26_0.tar.bz2'),
        (0, u'pyyaml-3.10-py27_0.tar.bz2'),
        (0, u'pyyaml-3.10-py33_0.tar.bz2'),
        (0, u'pyzmq-2.2.0.1-py26_1.tar.bz2'),
        (0, u'pyzmq-2.2.0.1-py27_1.tar.bz2'),
        (0, u'pyzmq-2.2.0.1-py33_1.tar.bz2'),
        (1, u'pyzmq-2.2.0.1-py26_0.tar.bz2'),
        (1, u'pyzmq-2.2.0.1-py27_0.tar.bz2'),
        (1, u'pyzmq-2.2.0.1-py33_0.tar.bz2'),
        (0, u'qt-4.7.4-0.tar.bz2'),
        (0, u'readline-6.2-0.tar.bz2'),
        (0, u'redis-2.6.9-0.tar.bz2'),
        (0, u'redis-py-2.7.2-py26_0.tar.bz2'),
        (0, u'redis-py-2.7.2-py27_0.tar.bz2'),
        (0, u'requests-1.2.0-py26_0.tar.bz2'),
        (0, u'requests-1.2.0-py27_0.tar.bz2'),
        (0, u'requests-1.2.0-py33_0.tar.bz2'),
        (0, u'rope-0.9.4-py27_0.tar.bz2'),
        (0, u'scikit-image-0.8.2-np16py26_1.tar.bz2'),
        (0, u'scikit-image-0.8.2-np16py27_1.tar.bz2'),
        (0, u'scikit-image-0.8.2-np17py26_1.tar.bz2'),
        (0, u'scikit-image-0.8.2-np17py27_1.tar.bz2'),
        (0, u'scikit-image-0.8.2-np17py33_1.tar.bz2'),
        (0, u'scikit-learn-0.13.1-np16py26_0.tar.bz2'),
        (0, u'scikit-learn-0.13.1-np16py27_0.tar.bz2'),
        (0, u'scikit-learn-0.13.1-np17py26_0.tar.bz2'),
        (0, u'scikit-learn-0.13.1-np17py27_0.tar.bz2'),
        (0, u'scipy-0.12.0-np15py26_0.tar.bz2'),
        (0, u'scipy-0.12.0-np15py26_p0.tar.bz2'),
        (0, u'scipy-0.12.0-np15py27_0.tar.bz2'),
        (0, u'scipy-0.12.0-np15py27_p0.tar.bz2'),
        (0, u'scipy-0.12.0-np16py26_0.tar.bz2'),
        (0, u'scipy-0.12.0-np16py26_p0.tar.bz2'),
        (0, u'scipy-0.12.0-np16py27_0.tar.bz2'),
        (0, u'scipy-0.12.0-np16py27_p0.tar.bz2'),
        (0, u'scipy-0.12.0-np17py26_0.tar.bz2'),
        (0, u'scipy-0.12.0-np17py26_p0.tar.bz2'),
        (0, u'scipy-0.12.0-np17py27_0.tar.bz2'),
        (0, u'scipy-0.12.0-np17py27_p0.tar.bz2'),
        (0, u'scipy-0.12.0-np17py33_0.tar.bz2'),
        (0, u'scipy-0.12.0-np17py33_p0.tar.bz2'),
        (1, u'scipy-0.11.0-np15py26_3.tar.bz2'),
        (1, u'scipy-0.11.0-np15py26_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np15py27_3.tar.bz2'),
        (1, u'scipy-0.11.0-np15py27_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py26_3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py26_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py27_3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py27_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py26_3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py26_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py27_3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py27_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py33_3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py33_p3.tar.bz2'),
        (2, u'scipy-0.11.0-np15py26_2.tar.bz2'),
        (2, u'scipy-0.11.0-np15py26_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np15py27_2.tar.bz2'),
        (2, u'scipy-0.11.0-np15py27_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py26_2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py26_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py27_2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py27_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py26_2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py26_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py27_2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py27_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py33_2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py33_p2.tar.bz2'),
        (3, u'scipy-0.11.0-np15py26_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np15py26_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np15py27_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np15py27_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py26_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py26_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py27_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py27_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py26_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py26_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py27_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py27_pro1.tar.bz2'),
        (4, u'scipy-0.11.0-np15py26_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np15py27_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np16py26_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np16py27_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np17py26_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np17py27_ce0.tar.bz2'),
        (4, u'scipy-0.11.0-np17py27_pro0.tar.bz2'),
        (0, u'shiboken-1.1.2-py26_0.tar.bz2'),
        (0, u'shiboken-1.1.2-py27_0.tar.bz2'),
        (0, u'six-1.3.0-py26_0.tar.bz2'),
        (0, u'six-1.3.0-py27_0.tar.bz2'),
        (0, u'six-1.3.0-py33_0.tar.bz2'),
        (1, u'six-1.2.0-py26_0.tar.bz2'),
        (1, u'six-1.2.0-py27_0.tar.bz2'),
        (1, u'six-1.2.0-py33_0.tar.bz2'),
        (0, u'sphinx-1.1.3-py26_3.tar.bz2'),
        (0, u'sphinx-1.1.3-py27_3.tar.bz2'),
        (0, u'sphinx-1.1.3-py33_3.tar.bz2'),
        (0, u'spyder-2.2.0-py27_0.tar.bz2'),
        (0, u'sqlalchemy-0.8.1-py26_0.tar.bz2'),
        (0, u'sqlalchemy-0.8.1-py27_0.tar.bz2'),
        (0, u'sqlalchemy-0.8.1-py33_0.tar.bz2'),
        (0, u'sqlite-3.7.13-0.tar.bz2'),
        (0, u'statsmodels-0.4.3-np16py26_1.tar.bz2'),
        (0, u'statsmodels-0.4.3-np16py27_1.tar.bz2'),
        (0, u'statsmodels-0.4.3-np17py26_1.tar.bz2'),
        (0, u'statsmodels-0.4.3-np17py27_1.tar.bz2'),
        (0, u'sympy-0.7.2-py26_0.tar.bz2'),
        (0, u'sympy-0.7.2-py27_0.tar.bz2'),
        (0, u'sympy-0.7.2-py33_0.tar.bz2'),
        (0, u'system-5.8-1.tar.bz2'),
        (1, u'system-5.8-0.tar.bz2'),
        (0, u'theano-0.5.0-np16py26_1.tar.bz2'),
        (0, u'theano-0.5.0-np16py27_1.tar.bz2'),
        (0, u'theano-0.5.0-np17py26_1.tar.bz2'),
        (0, u'theano-0.5.0-np17py27_1.tar.bz2'),
        (0, u'tk-8.5.13-0.tar.bz2'),
        (0, u'tornado-3.0.1-py26_0.tar.bz2'),
        (0, u'tornado-3.0.1-py27_0.tar.bz2'),
        (0, u'tornado-3.0.1-py33_0.tar.bz2'),
        (0, u'util-linux-2.21-0.tar.bz2'),
        (0, u'werkzeug-0.8.3-py26_0.tar.bz2'),
        (0, u'werkzeug-0.8.3-py27_0.tar.bz2'),
        (0, u'xlrd-0.9.2-py26_0.tar.bz2'),
        (0, u'xlrd-0.9.2-py27_0.tar.bz2'),
        (0, u'xlrd-0.9.2-py33_0.tar.bz2'),
        (0, u'xlwt-0.7.5-py26_0.tar.bz2'),
        (0, u'xlwt-0.7.5-py27_0.tar.bz2'),
        (0, u'yaml-0.1.4-0.tar.bz2'),
        (0, u'zeromq-2.2.0-1.tar.bz2'),
        (1, u'zeromq-2.2.0-0.tar.bz2'),
        (0, u'zlib-1.2.7-0.tar.bz2')
    ]

    assert max_rhs == 1 + 2 + 3 + 2 + 1 + 1 + 2 + 2 + 3 + 11 + 5 + 1 + 20 + 2 + 1 + 4 + 1 + 1 + 1

    eq, max_rhs = r.generate_version_eq(v, dists, [], specs)
    assert all(i > 0 for i, _ in eq)
    e = [(i, w[j]) for i, j in eq]

    assert e == [
        (1, u'cairo-1.12.2-0.tar.bz2'),
        (1, u'dateutil-2.1-py26_0.tar.bz2'),
        (1, u'dateutil-2.1-py27_0.tar.bz2'),
        (1, u'dateutil-2.1-py33_0.tar.bz2'),
        (2, u'dateutil-1.5-py26_0.tar.bz2'),
        (2, u'dateutil-1.5-py27_0.tar.bz2'),
        (2, u'dateutil-1.5-py33_0.tar.bz2'),
        (1, u'distribute-0.6.34-py26_1.tar.bz2'),
        (1, u'distribute-0.6.34-py27_1.tar.bz2'),
        (1, u'distribute-0.6.34-py33_1.tar.bz2'),
        (2, u'distribute-0.6.34-py26_0.tar.bz2'),
        (2, u'distribute-0.6.34-py27_0.tar.bz2'),
        (3, u'distribute-0.6.30-py26_0.tar.bz2'),
        (3, u'distribute-0.6.30-py27_0.tar.bz2'),
        (3, u'distribute-0.6.30-py33_0.tar.bz2'),
        (1, u'docutils-0.9.1-py26_1.tar.bz2'),
        (1, u'docutils-0.9.1-py27_1.tar.bz2'),
        (2, u'docutils-0.9.1-py26_0.tar.bz2'),
        (2, u'docutils-0.9.1-py27_0.tar.bz2'),
        (1, u'libnetcdf-4.2.1.1-0.tar.bz2'),
        (1, u'libpng-1.5.13-0.tar.bz2'),
        (1, u'mkl-10.3-p1.tar.bz2'),
        (2, u'mkl-10.3-0.tar.bz2'),
        (1, u'nose-1.2.1-py26_0.tar.bz2'),
        (1, u'nose-1.2.1-py27_0.tar.bz2'),
        (1, u'nose-1.2.1-py33_0.tar.bz2'),
        (2, u'nose-1.1.2-py26_0.tar.bz2'),
        (2, u'nose-1.1.2-py27_0.tar.bz2'),
        (2, u'nose-1.1.2-py33_0.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py26_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py26_p2.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py27_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np16py27_p2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py26_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py26_p2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py27_2.tar.bz2'),
        (1, u'numexpr-2.0.1-np17py27_p2.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py26_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py26_p1.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py27_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np16py27_p1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py26_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py26_p1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py27_1.tar.bz2'),
        (2, u'numexpr-2.0.1-np17py27_p1.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py26_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py26_pro0.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py27_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np16py27_pro0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py26_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py26_pro0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py27_ce0.tar.bz2'),
        (3, u'numexpr-2.0.1-np17py27_pro0.tar.bz2'),
        (1, u'numpy-1.7.0-py26_0.tar.bz2'),
        (1, u'numpy-1.7.0-py26_p0.tar.bz2'),
        (1, u'numpy-1.7.0-py27_0.tar.bz2'),
        (1, u'numpy-1.7.0-py27_p0.tar.bz2'),
        (1, u'numpy-1.7.0-py33_0.tar.bz2'),
        (1, u'numpy-1.7.0-py33_p0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py26_0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py26_p0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py27_0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py27_p0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py33_0.tar.bz2'),
        (2, u'numpy-1.7.0rc1-py33_p0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py26_ce0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py26_pro0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py27_ce0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py27_pro0.tar.bz2'),
        (3, u'numpy-1.7.0b2-py33_pro0.tar.bz2'),
        (4, u'numpy-1.6.2-py26_4.tar.bz2'),
        (4, u'numpy-1.6.2-py26_p4.tar.bz2'),
        (4, u'numpy-1.6.2-py27_4.tar.bz2'),
        (4, u'numpy-1.6.2-py27_p4.tar.bz2'),
        (5, u'numpy-1.6.2-py26_3.tar.bz2'),
        (5, u'numpy-1.6.2-py26_p3.tar.bz2'),
        (5, u'numpy-1.6.2-py27_3.tar.bz2'),
        (5, u'numpy-1.6.2-py27_p3.tar.bz2'),
        (6, u'numpy-1.6.2-py26_1.tar.bz2'),
        (6, u'numpy-1.6.2-py26_p1.tar.bz2'),
        (6, u'numpy-1.6.2-py27_1.tar.bz2'),
        (6, u'numpy-1.6.2-py27_p1.tar.bz2'),
        (7, u'numpy-1.6.2-py26_ce0.tar.bz2'),
        (7, u'numpy-1.6.2-py26_pro0.tar.bz2'),
        (7, u'numpy-1.6.2-py27_ce0.tar.bz2'),
        (7, u'numpy-1.6.2-py27_pro0.tar.bz2'),
        (8, u'numpy-1.5.1-py26_4.tar.bz2'),
        (8, u'numpy-1.5.1-py26_p4.tar.bz2'),
        (8, u'numpy-1.5.1-py27_4.tar.bz2'),
        (8, u'numpy-1.5.1-py27_p4.tar.bz2'),
        (9, u'numpy-1.5.1-py26_3.tar.bz2'),
        (9, u'numpy-1.5.1-py26_p3.tar.bz2'),
        (9, u'numpy-1.5.1-py27_3.tar.bz2'),
        (9, u'numpy-1.5.1-py27_p3.tar.bz2'),
        (10, u'numpy-1.5.1-py26_1.tar.bz2'),
        (10, u'numpy-1.5.1-py26_p1.tar.bz2'),
        (10, u'numpy-1.5.1-py27_1.tar.bz2'),
        (10, u'numpy-1.5.1-py27_p1.tar.bz2'),
        (11, u'numpy-1.5.1-py26_ce0.tar.bz2'),
        (11, u'numpy-1.5.1-py26_pro0.tar.bz2'),
        (11, u'numpy-1.5.1-py27_ce0.tar.bz2'),
        (11, u'numpy-1.5.1-py27_pro0.tar.bz2'),
        (1, u'pandas-0.10.1-np16py26_0.tar.bz2'),
        (1, u'pandas-0.10.1-np16py27_0.tar.bz2'),
        (1, u'pandas-0.10.1-np17py26_0.tar.bz2'),
        (1, u'pandas-0.10.1-np17py27_0.tar.bz2'),
        (1, u'pandas-0.10.1-np17py33_0.tar.bz2'),
        (2, u'pandas-0.10.0-np16py26_0.tar.bz2'),
        (2, u'pandas-0.10.0-np16py27_0.tar.bz2'),
        (2, u'pandas-0.10.0-np17py26_0.tar.bz2'),
        (2, u'pandas-0.10.0-np17py27_0.tar.bz2'),
        (3, u'pandas-0.9.1-np16py26_0.tar.bz2'),
        (3, u'pandas-0.9.1-np16py27_0.tar.bz2'),
        (3, u'pandas-0.9.1-np17py26_0.tar.bz2'),
        (3, u'pandas-0.9.1-np17py27_0.tar.bz2'),
        (4, u'pandas-0.9.0-np16py26_0.tar.bz2'),
        (4, u'pandas-0.9.0-np16py27_0.tar.bz2'),
        (4, u'pandas-0.9.0-np17py26_0.tar.bz2'),
        (4, u'pandas-0.9.0-np17py27_0.tar.bz2'),
        (5, u'pandas-0.8.1-np16py26_0.tar.bz2'),
        (5, u'pandas-0.8.1-np16py27_0.tar.bz2'),
        (5, u'pandas-0.8.1-np17py26_0.tar.bz2'),
        (5, u'pandas-0.8.1-np17py27_0.tar.bz2'),
        (1, u'py2cairo-1.10.0-py26_0.tar.bz2'),
        (1, u'py2cairo-1.10.0-py27_0.tar.bz2'),
        (1, u'python-3.3.1-0.tar.bz2'),
        (2, u'python-3.3.0-4.tar.bz2'),
        (3, u'python-3.3.0-3.tar.bz2'),
        (4, u'python-3.3.0-2.tar.bz2'),
        (5, u'python-3.3.0-pro1.tar.bz2'),
        (6, u'python-3.3.0-pro0.tar.bz2'),
        (7, u'python-2.7.5-0.tar.bz2'),
        (8, u'python-2.7.4-0.tar.bz2'),
        (9, u'python-2.7.3-7.tar.bz2'),
        (10, u'python-2.7.3-6.tar.bz2'),
        (11, u'python-2.7.3-5.tar.bz2'),
        (12, u'python-2.7.3-4.tar.bz2'),
        (13, u'python-2.7.3-3.tar.bz2'),
        (14, u'python-2.7.3-2.tar.bz2'),
        (15, u'python-2.6.8-6.tar.bz2'),
        (16, u'python-2.6.8-5.tar.bz2'),
        (17, u'python-2.6.8-4.tar.bz2'),
        (18, u'python-2.6.8-3.tar.bz2'),
        (19, u'python-2.6.8-2.tar.bz2'),
        (20, u'python-2.6.8-1.tar.bz2'),
        (1, u'pytz-2012j-py26_0.tar.bz2'),
        (1, u'pytz-2012j-py27_0.tar.bz2'),
        (1, u'pytz-2012j-py33_0.tar.bz2'),
        (2, u'pytz-2012d-py26_0.tar.bz2'),
        (2, u'pytz-2012d-py27_0.tar.bz2'),
        (2, u'pytz-2012d-py33_0.tar.bz2'),
        (1, u'pyzmq-2.2.0.1-py26_0.tar.bz2'),
        (1, u'pyzmq-2.2.0.1-py27_0.tar.bz2'),
        (1, u'pyzmq-2.2.0.1-py33_0.tar.bz2'),
        (1, u'scipy-0.11.0-np15py26_3.tar.bz2'),
        (1, u'scipy-0.11.0-np15py26_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np15py27_3.tar.bz2'),
        (1, u'scipy-0.11.0-np15py27_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py26_3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py26_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py27_3.tar.bz2'),
        (1, u'scipy-0.11.0-np16py27_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py26_3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py26_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py27_3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py27_p3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py33_3.tar.bz2'),
        (1, u'scipy-0.11.0-np17py33_p3.tar.bz2'),
        (2, u'scipy-0.11.0-np15py26_2.tar.bz2'),
        (2, u'scipy-0.11.0-np15py26_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np15py27_2.tar.bz2'),
        (2, u'scipy-0.11.0-np15py27_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py26_2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py26_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py27_2.tar.bz2'),
        (2, u'scipy-0.11.0-np16py27_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py26_2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py26_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py27_2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py27_p2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py33_2.tar.bz2'),
        (2, u'scipy-0.11.0-np17py33_p2.tar.bz2'),
        (3, u'scipy-0.11.0-np15py26_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np15py26_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np15py27_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np15py27_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py26_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py26_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py27_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np16py27_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py26_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py26_pro1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py27_ce1.tar.bz2'),
        (3, u'scipy-0.11.0-np17py27_pro1.tar.bz2'),
        (4, u'scipy-0.11.0-np15py26_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np15py27_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np16py26_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np16py27_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np17py26_pro0.tar.bz2'),
        (4, u'scipy-0.11.0-np17py27_ce0.tar.bz2'),
        (4, u'scipy-0.11.0-np17py27_pro0.tar.bz2'),
        (1, u'six-1.2.0-py26_0.tar.bz2'),
        (1, u'six-1.2.0-py27_0.tar.bz2'),
        (1, u'six-1.2.0-py33_0.tar.bz2'),
        (1, u'system-5.8-0.tar.bz2'),
        (1, u'zeromq-2.2.0-0.tar.bz2')
    ]

    assert max_rhs == 1 + 2 + 3 + 2 + 1 + 1 + 2 + 2 + 3 + 11 + 5 + 1 + 20 + 2 + 1 + 4 + 1 + 1 + 1

def test_unsat():
    r.msd_cache = {}

    # scipy 0.12.0b1 is not built for numpy 1.5, only 1.6 and 1.7
    assert raises((RuntimeError, SystemExit), lambda: r.solve(['numpy 1.5*', 'scipy 0.12.0b1']), 'conflict')
    # numpy 1.5 does not have a python 3 package
    assert raises((RuntimeError, SystemExit), lambda: r.solve(['numpy 1.5*', 'python 3*']), 'conflict')
    assert raises((RuntimeError, SystemExit), lambda: r.solve(['numpy 1.5*', 'numpy 1.6*']), 'conflict')

def test_nonexistent():
    r.msd_cache = {}

    assert raises(NoPackagesFound, lambda: r.solve(['notarealpackage 2.0*']), 'No packages found')
    # This exact version of NumPy does not exist
    assert raises(NoPackagesFound, lambda: r.solve(['numpy 1.5']), 'No packages found')

def test_nonexistent_deps():
    index2 = index.copy()
    index2['mypackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    }
    index2['mypackage-1.1-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    }
    index2['anotherpackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.1'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.1'],
        'version': '1.0',
    }
    index2['anotherpackage-2.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    }
    r = Resolve(index2)

    assert set(r.find_matches(MatchSpec('mypackage'))) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
    }
    assert set(r.get_dists(['mypackage']).keys()) == {
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.1.2-py26_0.tar.bz2',
        'nose-1.1.2-py27_0.tar.bz2',
        'nose-1.1.2-py33_0.tar.bz2',
        'nose-1.2.1-py26_0.tar.bz2',
        'nose-1.2.1-py27_0.tar.bz2',
        'nose-1.2.1-py33_0.tar.bz2',
        'nose-1.3.0-py26_0.tar.bz2',
        'nose-1.3.0-py27_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.6.8-1.tar.bz2',
        'python-2.6.8-2.tar.bz2',
        'python-2.6.8-3.tar.bz2',
        'python-2.6.8-4.tar.bz2',
        'python-2.6.8-5.tar.bz2',
        'python-2.6.8-6.tar.bz2',
        'python-2.7.3-2.tar.bz2',
        'python-2.7.3-3.tar.bz2',
        'python-2.7.3-4.tar.bz2',
        'python-2.7.3-5.tar.bz2',
        'python-2.7.3-6.tar.bz2',
        'python-2.7.3-7.tar.bz2',
        'python-2.7.4-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
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
        'zlib-1.2.7-0.tar.bz2',
    }

    assert set(r.get_dists(['mypackage'], max_only=True).keys()) == {
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py26_0.tar.bz2',
        'nose-1.3.0-py27_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.6.8-6.tar.bz2',
        'python-2.7.5-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    }

    assert r.solve(['mypackage']) == r.solve(['mypackage 1.1']) == [
        'mypackage-1.1-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]
    assert raises(NoPackagesFound, lambda: r.solve(['mypackage 1.0']))

    assert r.solve(['anotherpackage 1.0']) == [
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
    ]

    assert r.solve(['anotherpackage']) == [
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
    ]

    # This time, the latest version is messed up
    index3 = index.copy()
    index3['mypackage-1.1-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    }
    index3['mypackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    }
    index3['anotherpackage-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.0'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.0'],
        'version': '1.0',
    }
    index3['anotherpackage-2.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    }
    r = Resolve(index3)

    assert set(r.find_matches(MatchSpec('mypackage'))) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'mypackage-1.1-py33_0.tar.bz2',
        }
    assert set(r.get_dists(['mypackage']).keys()) == {
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.1.2-py26_0.tar.bz2',
        'nose-1.1.2-py27_0.tar.bz2',
        'nose-1.1.2-py33_0.tar.bz2',
        'nose-1.2.1-py26_0.tar.bz2',
        'nose-1.2.1-py27_0.tar.bz2',
        'nose-1.2.1-py33_0.tar.bz2',
        'nose-1.3.0-py26_0.tar.bz2',
        'nose-1.3.0-py27_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-2.6.8-1.tar.bz2',
        'python-2.6.8-2.tar.bz2',
        'python-2.6.8-3.tar.bz2',
        'python-2.6.8-4.tar.bz2',
        'python-2.6.8-5.tar.bz2',
        'python-2.6.8-6.tar.bz2',
        'python-2.7.3-2.tar.bz2',
        'python-2.7.3-3.tar.bz2',
        'python-2.7.3-4.tar.bz2',
        'python-2.7.3-5.tar.bz2',
        'python-2.7.3-6.tar.bz2',
        'python-2.7.3-7.tar.bz2',
        'python-2.7.4-0.tar.bz2',
        'python-2.7.5-0.tar.bz2',
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
        'zlib-1.2.7-0.tar.bz2',
    }

    assert raises(NoPackagesFound, lambda: r.get_dists(['mypackage'], max_only=True))

    assert r.solve(['mypackage']) == r.solve(['mypackage 1.0']) == [
        'mypackage-1.0-py33_0.tar.bz2',
        'nose-1.3.0-py33_0.tar.bz2',
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2',
    ]
    assert raises(NoPackagesFound, lambda: r.solve(['mypackage 1.1']))


    assert r.solve(['anotherpackage 1.0']) == [
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
    ]

    # If recursive checking is working correctly, this will give
    # anotherpackage 2.0, not anotherpackage 1.0
    assert r.solve(['anotherpackage']) == [
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
    ]


def test_install_package_with_feature():
    index2 = index.copy()
    index2['mypackage-1.0-featurepy33_0.tar.bz2'] = {
        'build': 'featurepy33_0',
        'build_number': 0,
        'depends': ['python 3.3*'],
        'name': 'mypackage',
        'version': '1.0',
        'features': 'feature',
    }
    index2['feature-1.0-py33_0.tar.bz2'] = {
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['python 3.3*'],
        'name': 'mypackage',
        'version': '1.0',
        'track_features': 'feature',
    }

    r = Resolve(index2)

    # It should not raise
    r.solve(['mypackage'], installed=['feature-1.0-py33_0.tar.bz2'])


def test_circular_dependencies():
    index2 = index.copy()
    index2['package1-1.0-0.tar.bz2'] = {
        'build': '0',
        'build_number': 0,
        'depends': ['package2'],
        'name': 'package1',
        'requires': ['package2'],
        'version': '1.0',
    }
    index2['package2-1.0-0.tar.bz2'] = {
        'build': '0',
        'build_number': 0,
        'depends': ['package1'],
        'name': 'package2',
        'requires': ['package1'],
        'version': '1.0',
    }
    r = Resolve(index2)

    assert set(r.find_matches(MatchSpec('package1'))) == {
        'package1-1.0-0.tar.bz2',
    }
    assert set(r.get_dists(['package1']).keys()) == {
        'package1-1.0-0.tar.bz2',
        'package2-1.0-0.tar.bz2',
    }
    assert r.solve(['package1']) == r.solve(['package2']) == \
        r.solve(['package1', 'package2']) == [
        'package1-1.0-0.tar.bz2',
        'package2-1.0-0.tar.bz2',
    ]


def test_package_ordering():
    sympy_071 = Package('sympy-0.7.1-py27_0.tar.bz2', r.index['sympy-0.7.1-py27_0.tar.bz2'])
    sympy_072 = Package('sympy-0.7.2-py27_0.tar.bz2', r.index['sympy-0.7.2-py27_0.tar.bz2'])
    python_275 = Package('python-2.7.5-0.tar.bz2', r.index['python-2.7.5-0.tar.bz2'])
    numpy = Package('numpy-1.7.1-py27_0.tar.bz2', r.index['numpy-1.7.1-py27_0.tar.bz2'])
    numpy_mkl = Package('numpy-1.7.1-py27_p0.tar.bz2', r.index['numpy-1.7.1-py27_p0.tar.bz2'])

    assert sympy_071 < sympy_072
    assert not sympy_071 < sympy_071
    assert not sympy_072 < sympy_071
    raises(TypeError, lambda: sympy_071 < python_275)

    assert sympy_071 <= sympy_072
    assert sympy_071 <= sympy_071
    assert not sympy_072 <= sympy_071
    assert raises(TypeError, lambda: sympy_071 <= python_275)

    assert sympy_071 == sympy_071
    assert not sympy_071 == sympy_072
    assert (sympy_071 == python_275) is False
    assert (sympy_071 == 1) is False

    assert not sympy_071 != sympy_071
    assert sympy_071 != sympy_072
    assert (sympy_071 != python_275) is True

    assert not sympy_071 > sympy_072
    assert not sympy_071 > sympy_071
    assert sympy_072 > sympy_071
    raises(TypeError, lambda: sympy_071 > python_275)

    assert not sympy_071 >= sympy_072
    assert sympy_071 >= sympy_071
    assert sympy_072 >= sympy_071
    assert raises(TypeError, lambda: sympy_071 >= python_275)

    # The first four are a bit arbitrary. For now, we just test that it
    # doesn't prefer the mkl version.
    assert not numpy < numpy_mkl
    assert not numpy <= numpy_mkl
    assert numpy > numpy_mkl
    assert numpy >= numpy_mkl
    assert (numpy != numpy_mkl) is True
    assert (numpy == numpy_mkl) is False

def test_irrational_version():
    r.msd_cache = {}

    assert r.solve2(['pytz 2012d', 'python 3*'], set(), returnall=True) == [[
        'openssl-1.0.1c-0.tar.bz2',
        'python-3.3.2-0.tar.bz2',
        'pytz-2012d-py33_0.tar.bz2',
        'readline-6.2-0.tar.bz2',
        'sqlite-3.7.13-0.tar.bz2',
        'system-5.8-1.tar.bz2',
        'tk-8.5.13-0.tar.bz2',
        'zlib-1.2.7-0.tar.bz2'
    ]]

def test_no_features():
    # Features that aren't specified shouldn't be selected.
    r.msd_cache = {}

    # Without this, there would be another solution including 'scipy-0.11.0-np16py26_p3.tar.bz2'.
    assert r.solve2(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'], set(),
        returnall=True) == [[
            'numpy-1.6.2-py26_4.tar.bz2',
            'openssl-1.0.1c-0.tar.bz2',
            'python-2.6.8-6.tar.bz2',
            'readline-6.2-0.tar.bz2',
            'scipy-0.11.0-np16py26_3.tar.bz2',
            'sqlite-3.7.13-0.tar.bz2',
            'system-5.8-1.tar.bz2',
            'tk-8.5.13-0.tar.bz2',
            'zlib-1.2.7-0.tar.bz2',
            ]]

    assert r.solve2(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'], f_mkl,
        returnall=True) == [[
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
            ]]

    index2 = index.copy()
    index2["pandas-0.12.0-np16py27_0.tar.bz2"] = \
        {
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
        }
    # Make it want to choose the pro version by having it be newer.
    index2["numpy-1.6.2-py27_p5.tar.bz2"] = \
        {
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
        }

    r2 = Resolve(index2)

    # This should not pick any mkl packages (the difference here is that none
    # of the specs directly have mkl versions)
    assert r2.solve2(['pandas 0.12.0 np16py27_0', 'python 2.7*'], set(),
        returnall=True) == [[
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
            ]]

    assert r2.solve2(['pandas 0.12.0 np16py27_0', 'python 2.7*'], f_mkl,
        returnall=True)[0] == [[
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
            ]][0]

def test_update_deps():
    r.msd_cache = {}

    installed = r.solve2(['python 2.7*', 'numpy 1.6*', 'pandas 0.10.1'], set())
    assert installed == [
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
    ]

    # numpy, scipy, and pandas should all be updated here. pytz is a new
    # dependency of pandas.
    assert r.solve2(['pandas', 'python 2.7*'], set(), installed=installed,
        update_deps=True, returnall=True) == [[
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
        'zlib-1.2.7-0.tar.bz2',
    ]]

    # pandas should be updated here. However, it's going to try to not update
    # scipy, so it won't be updated to the latest version (0.11.0).
    assert r.solve2(['pandas', 'python 2.7*'], set(), installed=installed,
        update_deps=False, returnall=True) == [[
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
