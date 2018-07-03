from __future__ import absolute_import, print_function

import unittest

from datetime import datetime
import pytest

from conda.base.context import context, reset_context
from conda.common.compat import iteritems, itervalues
from conda.common.io import env_var
from conda.exceptions import UnsatisfiableError
from conda.models.channel import Channel
from conda.models.records import PackageRecord
from conda.resolve import MatchSpec, Resolve, ResolvePackageNotFound

from .helpers import get_index_r_1, get_index_r_3, raises

index, r, = get_index_r_1()
f_mkl = set(['mkl'])


class TestSolve(unittest.TestCase):

    def assert_have_mkl(self, precs, names):
        for prec in precs:
            if prec.name in names:
                assert 'mkl' in prec.features

    # def test_explicit0(self):
    #     self.assertEqual(r.explicit([]), [])
    #
    # def test_explicit1(self):
    #     self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0']), None)
    #     self.assertEqual(r.explicit(['zlib']), None)
    #     self.assertEqual(r.explicit(['zlib 1.2.7']), None)
    #     # because zlib has no dependencies it is also explicit
    #     exp_result = r.explicit([MatchSpec('zlib 1.2.7 0', channel='defaults')])
    #     self.assertEqual(exp_result, [Dist('channel-1::zlib-1.2.7-0.tar.bz2')])
    #
    # def test_explicit2(self):
    #     self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
    #                                  'zlib 1.2.7 0']),
    #                      [Dist('channel-1::pycosat-0.6.0-py27_0.tar.bz2'),
    #                       Dist('channel-1::zlib-1.2.7-0.tar.bz2')])
    #     self.assertEqual(r.explicit(['pycosat 0.6.0 py27_0',
    #                                  'zlib 1.2.7']), None)
    #
    # def test_explicitNone(self):
    #     self.assertEqual(r.explicit(['pycosat 0.6.0 notarealbuildstring']), None)

    def test_empty(self):
        self.assertEqual(r.install([]), [])

    # def test_anaconda_14(self):
    #     specs = ['anaconda 1.4.0 np17py33_0']
    #     res = r.explicit(specs)
    #     self.assertEqual(len(res), 51)
    #     assert r.install(specs) == res
    #     specs.append('python 3.3*')
    #     self.assertEqual(r.explicit(specs), None)
    #     self.assertEqual(r.install(specs), res)

    def test_iopro_nomkl(self):
        installed = r.install(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*'], returnall=True)
        installed = [rec.dist_str() for rec in installed]
        assert installed == [
            'channel-1::iopro-1.4.3-np17py27_p0',
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::python-2.7.5-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
        ]

    def test_iopro_mkl(self):
        installed = r.install(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl')], returnall=True)
        installed = [prec.dist_str() for prec in installed]
        assert installed == [
            'channel-1::iopro-1.4.3-np17py27_p0',
            'channel-1::mkl-rt-11.0-p0',
            'channel-1::numpy-1.7.1-py27_p0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::python-2.7.5-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
        ]

    def test_mkl(self):
        a = r.install(['mkl 11*', MatchSpec(track_features='mkl')])
        b = r.install(['mkl'])
        assert a == b

    def test_accelerate(self):
        self.assertEqual(
            r.install(['accelerate']),
            r.install(['accelerate', MatchSpec(track_features='mkl')]))

    def test_scipy_mkl(self):
        precs = r.install(['scipy', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl')])
        self.assert_have_mkl(precs, ('numpy', 'scipy'))
        dist_strs = [prec.dist_str() for prec in precs]
        assert 'channel-1::scipy-0.12.0-np17py27_p0' in dist_strs

    def test_anaconda_nomkl(self):
        precs = r.install(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        assert len(precs) == 107
        dist_strs = [prec.dist_str() for prec in precs]
        assert 'channel-1::scipy-0.12.0-np17py27_0' in dist_strs


def test_pseudo_boolean():
    # The latest version of iopro, 1.5.0, was not built against numpy 1.5
    installed = r.install(['iopro', 'python 2.7*', 'numpy 1.5*'], returnall=True)
    installed = [rec.dist_str() for rec in installed]
    assert installed == [
        'channel-1::iopro-1.4.3-np15py27_p0',
        'channel-1::numpy-1.5.1-py27_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.7.5-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::unixodbc-2.3.1-0',
        'channel-1::zlib-1.2.7-0',
    ]

    installed = r.install(['iopro', 'python 2.7*', 'numpy 1.5*', MatchSpec(track_features='mkl')], returnall=True)
    installed = [rec.dist_str() for rec in installed]
    assert installed == [
        'channel-1::iopro-1.4.3-np15py27_p0',
        'channel-1::mkl-rt-11.0-p0',
        'channel-1::numpy-1.5.1-py27_p4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.7.5-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::unixodbc-2.3.1-0',
        'channel-1::zlib-1.2.7-0',
    ]


def test_get_dists():
    reduced_index = r.get_reduced_index(["anaconda 1.5.0"])
    dist_strs = [prec.dist_str() for prec in reduced_index]
    assert 'channel-1::anaconda-1.5.0-np17py27_0' in dist_strs
    assert 'channel-1::dynd-python-0.3.0-np17py33_0' in dist_strs


def test_generate_eq_1():
    reduced_index = r.get_reduced_index(['anaconda'])
    r2 = Resolve(reduced_index, True, True)
    C = r2.gen_clauses()
    eqc, eqv, eqb, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
    # Should satisfy the following criteria:
    # - lower versions of the same package should should have higher
    #   coefficients.
    # - the same versions of the same package (e.g., different build strings)
    #   should have the same coefficients.
    # - a package that only has one version should not appear, unless
    #   include=True as it will have a 0 coefficient. The same is true of the
    #   latest version of a package.
    eqc = {key: value for key, value in iteritems(eqc)}
    eqv = {key: value for key, value in iteritems(eqv)}
    eqb = {key: value for key, value in iteritems(eqb)}
    eqt = {key: value for key, value in iteritems(eqt)}
    assert eqc == {}
    assert eqv == {
        'channel-1::anaconda-1.4.0-np15py26_0': 1,
        'channel-1::anaconda-1.4.0-np15py27_0': 1,
        'channel-1::anaconda-1.4.0-np16py26_0': 1,
        'channel-1::anaconda-1.4.0-np16py27_0': 1,
        'channel-1::anaconda-1.4.0-np17py26_0': 1,
        'channel-1::anaconda-1.4.0-np17py27_0': 1,
        'channel-1::anaconda-1.4.0-np17py33_0': 1,
        'channel-1::astropy-0.2-np15py26_0': 1,
        'channel-1::astropy-0.2-np15py27_0': 1,
        'channel-1::astropy-0.2-np16py26_0': 1,
        'channel-1::astropy-0.2-np16py27_0': 1,
        'channel-1::astropy-0.2-np17py26_0': 1,
        'channel-1::astropy-0.2-np17py27_0': 1,
        'channel-1::astropy-0.2-np17py33_0': 1,
        'channel-1::biopython-1.60-np15py26_0': 1,
        'channel-1::biopython-1.60-np15py27_0': 1,
        'channel-1::biopython-1.60-np16py26_0': 1,
        'channel-1::biopython-1.60-np16py27_0': 1,
        'channel-1::biopython-1.60-np17py26_0': 1,
        'channel-1::biopython-1.60-np17py27_0': 1,
        'channel-1::bitarray-0.8.0-py26_0': 1,
        'channel-1::bitarray-0.8.0-py27_0': 1,
        'channel-1::bitarray-0.8.0-py33_0': 1,
        'channel-1::boto-2.8.0-py26_0': 1,
        'channel-1::boto-2.8.0-py27_0': 1,
        'channel-1::conda-1.4.4-py27_0': 1,
        'channel-1::cython-0.18-py26_0': 1,
        'channel-1::cython-0.18-py27_0': 1,
        'channel-1::cython-0.18-py33_0': 1,
        'channel-1::distribute-0.6.34-py26_1': 1,
        'channel-1::distribute-0.6.34-py27_1': 1,
        'channel-1::distribute-0.6.34-py33_1': 1,
        'channel-1::gevent-0.13.7-py26_0': 1,
        'channel-1::gevent-0.13.7-py27_0': 1,
        'channel-1::ipython-0.13.1-py26_1': 1,
        'channel-1::ipython-0.13.1-py27_1': 1,
        'channel-1::ipython-0.13.1-py33_1': 1,
        'channel-1::llvmpy-0.11.1-py26_0': 1,
        'channel-1::llvmpy-0.11.1-py27_0': 1,
        'channel-1::llvmpy-0.11.1-py33_0': 1,
        'channel-1::lxml-3.0.2-py26_0': 1,
        'channel-1::lxml-3.0.2-py27_0': 1,
        'channel-1::lxml-3.0.2-py33_0': 1,
        'channel-1::matplotlib-1.2.0-np15py26_1': 1,
        'channel-1::matplotlib-1.2.0-np15py27_1': 1,
        'channel-1::matplotlib-1.2.0-np16py26_1': 1,
        'channel-1::matplotlib-1.2.0-np16py27_1': 1,
        'channel-1::matplotlib-1.2.0-np17py26_1': 1,
        'channel-1::matplotlib-1.2.0-np17py27_1': 1,
        'channel-1::matplotlib-1.2.0-np17py33_1': 1,
        'channel-1::nose-1.2.1-py26_0': 1,
        'channel-1::nose-1.2.1-py27_0': 1,
        'channel-1::nose-1.2.1-py33_0': 1,
        'channel-1::numba-0.7.0-np16py26_1': 1,
        'channel-1::numba-0.7.0-np16py27_1': 1,
        'channel-1::numba-0.7.0-np17py26_1': 1,
        'channel-1::numba-0.7.0-np17py27_1': 1,
        'channel-1::numpy-1.5.1-py26_3': 3,
        'channel-1::numpy-1.5.1-py27_3': 3,
        'channel-1::numpy-1.6.2-py26_3': 2,
        'channel-1::numpy-1.6.2-py26_4': 2,
        # 'channel-1::numpy-1.6.2-py26_p4': 2,
        'channel-1::numpy-1.6.2-py27_3': 2,
        'channel-1::numpy-1.6.2-py27_4': 2,
        # 'channel-1::numpy-1.6.2-py27_p4': 2,
        'channel-1::numpy-1.7.0-py26_0': 1,
        'channel-1::numpy-1.7.0-py27_0': 1,
        'channel-1::numpy-1.7.0-py33_0': 1,
        'channel-1::pandas-0.10.0-np16py26_0': 2,
        'channel-1::pandas-0.10.0-np16py27_0': 2,
        'channel-1::pandas-0.10.0-np17py26_0': 2,
        'channel-1::pandas-0.10.0-np17py27_0': 2,
        'channel-1::pandas-0.10.1-np16py26_0': 1,
        'channel-1::pandas-0.10.1-np16py27_0': 1,
        'channel-1::pandas-0.10.1-np17py26_0': 1,
        'channel-1::pandas-0.10.1-np17py27_0': 1,
        'channel-1::pandas-0.10.1-np17py33_0': 1,
        'channel-1::pandas-0.8.1-np16py26_0': 5,
        'channel-1::pandas-0.8.1-np16py27_0': 5,
        'channel-1::pandas-0.8.1-np17py26_0': 5,
        'channel-1::pandas-0.8.1-np17py27_0': 5,
        'channel-1::pandas-0.9.0-np16py26_0': 4,
        'channel-1::pandas-0.9.0-np16py27_0': 4,
        'channel-1::pandas-0.9.0-np17py26_0': 4,
        'channel-1::pandas-0.9.0-np17py27_0': 4,
        'channel-1::pandas-0.9.1-np16py26_0': 3,
        'channel-1::pandas-0.9.1-np16py27_0': 3,
        'channel-1::pandas-0.9.1-np17py26_0': 3,
        'channel-1::pandas-0.9.1-np17py27_0': 3,
        'channel-1::pip-1.2.1-py26_1': 1,
        'channel-1::pip-1.2.1-py27_1': 1,
        'channel-1::pip-1.2.1-py33_1': 1,
        'channel-1::psutil-0.6.1-py26_0': 1,
        'channel-1::psutil-0.6.1-py27_0': 1,
        'channel-1::psutil-0.6.1-py33_0': 1,
        'channel-1::pyflakes-0.6.1-py26_0': 1,
        'channel-1::pyflakes-0.6.1-py27_0': 1,
        'channel-1::pyflakes-0.6.1-py33_0': 1,
        'channel-1::python-2.6.8-6': 4,
        'channel-1::python-2.7.3-7': 3,
        'channel-1::python-2.7.4-0': 2,
        'channel-1::python-3.3.0-4': 1,
        'channel-1::pytz-2012j-py26_0': 1,
        'channel-1::pytz-2012j-py27_0': 1,
        'channel-1::pytz-2012j-py33_0': 1,
        'channel-1::requests-0.13.9-py26_0': 1,
        'channel-1::requests-0.13.9-py27_0': 1,
        'channel-1::requests-0.13.9-py33_0': 1,
        'channel-1::scikit-learn-0.13-np15py26_1': 1,
        'channel-1::scikit-learn-0.13-np15py27_1': 1,
        'channel-1::scikit-learn-0.13-np16py26_1': 1,
        'channel-1::scikit-learn-0.13-np16py27_1': 1,
        'channel-1::scikit-learn-0.13-np17py26_1': 1,
        'channel-1::scikit-learn-0.13-np17py27_1': 1,
        'channel-1::scipy-0.11.0-np15py26_3': 1,
        'channel-1::scipy-0.11.0-np15py27_3': 1,
        'channel-1::scipy-0.11.0-np16py26_3': 1,
        'channel-1::scipy-0.11.0-np16py27_3': 1,
        'channel-1::scipy-0.11.0-np17py26_3': 1,
        'channel-1::scipy-0.11.0-np17py27_3': 1,
        'channel-1::scipy-0.11.0-np17py33_3': 1,
        'channel-1::six-1.2.0-py26_0': 1,
        'channel-1::six-1.2.0-py27_0': 1,
        'channel-1::six-1.2.0-py33_0': 1,
        'channel-1::spyder-2.1.13-py27_0': 1,
        'channel-1::sqlalchemy-0.7.8-py26_0': 1,
        'channel-1::sqlalchemy-0.7.8-py27_0': 1,
        'channel-1::sqlalchemy-0.7.8-py33_0': 1,
        'channel-1::sympy-0.7.1-py26_0': 1,
        'channel-1::sympy-0.7.1-py27_0': 1,
        'channel-1::tornado-2.4.1-py26_0': 1,
        'channel-1::tornado-2.4.1-py27_0': 1,
        'channel-1::tornado-2.4.1-py33_0': 1,
        'channel-1::xlrd-0.9.0-py26_0': 1,
        'channel-1::xlrd-0.9.0-py27_0': 1,
        'channel-1::xlrd-0.9.0-py33_0': 1,
        'channel-1::xlwt-0.7.4-py26_0': 1,
        'channel-1::xlwt-0.7.4-py27_0': 1,
    }
    assert eqb == {
        'channel-1::cairo-1.12.2-0': 1,
        'channel-1::cubes-0.10.2-py27_0': 1,
        'channel-1::dateutil-2.1-py26_0': 1,
        'channel-1::dateutil-2.1-py27_0': 1,
        'channel-1::dateutil-2.1-py33_0': 1,
        'channel-1::gevent-websocket-0.3.6-py26_1': 1,
        'channel-1::gevent-websocket-0.3.6-py27_1': 1,
        'channel-1::gevent_zeromq-0.2.5-py26_1': 1,
        'channel-1::gevent_zeromq-0.2.5-py27_1': 1,
        'channel-1::libnetcdf-4.2.1.1-0': 1,
        'channel-1::numexpr-2.0.1-np16py26_1': 2,
        'channel-1::numexpr-2.0.1-np16py26_2': 1,
        'channel-1::numexpr-2.0.1-np16py26_ce0': 3,
        'channel-1::numexpr-2.0.1-np16py26_p1': 2,
        'channel-1::numexpr-2.0.1-np16py26_p2': 1,
        'channel-1::numexpr-2.0.1-np16py26_pro0': 3,
        'channel-1::numexpr-2.0.1-np16py27_1': 2,
        'channel-1::numexpr-2.0.1-np16py27_2': 1,
        'channel-1::numexpr-2.0.1-np16py27_ce0': 3,
        'channel-1::numexpr-2.0.1-np16py27_p1': 2,
        'channel-1::numexpr-2.0.1-np16py27_p2': 1,
        'channel-1::numexpr-2.0.1-np16py27_pro0': 3,
        'channel-1::numexpr-2.0.1-np17py26_1': 2,
        'channel-1::numexpr-2.0.1-np17py26_2': 1,
        'channel-1::numexpr-2.0.1-np17py26_ce0': 3,
        'channel-1::numexpr-2.0.1-np17py26_p1': 2,
        'channel-1::numexpr-2.0.1-np17py26_p2': 1,
        'channel-1::numexpr-2.0.1-np17py26_pro0': 3,
        'channel-1::numexpr-2.0.1-np17py27_1': 2,
        'channel-1::numexpr-2.0.1-np17py27_2': 1,
        'channel-1::numexpr-2.0.1-np17py27_ce0': 3,
        'channel-1::numexpr-2.0.1-np17py27_p1': 2,
        'channel-1::numexpr-2.0.1-np17py27_p2': 1,
        'channel-1::numexpr-2.0.1-np17py27_pro0': 3,
        'channel-1::numpy-1.6.2-py26_3': 1,
        'channel-1::numpy-1.6.2-py27_3': 1,
        'channel-1::py2cairo-1.10.0-py26_0': 1,
        'channel-1::py2cairo-1.10.0-py27_0': 1,
        'channel-1::pycurl-7.19.0-py26_0': 1,
        'channel-1::pycurl-7.19.0-py27_0': 1,
        'channel-1::pysal-1.5.0-np15py27_0': 1,
        'channel-1::pysal-1.5.0-np16py27_0': 1,
        'channel-1::pysal-1.5.0-np17py27_0': 1,
        'channel-1::pytest-2.3.4-py26_0': 1,
        'channel-1::pytest-2.3.4-py27_0': 1,
        'channel-1::pyzmq-2.2.0.1-py26_0': 1,
        'channel-1::pyzmq-2.2.0.1-py27_0': 1,
        'channel-1::pyzmq-2.2.0.1-py33_0': 1,
        'channel-1::scikit-image-0.8.2-np16py26_0': 1,
        'channel-1::scikit-image-0.8.2-np16py27_0': 1,
        'channel-1::scikit-image-0.8.2-np17py26_0': 1,
        'channel-1::scikit-image-0.8.2-np17py27_0': 1,
        'channel-1::scikit-image-0.8.2-np17py33_0': 1,
        'channel-1::sphinx-1.1.3-py26_2': 1,
        'channel-1::sphinx-1.1.3-py27_2': 1,
        'channel-1::sphinx-1.1.3-py33_2': 1,
        'channel-1::statsmodels-0.4.3-np16py26_0': 1,
        'channel-1::statsmodels-0.4.3-np16py27_0': 1,
        'channel-1::statsmodels-0.4.3-np17py26_0': 1,
        'channel-1::statsmodels-0.4.3-np17py27_0': 1,
        'channel-1::system-5.8-0': 1,
        'channel-1::theano-0.5.0-np15py26_0': 1,
        'channel-1::theano-0.5.0-np15py27_0': 1,
        'channel-1::theano-0.5.0-np16py26_0': 1,
        'channel-1::theano-0.5.0-np16py27_0': 1,
        'channel-1::theano-0.5.0-np17py26_0': 1,
        'channel-1::theano-0.5.0-np17py27_0': 1,
        'channel-1::zeromq-2.2.0-0': 1,
    }

    # No timestamps in the current data set
    assert eqt == {}


def test_unsat():
    # scipy 0.12.0b1 is not built for numpy 1.5, only 1.6 and 1.7
    assert raises(UnsatisfiableError, lambda: r.install(['numpy 1.5*', 'scipy 0.12.0b1']))
    # numpy 1.5 does not have a python 3 package
    assert raises(UnsatisfiableError, lambda: r.install(['numpy 1.5*', 'python 3*']))
    assert raises(UnsatisfiableError, lambda: r.install(['numpy 1.5*', 'numpy 1.6*']))


def test_nonexistent():
    assert not r.find_matches(MatchSpec('notarealpackage 2.0*'))
    assert raises(ResolvePackageNotFound, lambda: r.install(['notarealpackage 2.0*']))
    # This exact version of NumPy does not exist
    assert raises(ResolvePackageNotFound, lambda: r.install(['numpy 1.5']))


def test_timestamps_and_deps():
    # If timestamp maximization is performed too early in the solve optimization,
    # it will force unnecessary changes to dependencies. Timestamp maximization needs
    # to be done at low priority so that conda is free to consider packages with the
    # same version and build that are most compatible with the installed environment.
    index2 = {key: value for key, value in iteritems(index)}
    mypackage1 = PackageRecord(**{
        'build': 'hash12_0',
        'build_number': 0,
        'depends': ['libpng 1.2.*'],
        'name': 'mypackage',
        'requires': ['libpng 1.2.*'],
        'version': '1.0',
        'timestamp': 1,
    })
    index2[mypackage1] = mypackage1
    mypackage2 = PackageRecord(**{
        'build': 'hash15_0',
        'build_number': 0,
        'depends': ['libpng 1.5.*'],
        'name': 'mypackage',
        'requires': ['libpng 1.5.*'],
        'version': '1.0',
        'timestamp': 0,
    })
    index2[mypackage2] = mypackage2
    r = Resolve(index2)
    installed1 = r.install(['libpng 1.2.*', 'mypackage'])
    print([prec.dist_str() for prec in installed1])
    assert any(k.name == 'libpng' and k.version.startswith('1.2') for k in installed1)
    assert any(k.name == 'mypackage' and k.build == 'hash12_0' for k in installed1)
    installed2 = r.install(['libpng 1.5.*', 'mypackage'])
    assert any(k.name == 'libpng' and k.version.startswith('1.5') for k in installed2)
    assert any(k.name == 'mypackage' and k.build == 'hash15_0' for k in installed2)
    # this is testing that previously installed reqs are not disrupted by newer timestamps.
    #   regression test of sorts for https://github.com/conda/conda/issues/6271
    installed3 = r.install(['mypackage'], r.install(['libpng 1.2.*']))
    assert installed1 == installed3
    installed4 = r.install(['mypackage'], r.install(['libpng 1.5.*']))
    assert installed2 == installed4
    # unspecified python version should maximize libpng (v1.5), even though it has a lower timestamp
    installed5 = r.install(['mypackage'])
    assert installed2 == installed5

def test_nonexistent_deps():
    index2 = index.copy()
    p1 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    })
    p2 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    })
    p3 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.1'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.1'],
        'version': '1.0',
    })
    p4 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    })
    index2.update({p1: p1, p2: p2, p3: p3, p4: p4})
    index2 = {key: value for key, value in iteritems(index2)}
    r = Resolve(index2)

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('mypackage'))) == {
        'defaults::mypackage-1.0-py33_0',
        'defaults::mypackage-1.1-py33_0',
    }
    assert set(prec.dist_str() for prec in r.get_reduced_index(['mypackage'])) == {
        'defaults::mypackage-1.1-py33_0',
        'channel-1::nose-1.1.2-py33_0',
        'channel-1::nose-1.2.1-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.0-2',
        'channel-1::python-3.3.0-3',
        'channel-1::python-3.3.0-4',
        'channel-1::python-3.3.0-pro0',
        'channel-1::python-3.3.0-pro1',
        'channel-1::python-3.3.1-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    }

    target_result = r.install(['mypackage'])
    assert target_result == r.install(['mypackage 1.1'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == [
        'defaults::mypackage-1.1-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]
    assert raises(ResolvePackageNotFound, lambda: r.install(['mypackage 1.0']))
    assert raises(ResolvePackageNotFound, lambda: r.install(['mypackage 1.0', 'burgertime 1.0']))

    target_result = r.install(['anotherpackage 1.0'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == [
        'defaults::anotherpackage-1.0-py33_0',
        'defaults::mypackage-1.1-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    target_result = r.install(['anotherpackage'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == [
        'defaults::anotherpackage-2.0-py33_0',
        'defaults::mypackage-1.1-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    # This time, the latest version is messed up
    index3 = index.copy()
    p5 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*', 'notarealpackage 2.0*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.1',
    })
    p6 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'python 3.3*'],
        'name': 'mypackage',
        'requires': ['nose 1.2.1', 'python 3.3'],
        'version': '1.0',
    })
    p7 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage 1.0'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage 1.0'],
        'version': '1.0',
    })
    p8 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['nose', 'mypackage'],
        'name': 'anotherpackage',
        'requires': ['nose', 'mypackage'],
        'version': '2.0',
    })
    index3.update({p5: p5, p6: p6, p7: p7, p8: p8})
    index3 = {key: value for key, value in iteritems(index3)}
    r = Resolve(index3)

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('mypackage'))) == {
        'defaults::mypackage-1.0-py33_0',
        'defaults::mypackage-1.1-py33_0',
        }
    assert set(prec.dist_str() for prec in r.get_reduced_index(['mypackage']).keys()) == {
        'defaults::mypackage-1.0-py33_0',
        'channel-1::nose-1.1.2-py33_0',
        'channel-1::nose-1.2.1-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.0-2',
        'channel-1::python-3.3.0-3',
        'channel-1::python-3.3.0-4',
        'channel-1::python-3.3.0-pro0',
        'channel-1::python-3.3.0-pro1',
        'channel-1::python-3.3.1-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    }

    target_result = r.install(['mypackage'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == [
        'defaults::mypackage-1.0-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]
    assert raises(ResolvePackageNotFound, lambda: r.install(['mypackage 1.1']))

    target_result = r.install(['anotherpackage 1.0'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == [
        'defaults::anotherpackage-1.0-py33_0',
        'defaults::mypackage-1.0-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    # If recursive checking is working correctly, this will give
    # anotherpackage 2.0, not anotherpackage 1.0
    target_result = r.install(['anotherpackage'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == [
        'defaults::anotherpackage-2.0-py33_0',
        'defaults::mypackage-1.0-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]


def test_install_package_with_feature():
    index2 = index.copy()
    p1 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'featurepy33_0',
        'build_number': 0,
        'depends': ['python 3.3*'],
        'name': 'mypackage',
        'version': '1.0',
        'features': 'feature',
    })
    p2 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': 'py33_0',
        'build_number': 0,
        'depends': ['python 3.3*'],
        'name': 'feature',
        'version': '1.0',
        'track_features': 'feature',
    })
    index2.update({p1: p1, p2: p2})
    index2 = {key: value for key, value in iteritems(index2)}
    r = Resolve(index2)

    # It should not raise
    r.install(['mypackage','feature 1.0'])


def test_unintentional_feature_downgrade():
    # See https://github.com/conda/conda/issues/6765
    # With the bug in place, this bad build of scipy
    # will be selected for install instead of a later
    # build of scipy 0.11.0.
    good_rec_match = MatchSpec("channel-1::scipy==0.11.0=np17py33_3")
    good_rec = next(prec for prec in itervalues(index) if good_rec_match.match(prec))
    bad_deps = tuple(d for d in good_rec.depends
                     if not d.startswith('numpy'))
    bad_rec = PackageRecord.from_objects(good_rec,
                                         build=good_rec.build.replace('_3','_x0'),
                                         build_number=0, depends=bad_deps,
                                         fn=good_rec.fn.replace('_3','_x0'),
                                         url=good_rec.url.replace('_3','_x0'))
    index2 = index.copy()
    index2[bad_rec] = bad_rec
    r = Resolve(index2)
    install = r.install(['scipy 0.11.0'])
    assert bad_rec not in install
    assert any(d.name == 'numpy' for d in install)


def test_circular_dependencies():
    index2 = index.copy()
    package1 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'depends': ['package2'],
        'name': 'package1',
        'requires': ['package2'],
        'version': '1.0',
    })
    index2[package1] = package1
    package2 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'depends': ['package1'],
        'name': 'package2',
        'requires': ['package1'],
        'version': '1.0',
    })
    index2[package2] = package2
    index2 = {key: value for key, value in iteritems(index2)}
    r = Resolve(index2)

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('package1'))) == {
        'defaults::package1-1.0-0',
    }
    assert set(prec.dist_str() for prec in r.get_reduced_index(['package1']).keys()) == {
        'defaults::package1-1.0-0',
        'defaults::package2-1.0-0',
    }
    result = r.install(['package1', 'package2'])
    assert r.install(['package1']) == r.install(['package2']) == result
    result = [r.dist_str() for r in result]
    assert result == [
        'defaults::package1-1.0-0',
        'defaults::package2-1.0-0',
    ]


def test_optional_dependencies():
    index2 = index.copy()
    p1 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'constrains': ['package2 >1.0'],
        'name': 'package1',
        'requires': ['package2'],
        'version': '1.0',
    })
    p2 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'depends': [],
        'name': 'package2',
        'requires': [],
        'version': '1.0',
    })
    p3 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'depends': [],
        'name': 'package2',
        'requires': [],
        'version': '2.0',
    })
    index2.update({p1: p1, p2: p2, p3: p3})
    index2 = {key: value for key, value in iteritems(index2)}
    r = Resolve(index2)

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('package1'))) == {
        'defaults::package1-1.0-0',
    }
    assert set(prec.dist_str() for prec in r.get_reduced_index(['package1']).keys()) == {
        'defaults::package1-1.0-0',
        'defaults::package2-2.0-0',
    }
    result = r.install(['package1'])
    result = [rec.dist_str() for rec in result]
    assert result == [
        'defaults::package1-1.0-0',
    ]
    result = r.install(['package1', 'package2'])
    assert result == r.install(['package1', 'package2 >1.0'])
    result = [rec.dist_str() for rec in result]
    assert result == [
        'defaults::package1-1.0-0',
        'defaults::package2-2.0-0',
    ]
    assert raises(UnsatisfiableError, lambda: r.install(['package1', 'package2 <2.0']))
    assert raises(UnsatisfiableError, lambda: r.install(['package1', 'package2 1.0']))


def test_irrational_version():
    result = r.install(['pytz 2012d', 'python 3*'], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::pytz-2012d-py33_0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]


def test_no_features():
    # Without this, there would be another solution including 'scipy-0.11.0-np16py26_p3.tar.bz2'.
    result = r.install(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::numpy-1.6.2-py26_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.6.8-6',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.11.0-np16py26_3',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    result = r.install(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*', MatchSpec(track_features='mkl')], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::mkl-rt-11.0-p0',           # This,
        'channel-1::numpy-1.6.2-py26_p4',      # this,
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.6.8-6',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.11.0-np16py26_p3', # and this are different.
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    index2 = index.copy()
    pandas = PackageRecord(**{
            "channel": "channel-1",
            "subdir": context.subdir,
            "md5": "0123456789",
            "fn": "doesnt-matter-here",
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
    index2[pandas] = pandas
    # Make it want to choose the pro version by having it be newer.
    numpy = PackageRecord(**{
            "channel": "channel-1",
            "subdir": context.subdir,
            "md5": "0123456789",
            "fn": "doesnt-matter-here",
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
    index2[numpy] = numpy

    index2 = {key: value for key, value in iteritems(index2)}
    r2 = Resolve(index2)

    # This should not pick any mkl packages (the difference here is that none
    # of the specs directly have mkl versions)
    result = r2.solve(['pandas 0.12.0 np16py27_0', 'python 2.7*'], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.6.2-py27_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.12.0-np16py27_0',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    result = r2.solve(['pandas 0.12.0 np16py27_0', 'python 2.7*', MatchSpec(track_features='mkl')], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::mkl-rt-11.0-p0',           # This
        'channel-1::numpy-1.6.2-py27_p5',      # and this are different.
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.12.0-np16py27_0',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]


@pytest.mark.skipif(datetime.now() < datetime(2018, 8, 1), reason="bogus test; talk with @mcg1969")
def test_multiple_solution():
    index2 = index.copy()
    fn = 'pandas-0.11.0-np16py27_1.tar.bz2'
    res1 = set([fn])
    for k in range(1,15):
        fn2 = Dist('%s_%d.tar.bz2'%(fn[:-8],k))
        index2[fn2] = index[Dist(add_defaults_if_no_channel(fn))]
        res1.add(fn2)
    index2 = {Dist(key): value for key, value in iteritems(index2)}
    r = Resolve(index2)
    res = r.solve(['pandas', 'python 2.7*', 'numpy 1.6*'], returnall=True)
    res = set([y for y in res if y.name.startswith('pandas')])
    assert len(res) <= len(res1)


def test_broken_install():
    installed = r.install(['pandas', 'python 2.7*', 'numpy 1.6*'])
    _installed = [rec.dist_str() for rec in installed]
    assert _installed == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.6.2-py27_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.11.0-np16py27_1',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.12.0-np16py27_0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    # Add an incompatible numpy; installation should be untouched
    installed1 = list(installed)
    incompat_numpy_rec = next(
        rec for rec in index.values() if rec['name'] == 'numpy' and rec['version'] == '1.7.1' and rec['build'] == 'py33_p0'
    )
    installed1[1] = incompat_numpy_rec
    assert set(r.install([], installed1)) == set(installed1)
    assert r.install(['numpy 1.6*'], installed1) == installed  # adding numpy spec again snaps the packages back to a consistent state

    # Add an incompatible pandas; installation should be untouched, then fixed
    installed2 = list(installed)
    pandas_matcher_1 = MatchSpec('channel-1::pandas==0.11.0=np17py27_1')
    pandas_prec_1 = next(prec for prec in index if pandas_matcher_1.match(prec))
    installed2[3] = pandas_prec_1
    assert set(r.install([], installed2)) == set(installed2)
    assert r.install(['pandas'], installed2) == installed

    # Removing pandas should fix numpy, since pandas depends on it
    numpy_matcher = MatchSpec('channel-1::numpy==1.7.1=py33_p0')
    numpy_prec = next(prec for prec in index if numpy_matcher.match(prec))
    installed3 = list(installed)
    installed3[1] = numpy_prec
    installed3[3] = pandas_prec_1
    installed4 = r.remove(['pandas'], installed3)
    assert r.bad_installed(installed4, [])[0] is None

    # Tests removed involving packages not in the index, because we
    # always insure installed packages _are_ in the index


def test_remove():
    installed = r.install(['pandas', 'python 2.7*'])
    _installed = [rec.dist_str() for rec in installed]
    assert _installed == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.7.1-py27_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.11.0-np17py27_1',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.12.0-np17py27_0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    result = r.remove(['pandas'], installed=installed)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.7.1-py27_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.12.0-np17py27_0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    # Pandas requires numpy
    result = r.remove(['numpy'], installed=installed)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]


def test_channel_priority_1():
    channels = (
        Channel("channel-A"),
        Channel("channel-1"),
        Channel("channel-B"),
    )

    index2 = index.copy()
    pandas_matcher_1 = MatchSpec('channel-1::pandas==0.11.0=np17py27_1')
    pandas_prec_1 = next(prec for prec in index2 if pandas_matcher_1.match(prec))
    record_0 = pandas_prec_1

    pandas_matcher_2 = MatchSpec('channel-1::pandas==0.10.1=np17py27_0')
    pandas_prec_2 = next(prec for prec in index2 if pandas_matcher_2.match(prec))
    record_1 = pandas_prec_2
    record_2 = PackageRecord.from_objects(record_1, channel=Channel("channel-A"))

    index2[record_2] = record_2

    spec = ['pandas', 'python 2.7*']

    r2 = Resolve(index2, channels=channels)

    with env_var("CONDA_CHANNEL_PRIORITY", "True", reset_context):
        # Should select the "record_2" because it has highest channel priority, even though
        # 'channel-1::pandas-0.11.1-np17py27_0.tar.bz2' would otherwise be preferred
        installed1 = r2.install(spec)
        assert record_2 in installed1
        assert record_1 not in installed1
        assert record_0 not in installed1

        r3 = Resolve(index2, channels=reversed(channels))
        installed2 = r3.install(spec)
        assert record_0 in installed2
        assert record_2 not in installed2
        assert record_1 not in installed2


    with env_var("CONDA_CHANNEL_PRIORITY", "False", reset_context):
        # Should also select the newer package because we have
        # turned off channel priority altogether
        r2._reduced_index_cache.clear()
        installed3 = r2.install(spec)
        assert record_0 in installed3
        assert record_1 not in installed3
        assert record_2 not in installed3

    assert installed1 != installed2
    assert installed1 != installed3
    assert installed2 == installed3


def test_channel_priority_2():
    this_index = index.copy()
    index3, r3 = get_index_r_3()
    this_index.update(index3)
    spec = ['pandas', 'python 2.7*']
    channels = (Channel('channel-1'), Channel('channel-3'))
    this_r = Resolve(this_index, channels=channels)
    with env_var("CONDA_CHANNEL_PRIORITY", "True", reset_context):
        dists = this_r.get_reduced_index(spec)
        r2 = Resolve(dists, True, True, channels=channels)
        C = r2.gen_clauses()
        eqc, eqv, eqb, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
        eqc = {key: value for key, value in iteritems(eqc)}
        assert eqc == {
            'channel-3::openssl-1.0.1c-0': 1,
            'channel-3::openssl-1.0.1g-0': 1,
            'channel-3::openssl-1.0.1h-0': 1,
            'channel-3::openssl-1.0.1h-1': 1,
            'channel-3::openssl-1.0.1j-0': 1,
            'channel-3::openssl-1.0.1j-1': 1,
            'channel-3::openssl-1.0.1j-2': 1,
            'channel-3::openssl-1.0.1j-3': 1,
            'channel-3::openssl-1.0.1j-4': 1,
            'channel-3::openssl-1.0.1j-5': 1,
            'channel-3::openssl-1.0.1k-0': 1,
            'channel-3::openssl-1.0.1k-1': 1,
            'channel-3::openssl-1.0.2d-0': 1,
            'channel-3::openssl-1.0.2e-0': 1,
            'channel-3::openssl-1.0.2f-0': 1,
            'channel-3::openssl-1.0.2g-0': 1,
            'channel-3::openssl-1.0.2h-0': 1,
            'channel-3::openssl-1.0.2h-1': 1,
            'channel-3::openssl-1.0.2i-0': 1,
            'channel-3::openssl-1.0.2j-0': 1,
            'channel-3::openssl-1.0.2k-0': 1,
            'channel-3::openssl-1.0.2k-1': 1,
            'channel-3::openssl-1.0.2k-2': 1,
            'channel-3::openssl-1.0.2l-0': 1,
            'channel-3::python-2.7.10-0': 1,
            'channel-3::python-2.7.10-1': 1,
            'channel-3::python-2.7.10-2': 1,
            'channel-3::python-2.7.11-0': 1,
            'channel-3::python-2.7.11-5': 1,
            'channel-3::python-2.7.12-0': 1,
            'channel-3::python-2.7.12-1': 1,
            'channel-3::python-2.7.13-0': 1,
            'channel-3::python-2.7.3-2': 1,
            'channel-3::python-2.7.3-3': 1,
            'channel-3::python-2.7.3-4': 1,
            'channel-3::python-2.7.3-5': 1,
            'channel-3::python-2.7.3-6': 1,
            'channel-3::python-2.7.3-7': 1,
            'channel-3::python-2.7.4-0': 1,
            'channel-3::python-2.7.5-0': 1,
            'channel-3::python-2.7.5-1': 1,
            'channel-3::python-2.7.5-2': 1,
            'channel-3::python-2.7.5-3': 1,
            'channel-3::python-2.7.6-0': 1,
            'channel-3::python-2.7.6-1': 1,
            'channel-3::python-2.7.6-2': 1,
            'channel-3::python-2.7.7-0': 1,
            'channel-3::python-2.7.7-2': 1,
            'channel-3::python-2.7.8-0': 1,
            'channel-3::python-2.7.8-1': 1,
            'channel-3::python-2.7.9-0': 1,
            'channel-3::python-2.7.9-1': 1,
            'channel-3::python-2.7.9-2': 1,
            'channel-3::python-2.7.9-3': 1,
            'channel-3::readline-6.2-0': 1,
            'channel-3::readline-6.2-2': 1,
            'channel-3::sqlite-3.13.0-0': 1,
            'channel-3::sqlite-3.7.13-0': 1,
            'channel-3::sqlite-3.8.4.1-0': 1,
            'channel-3::sqlite-3.8.4.1-1': 1,
            'channel-3::sqlite-3.9.2-0': 1,
            'channel-3::system-5.8-0': 1,
            'channel-3::system-5.8-1': 1,
            'channel-3::system-5.8-2': 1,
            'channel-3::tk-8.5.13-0': 1,
            'channel-3::tk-8.5.15-0': 1,
            'channel-3::tk-8.5.18-0': 1,
            'channel-3::zlib-1.2.7-0': 1,
            'channel-3::zlib-1.2.7-1': 1,
            'channel-3::zlib-1.2.7-2': 1,
            'channel-3::zlib-1.2.8-0': 1,
            'channel-3::zlib-1.2.8-3': 1,
        }
        installed_w_priority = [prec.dist_str() for prec in this_r.install(spec)]
        assert installed_w_priority == [
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::pandas-0.11.0-np17py27_1',
            'channel-1::python-2.7.5-0',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::readline-6.2-0',
            'channel-1::scipy-0.12.0-np17py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
        ]

    with env_var("CONDA_CHANNEL_PRIORITY", "False", reset_context):
        dists = this_r.get_reduced_index(spec)
        r2 = Resolve(dists, True, True, channels=channels)
        C = r2.gen_clauses()
        eqc, eqv, eqb, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
        eqc = {key: value for key, value in iteritems(eqc)}
        assert eqc == {
            'channel-1::dateutil-1.5-py27_0': 1,
            'channel-1::nose-1.1.2-py27_0': 2,
            'channel-1::nose-1.2.1-py27_0': 1,
            'channel-1::numpy-1.6.2-py27_1': 4,
            'channel-1::numpy-1.6.2-py27_3': 4,
            'channel-1::numpy-1.6.2-py27_4': 4,
            'channel-1::numpy-1.6.2-py27_ce0': 4,
            'channel-1::numpy-1.6.2-py27_p1': 4,
            'channel-1::numpy-1.6.2-py27_p3': 4,
            'channel-1::numpy-1.6.2-py27_p4': 4,
            'channel-1::numpy-1.6.2-py27_pro0': 4,
            'channel-1::numpy-1.7.0-py27_0': 1,
            'channel-1::numpy-1.7.0-py27_p0': 1,
            'channel-1::numpy-1.7.0b2-py27_ce0': 3,
            'channel-1::numpy-1.7.0b2-py27_pro0': 3,
            'channel-1::numpy-1.7.0rc1-py27_0': 2,
            'channel-1::numpy-1.7.0rc1-py27_p0': 2,
            'channel-1::openssl-1.0.1c-0': 13,
            'channel-1::pandas-0.10.0-np16py27_0': 2,
            'channel-1::pandas-0.10.0-np17py27_0': 2,
            'channel-1::pandas-0.10.1-np16py27_0': 1,
            'channel-1::pandas-0.10.1-np17py27_0': 1,
            'channel-1::pandas-0.8.1-np16py27_0': 5,
            'channel-1::pandas-0.8.1-np17py27_0': 5,
            'channel-1::pandas-0.9.0-np16py27_0': 4,
            'channel-1::pandas-0.9.0-np17py27_0': 4,
            'channel-1::pandas-0.9.1-np16py27_0': 3,
            'channel-1::pandas-0.9.1-np17py27_0': 3,
            'channel-1::python-2.7.3-2': 10,
            'channel-1::python-2.7.3-3': 10,
            'channel-1::python-2.7.3-4': 10,
            'channel-1::python-2.7.3-5': 10,
            'channel-1::python-2.7.3-6': 10,
            'channel-1::python-2.7.3-7': 10,
            'channel-1::python-2.7.4-0': 9,
            'channel-1::python-2.7.5-0': 8,
            'channel-1::pytz-2012d-py27_0': 2,
            'channel-1::pytz-2012j-py27_0': 1,
            'channel-1::scipy-0.11.0-np16py27_2': 1,
            'channel-1::scipy-0.11.0-np16py27_3': 1,
            'channel-1::scipy-0.11.0-np16py27_ce1': 1,
            'channel-1::scipy-0.11.0-np16py27_p2': 1,
            'channel-1::scipy-0.11.0-np16py27_p3': 1,
            'channel-1::scipy-0.11.0-np16py27_pro0': 1,
            'channel-1::scipy-0.11.0-np16py27_pro1': 1,
            'channel-1::scipy-0.11.0-np17py27_2': 1,
            'channel-1::scipy-0.11.0-np17py27_3': 1,
            'channel-1::scipy-0.11.0-np17py27_ce0': 1,
            'channel-1::scipy-0.11.0-np17py27_ce1': 1,
            'channel-1::scipy-0.11.0-np17py27_p2': 1,
            'channel-1::scipy-0.11.0-np17py27_p3': 1,
            'channel-1::scipy-0.11.0-np17py27_pro0': 1,
            'channel-1::scipy-0.11.0-np17py27_pro1': 1,
            'channel-1::six-1.2.0-py27_0': 1,
            'channel-1::sqlite-3.7.13-0': 3,
            'channel-1::tk-8.5.13-0': 2,
            'channel-1::zlib-1.2.7-0': 1,
            'channel-3::openssl-1.0.1c-0': 13,
            'channel-3::openssl-1.0.1g-0': 12,
            'channel-3::openssl-1.0.1h-0': 11,
            'channel-3::openssl-1.0.1h-1': 11,
            'channel-3::openssl-1.0.1j-0': 10,
            'channel-3::openssl-1.0.1j-1': 10,
            'channel-3::openssl-1.0.1j-2': 10,
            'channel-3::openssl-1.0.1j-3': 10,
            'channel-3::openssl-1.0.1j-4': 10,
            'channel-3::openssl-1.0.1j-5': 10,
            'channel-3::openssl-1.0.1k-0': 9,
            'channel-3::openssl-1.0.1k-1': 9,
            'channel-3::openssl-1.0.2d-0': 8,
            'channel-3::openssl-1.0.2e-0': 7,
            'channel-3::openssl-1.0.2f-0': 6,
            'channel-3::openssl-1.0.2g-0': 5,
            'channel-3::openssl-1.0.2h-0': 4,
            'channel-3::openssl-1.0.2h-1': 4,
            'channel-3::openssl-1.0.2i-0': 3,
            'channel-3::openssl-1.0.2j-0': 2,
            'channel-3::openssl-1.0.2k-0': 1,
            'channel-3::openssl-1.0.2k-1': 1,
            'channel-3::openssl-1.0.2k-2': 1,
            'channel-3::python-2.7.10-0': 3,
            'channel-3::python-2.7.10-1': 3,
            'channel-3::python-2.7.10-2': 3,
            'channel-3::python-2.7.11-0': 2,
            'channel-3::python-2.7.11-5': 2,
            'channel-3::python-2.7.12-0': 1,
            'channel-3::python-2.7.12-1': 1,
            'channel-3::python-2.7.3-2': 10,
            'channel-3::python-2.7.3-3': 10,
            'channel-3::python-2.7.3-4': 10,
            'channel-3::python-2.7.3-5': 10,
            'channel-3::python-2.7.3-6': 10,
            'channel-3::python-2.7.3-7': 10,
            'channel-3::python-2.7.4-0': 9,
            'channel-3::python-2.7.5-0': 8,
            'channel-3::python-2.7.5-1': 8,
            'channel-3::python-2.7.5-2': 8,
            'channel-3::python-2.7.5-3': 8,
            'channel-3::python-2.7.6-0': 7,
            'channel-3::python-2.7.6-1': 7,
            'channel-3::python-2.7.6-2': 7,
            'channel-3::python-2.7.7-0': 6,
            'channel-3::python-2.7.7-2': 6,
            'channel-3::python-2.7.8-0': 5,
            'channel-3::python-2.7.8-1': 5,
            'channel-3::python-2.7.9-0': 4,
            'channel-3::python-2.7.9-1': 4,
            'channel-3::python-2.7.9-2': 4,
            'channel-3::python-2.7.9-3': 4,
            'channel-3::sqlite-3.7.13-0': 3,
            'channel-3::sqlite-3.8.4.1-0': 2,
            'channel-3::sqlite-3.8.4.1-1': 2,
            'channel-3::sqlite-3.9.2-0': 1,
            'channel-3::tk-8.5.13-0': 2,
            'channel-3::tk-8.5.15-0': 1,
            'channel-3::zlib-1.2.7-0': 1,
            'channel-3::zlib-1.2.7-1': 1,
            'channel-3::zlib-1.2.7-2': 1,
        }
        installed_wo_priority = set([prec.dist_str() for prec in this_r.install(spec)])
        assert installed_wo_priority == {
            'channel-3::openssl-1.0.2l-0',
            'channel-3::python-2.7.13-0',
            'channel-3::sqlite-3.13.0-0',
            'channel-3::tk-8.5.18-0',
            'channel-3::zlib-1.2.8-3',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::pandas-0.11.0-np17py27_1',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::readline-6.2-0',
            'channel-1::scipy-0.12.0-np17py27_0',
            'channel-1::six-1.3.0-py27_0',
        }


def test_dependency_sort():
    specs = ['pandas','python 2.7*','numpy 1.6*']
    installed = r.install(specs)
    must_have = {prec.name: prec for prec in installed}
    installed = r.dependency_sort(must_have)

    results_should_be = [
        'channel-1::openssl-1.0.1c-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
        'channel-1::python-2.7.5-0',
        'channel-1::numpy-1.6.2-py27_4',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::scipy-0.12.0-np16py27_0',
        'channel-1::pandas-0.11.0-np16py27_1'
    ]
    assert len(installed) == len(results_should_be)
    assert [prec.dist_str() for prec in installed] == results_should_be


def test_update_deps():
    installed = r.install(['python 2.7*', 'numpy 1.6*', 'pandas 0.10.1'])
    result = [rec.dist_str() for rec in installed]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.6.2-py27_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.10.1-np16py27_0',
        'channel-1::python-2.7.5-0',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.11.0-np16py27_3',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    # scipy, and pandas should all be updated here. pytz is a new
    # dependency of pandas. But numpy does not _need_ to be updated
    # to get the latest version of pandas, so it stays put.
    result = r.install(['pandas', 'python 2.7*'], installed=installed, update_deps=True, returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.6.2-py27_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.11.0-np16py27_1',
        'channel-1::python-2.7.5-0',
        'channel-1::pytz-2013b-py27_0',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.12.0-np16py27_0',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]

    # pandas should be updated here. However, it's going to try to not update
    # scipy, so it won't be updated to the latest version (0.11.0).
    result = r.install(['pandas', 'python 2.7*'], installed=installed, update_deps=False, returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == [
        'channel-1::dateutil-2.1-py27_1',
        'channel-1::numpy-1.6.2-py27_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::pandas-0.10.1-np16py27_0',
        'channel-1::python-2.7.5-0',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.11.0-np16py27_3',
        'channel-1::six-1.3.0-py27_0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ]


def test_surplus_features_1():
    index = {
        PackageRecord(**{
            'name': 'feature',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'track_features': 'feature',
        }),
        PackageRecord(**{
            'name': 'package1',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'features': 'feature',
        }),
        PackageRecord(**{
            'name': 'package2',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'depends': ['package1'],
            'features': 'feature',
        }),
        PackageRecord(**{
            'name': 'package2',
            'version': '2.0',
            'build': '0',
            'build_number': 0,
            'features': 'feature',
        }),
    }
    index = {prec: prec for prec in index}
    r = Resolve({key: value for key, value in iteritems(index)})
    install = r.install(['package2', 'feature'])
    assert 'package1' not in set(d.name for d in install)


def test_surplus_features_2():
    index = {
        PackageRecord(**{
            'name': 'feature',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'track_features': 'feature',
        }),
        PackageRecord(**{
            'name': 'package1',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'features': 'feature',
        }),
        PackageRecord(**{
            'name': 'package2',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'depends': ['package1'],
            'features': 'feature',
        }),
        PackageRecord(**{
            'name': 'package2',
            'version': '1.0',
            'build': '1',
            'build_number': 1,
            'features': 'feature',
        }),
    }
    index = {prec: prec for prec in index}
    r = Resolve({key: value for key, value in iteritems(index)})
    install = r.install(['package2', 'feature'])
    assert 'package1' not in set(d.name for d in install)
