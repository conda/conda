import json
import unittest
from os.path import dirname, join

from conda.resolve import MatchSpec, Package, Resolve, partial_lt



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
            ('iopro-1.4.3-np17py27_p0.tar.bz2',
             'numpy-1.7.1-py27_0.tar.bz2',
             'openssl-1.0.1c-0.tar.bz2',
             'python-2.7.5-0.tar.bz2',
             'readline-6.2-0.tar.bz2',
             'sqlite-3.7.13-0.tar.bz2',
             'system-5.8-1.tar.bz2',
             'tk-8.5.13-0.tar.bz2',
             'unixodbc-2.3.1-0.tar.bz2',
             'zlib-1.2.7-0.tar.bz2'))

    def test_iopro_mkl(self):
        self.assertEqual(
            r.solve2(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'],
                    f_mkl),
            ('iopro-1.4.3-np17py27_p0.tar.bz2',
             'mkl-rt-11.0-p0.tar.bz2',
             'numpy-1.7.1-py27_p0.tar.bz2',
             'openssl-1.0.1c-0.tar.bz2',
             'python-2.7.5-0.tar.bz2',
             'readline-6.2-0.tar.bz2',
             'sqlite-3.7.13-0.tar.bz2',
             'system-5.8-1.tar.bz2',
             'tk-8.5.13-0.tar.bz2',
             'unixodbc-2.3.1-0.tar.bz2',
             'zlib-1.2.7-0.tar.bz2'))

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

def _raises(exception, func):
    try:
        a = func()
    except exception:
        return True
    raise Exception("did not raise, gave %s" % a)

def test_package_ordering():
    sympy_071 = Package('sympy-0.7.1-py27_0.tar.bz2', r.index['sympy-0.7.1-py27_0.tar.bz2'])
    sympy_072 = Package('sympy-0.7.2-py27_0.tar.bz2', r.index['sympy-0.7.2-py27_0.tar.bz2'])
    python_275 = Package('python-2.7.5-0.tar.bz2', r.index['python-2.7.5-0.tar.bz2'])

    assert sympy_071 < sympy_072
    assert not sympy_071 < sympy_071
    assert not sympy_072 < sympy_071
    _raises(TypeError, lambda: sympy_071 < python_275)

    assert sympy_071 <= sympy_072
    assert sympy_071 <= sympy_071
    assert not sympy_072 <= sympy_071
    assert _raises(TypeError, lambda: sympy_071 <= python_275)

    assert sympy_071 == sympy_071
    assert not sympy_071 == sympy_072
    # This is wrong. It should just be False
    assert _raises(TypeError, lambda: sympy_071 == python_275)

    assert not sympy_071 != sympy_071
    assert sympy_071 != sympy_072
    assert _raises(TypeError, lambda: sympy_071 != python_275)

    assert not sympy_071 > sympy_072
    assert not sympy_071 > sympy_071
    assert sympy_072 > sympy_071
    _raises(TypeError, lambda: sympy_071 > python_275)

    assert not sympy_071 >= sympy_072
    assert sympy_071 >= sympy_071
    assert sympy_072 >= sympy_071
    assert _raises(TypeError, lambda: sympy_071 >= python_275)


def test_partial_lt():
    sympy_071 = Package('sympy-0.7.1-py27_0.tar.bz2', r.index['sympy-0.7.1-py27_0.tar.bz2'])
    sympy_072 = Package('sympy-0.7.2-py27_0.tar.bz2', r.index['sympy-0.7.2-py27_0.tar.bz2'])
    python_275 = Package('python-2.7.5-0.tar.bz2', r.index['python-2.7.5-0.tar.bz2'])
    python_274 = Package('python-2.7.4-0.tar.bz2', r.index['python-2.7.4-0.tar.bz2'])
    matplotlib_121 = Package('matplotlib-1.2.1-np17py27_1.tar.bz2', r.index['matplotlib-1.2.1-np17py27_1.tar.bz2'])

    assert partial_lt((sympy_071, python_274), (sympy_071, python_275)) is True
    assert partial_lt((sympy_071, python_275), (sympy_071, python_274)) is False
    assert partial_lt((sympy_071, python_274), (sympy_072, python_275)) is True
    assert partial_lt((sympy_072, python_275), (sympy_071, python_274)) is False
    assert partial_lt((sympy_071, python_274), (sympy_071, python_274)) is False

    assert partial_lt((sympy_071, python_274), (sympy_071, python_274,
    matplotlib_121)) is True
    assert partial_lt((sympy_071, python_274, matplotlib_121), (sympy_071,
    python_274)) is False

    assert partial_lt((sympy_071, python_274), (sympy_072, python_274,
    matplotlib_121)) is True
    assert partial_lt((sympy_072, python_274, matplotlib_121), (sympy_071,
    python_274)) is False

    assert _raises(TypeError, lambda: partial_lt((sympy_071, python_275), (sympy_071, matplotlib_121)))
    assert _raises(TypeError, lambda: partial_lt((sympy_071, matplotlib_121), (sympy_071, python_275)))

    assert partial_lt((sympy_071, python_275), (sympy_072, matplotlib_121)) is True
    assert partial_lt((sympy_072, matplotlib_121), (sympy_071, python_275)) is False
