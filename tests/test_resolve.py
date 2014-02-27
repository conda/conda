from __future__ import print_function, absolute_import
import json
import unittest
from os.path import dirname, join

from conda.resolve import MatchSpec, Package, Resolve

from tests.helpers import raises


with open(join(dirname(__file__), 'index.json')) as fi:
    r = Resolve(json.load(fi))

f_mkl = set(['mkl'])


class TestMatchSpec(unittest.TestCase):

    def test_match(self):
        for spec, res in [('numpy 1.7*', True),
                          ('numpy 1.7.1', True),
                          ('numpy 1.7', False),
                          ('numpy 1.5*', False),
                          ('numpy 1.6*|1.7*', True),
                          ('numpy 1.6*|1.8*', False),
                          ('numpy 1.6.2|1.7*', True),
                          ('numpy 1.6.2|1.7.1', True),
                          ('numpy 1.6.2|1.7.0', False),
                          ('numpy 1.7.1 py27_0', True),
                          ('numpy 1.7.1 py26_0', False),
                          ('python', False)]:
            m = MatchSpec(spec)
            self.assertEqual(m.match('numpy-1.7.1-py27_0.tar.bz2'), res)

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
        self.assertRaises(ValueError, pkgs.sort)


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
                     set()),
            ['iopro-1.4.3-np17py27_p0.tar.bz2',
             'numpy-1.7.1-py27_0.tar.bz2',
             'openssl-1.0.1c-0.tar.bz2',
             'python-2.7.5-0.tar.bz2',
             'readline-6.2-0.tar.bz2',
             'sqlite-3.7.13-0.tar.bz2',
             'system-5.8-1.tar.bz2',
             'tk-8.5.13-0.tar.bz2',
             'unixodbc-2.3.1-0.tar.bz2',
             'zlib-1.2.7-0.tar.bz2'])

    def test_iopro_mkl(self):
        self.assertEqual(
            r.solve2(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
                    f_mkl),
            ['iopro-1.4.3-np17py27_p0.tar.bz2',
             'mkl-rt-11.0-p0.tar.bz2',
             'numpy-1.7.1-py27_p0.tar.bz2',
             'openssl-1.0.1c-0.tar.bz2',
             'python-2.7.5-0.tar.bz2',
             'readline-6.2-0.tar.bz2',
             'sqlite-3.7.13-0.tar.bz2',
             'system-5.8-1.tar.bz2',
             'tk-8.5.13-0.tar.bz2',
             'unixodbc-2.3.1-0.tar.bz2',
             'zlib-1.2.7-0.tar.bz2'])

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


def test_get_dists():
    dists = r.get_dists(["anaconda 1.5.0"])
    assert 'anaconda-1.5.0-np17py27_0.tar.bz2' in dists
    assert 'dynd-python-0.3.0-np17py33_0.tar.bz2' in dists
    for d in dists:
        assert dists[d].fn == d

def test_generate_eq():
    dists = r.get_dists(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
    v = {}
    w = {}
    for i, fn in enumerate(sorted(dists)):
        v[fn] = i + 1
        w[i + 1] = fn

    eq, max_rhs = r.generate_eq(v, dists)
    assert all(i > 0 for i, _ in eq)
    e = [(i, w[j]) for i, j in eq]
    # Should satisfy the following criteria:
    # - lower versions of the same package should should have higher
    #   coefficients.
    # - the same versions of the same package (e.g., different build strings)
    #   should have the same coefficients.
    # - a package that only has one version should not appear, as it will have
    #   a 0 coefficient. The same is true of the latest version of a package.
    # The actual order may be arbitrary, so we compare sets
    assert set(e) == set([
        (1, 'python-3.3.1-0.tar.bz2'),
        (2, 'python-3.3.0-4.tar.bz2'),
        (3, 'python-3.3.0-3.tar.bz2'),
        (4, 'python-3.3.0-2.tar.bz2'),
        (5, 'python-3.3.0-pro1.tar.bz2'),
        (6, 'python-3.3.0-pro0.tar.bz2'),
        (7, 'python-2.7.5-0.tar.bz2'),
        (8, 'python-2.7.4-0.tar.bz2'),
        (9, 'python-2.7.3-7.tar.bz2'),
        (10, 'python-2.7.3-6.tar.bz2'),
        (11, 'python-2.7.3-5.tar.bz2'),
        (12, 'python-2.7.3-4.tar.bz2'),
        (13, 'python-2.7.3-3.tar.bz2'),
        (14, 'python-2.7.3-2.tar.bz2'),
        (15, 'python-2.6.8-6.tar.bz2'),
        (16, 'python-2.6.8-5.tar.bz2'),
        (17, 'python-2.6.8-4.tar.bz2'),
        (18, 'python-2.6.8-3.tar.bz2'),
        (19, 'python-2.6.8-2.tar.bz2'),
        (20, 'python-2.6.8-1.tar.bz2'),
        (1, 'numpy-1.7.0-py26_0.tar.bz2'),
        (1, 'numpy-1.7.0-py26_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py27_0.tar.bz2'),
        (1, 'numpy-1.7.0-py27_p0.tar.bz2'),
        (1, 'numpy-1.7.0-py33_0.tar.bz2'),
        (1, 'numpy-1.7.0-py33_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py26_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py26_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py27_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py27_p0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py33_0.tar.bz2'),
        (2, 'numpy-1.7.0rc1-py33_p0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py26_ce0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py26_pro0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py27_ce0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py27_pro0.tar.bz2'),
        (3, 'numpy-1.7.0b2-py33_pro0.tar.bz2'),
        (4, 'numpy-1.6.2-py26_4.tar.bz2'),
        (4, 'numpy-1.6.2-py27_4.tar.bz2'),
        (1, 'nose-1.2.1-py26_0.tar.bz2'),
        (1, 'nose-1.2.1-py27_0.tar.bz2'),
        (1, 'nose-1.2.1-py33_0.tar.bz2'),
        (2, 'nose-1.1.2-py26_0.tar.bz2'),
        (2, 'nose-1.1.2-py27_0.tar.bz2'),
        (2, 'nose-1.1.2-py33_0.tar.bz2'),
        (1, 'mkl-10.3-p1.tar.bz2'),
        (2, 'mkl-10.3-0.tar.bz2'),
        (1, 'system-5.8-0.tar.bz2')])

    assert max_rhs == 20 + 4 + 2 + 2 + 1

def test_unsat():
    # scipy 0.12.0b1 is not built for numpy 1.5, only 1.6 and 1.7
    assert raises(RuntimeError, lambda: r.solve(['numpy 1.5*', 'scipy 0.12.0b1']))
    # numpy 1.5 does not have a python 3 package
    assert raises(RuntimeError, lambda: r.solve(['numpy 1.5*', 'python 3*']))

    assert raises(RuntimeError, lambda: r.solve(['numpy 1.5', 'numpy 1.6']))
