# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, print_function

from collections import OrderedDict
from os.path import isdir, join
from pprint import pprint
import unittest

import pytest

from conda.base.context import context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import iteritems, itervalues
from conda.common.io import env_var
from conda.exceptions import UnsatisfiableError
from conda.gateways.disk.read import read_python_record
from conda.models.channel import Channel
from conda.models.enums import PackageType
from conda.models.records import PackageRecord
from conda.resolve import MatchSpec, Resolve, ResolvePackageNotFound
from conda.testing.helpers import TEST_DATA_DIR, add_subdir, add_subdir_to_iter, \
    get_index_r_1, get_index_r_4, raises

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
        assert installed == add_subdir_to_iter([
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
        ])

    def test_iopro_mkl(self):
        installed = r.install(['iopro 1.4*', 'python 2.7*', 'numpy 1.7*', MatchSpec(track_features='mkl')], returnall=True)
        installed = [prec.dist_str() for prec in installed]
        assert installed == add_subdir_to_iter([
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
        ])

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
        assert add_subdir('channel-1::scipy-0.12.0-np17py27_p0') in dist_strs

    def test_anaconda_nomkl(self):
        precs = r.install(['anaconda 1.5.0', 'python 2.7*', 'numpy 1.7*'])
        assert len(precs) == 107
        dist_strs = [prec.dist_str() for prec in precs]
        assert add_subdir('channel-1::scipy-0.12.0-np17py27_0') in dist_strs


def test_generate_eq_1():
    # avoid cache from other tests which may have different result
    r._reduced_index_cache = {}

    reduced_index = r.get_reduced_index((MatchSpec('anaconda'), ))
    r2 = Resolve(reduced_index, True)
    C = r2.gen_clauses()
    eqc, eqv, eqb,  eqa, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
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
    assert eqv == add_subdir_to_iter({
        'channel-1::anaconda-1.4.0-np15py27_0': 1,
        'channel-1::anaconda-1.4.0-np16py27_0': 1,
        'channel-1::anaconda-1.4.0-np17py27_0': 1,
        'channel-1::anaconda-1.4.0-np17py33_0': 1,
        'channel-1::astropy-0.2-np15py27_0': 1,
        'channel-1::astropy-0.2-np16py27_0': 1,
        'channel-1::astropy-0.2-np17py27_0': 1,
        'channel-1::astropy-0.2-np17py33_0': 1,
        'channel-1::biopython-1.60-np15py27_0': 1,
        'channel-1::biopython-1.60-np16py27_0': 1,
        'channel-1::biopython-1.60-np17py27_0': 1,
        'channel-1::bitarray-0.8.0-py27_0': 1,
        'channel-1::bitarray-0.8.0-py33_0': 1,
        'channel-1::boto-2.8.0-py27_0': 1,
        'channel-1::conda-1.4.4-py27_0': 1,
        'channel-1::cython-0.18-py27_0': 1,
        'channel-1::cython-0.18-py33_0': 1,
        'channel-1::distribute-0.6.34-py27_1': 1,
        'channel-1::distribute-0.6.34-py33_1': 1,
        'channel-1::ipython-0.13.1-py27_1': 1,
        'channel-1::ipython-0.13.1-py33_1': 1,
        'channel-1::llvmpy-0.11.1-py27_0': 1,
        'channel-1::llvmpy-0.11.1-py33_0': 1,
        'channel-1::lxml-3.0.2-py27_0': 1,
        'channel-1::lxml-3.0.2-py33_0': 1,
        'channel-1::matplotlib-1.2.0-np15py27_1': 1,
        'channel-1::matplotlib-1.2.0-np16py27_1': 1,
        'channel-1::matplotlib-1.2.0-np17py27_1': 1,
        'channel-1::matplotlib-1.2.0-np17py33_1': 1,
        'channel-1::nose-1.2.1-py27_0': 1,
        'channel-1::nose-1.2.1-py33_0': 1,
        'channel-1::numba-0.7.0-np16py27_1': 1,
        'channel-1::numba-0.7.0-np17py27_1': 1,
        'channel-1::numpy-1.5.1-py27_3': 3,
        'channel-1::numpy-1.6.2-py26_4': 2,
        'channel-1::numpy-1.6.2-py27_3': 2,
        'channel-1::numpy-1.6.2-py27_4': 2,
        'channel-1::numpy-1.7.0-py27_0': 1,
        'channel-1::numpy-1.7.0-py33_0': 1,
        'channel-1::pandas-0.10.1-np16py27_0': 1,
        'channel-1::pandas-0.10.1-np17py27_0': 1,
        'channel-1::pandas-0.10.1-np17py33_0': 1,
        'channel-1::pip-1.2.1-py27_1': 1,
        'channel-1::pip-1.2.1-py33_1': 1,
        'channel-1::psutil-0.6.1-py27_0': 1,
        'channel-1::psutil-0.6.1-py33_0': 1,
        'channel-1::pyflakes-0.6.1-py27_0': 1,
        'channel-1::pyflakes-0.6.1-py33_0': 1,
        'channel-1::python-2.6.8-6': 4,
        'channel-1::python-2.7.3-7': 3,
        'channel-1::python-2.7.4-0': 2,
        'channel-1::python-3.3.0-4': 1,
        'channel-1::pytz-2012j-py27_0': 1,
        'channel-1::pytz-2012j-py33_0': 1,
        'channel-1::requests-0.13.9-py27_0': 1,
        'channel-1::requests-0.13.9-py33_0': 1,
        'channel-1::scikit-learn-0.13-np15py27_1': 1,
        'channel-1::scikit-learn-0.13-np16py27_1': 1,
        'channel-1::scikit-learn-0.13-np17py27_1': 1,
        'channel-1::scipy-0.11.0-np15py27_3': 1,
        'channel-1::scipy-0.11.0-np16py27_3': 1,
        'channel-1::scipy-0.11.0-np17py27_3': 1,
        'channel-1::scipy-0.11.0-np17py33_3': 1,
        'channel-1::six-1.2.0-py27_0': 1,
        'channel-1::six-1.2.0-py33_0': 1,
        'channel-1::spyder-2.1.13-py27_0': 1,
        'channel-1::sqlalchemy-0.7.8-py27_0': 1,
        'channel-1::sqlalchemy-0.7.8-py33_0': 1,
        'channel-1::sympy-0.7.1-py27_0': 1,
        'channel-1::tornado-2.4.1-py27_0': 1,
        'channel-1::tornado-2.4.1-py33_0': 1,
        'channel-1::xlrd-0.9.0-py27_0': 1,
        'channel-1::xlrd-0.9.0-py33_0': 1,
        'channel-1::xlwt-0.7.4-py27_0': 1
    })
    assert eqb == add_subdir_to_iter({
        'channel-1::cubes-0.10.2-py27_0': 1,
        'channel-1::dateutil-2.1-py27_0': 1,
        'channel-1::dateutil-2.1-py33_0': 1,
        'channel-1::gevent-websocket-0.3.6-py27_1': 1,
        'channel-1::gevent_zeromq-0.2.5-py27_1': 1,
        'channel-1::numexpr-2.0.1-np16py27_2': 1,
        'channel-1::numexpr-2.0.1-np17py27_2': 1,
        'channel-1::numpy-1.6.2-py27_3': 1,
        'channel-1::pycurl-7.19.0-py27_0': 1,
        'channel-1::pysal-1.5.0-np15py27_0': 1,
        'channel-1::pysal-1.5.0-np16py27_0': 1,
        'channel-1::pysal-1.5.0-np17py27_0': 1,
        'channel-1::pytest-2.3.4-py27_0': 1,
        'channel-1::pyzmq-2.2.0.1-py27_0': 1,
        'channel-1::pyzmq-2.2.0.1-py33_0': 1,
        'channel-1::scikit-image-0.8.2-np16py27_0': 1,
        'channel-1::scikit-image-0.8.2-np17py27_0': 1,
        'channel-1::scikit-image-0.8.2-np17py33_0': 1,
        'channel-1::sphinx-1.1.3-py27_2': 1,
        'channel-1::sphinx-1.1.3-py33_2': 1,
        'channel-1::statsmodels-0.4.3-np16py27_0': 1,
        'channel-1::statsmodels-0.4.3-np17py27_0': 1,
        'channel-1::system-5.8-0': 1,
        'channel-1::theano-0.5.0-np15py27_0': 1,
        'channel-1::theano-0.5.0-np16py27_0': 1,
        'channel-1::theano-0.5.0-np17py27_0': 1,
        'channel-1::zeromq-2.2.0-0': 1
    })

    # No timestamps in the current data set
    assert eqt == {}


def test_pseudo_boolean():
    # The latest version of iopro, 1.5.0, was not built against numpy 1.5
    installed = r.install(['iopro', 'python 2.7*', 'numpy 1.5*'], returnall=True)
    installed = [rec.dist_str() for rec in installed]
    assert installed == add_subdir_to_iter([
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
    ])

    installed = r.install(['iopro', 'python 2.7*', 'numpy 1.5*', MatchSpec(track_features='mkl')], returnall=True)
    installed = [rec.dist_str() for rec in installed]
    assert installed == add_subdir_to_iter([
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
    ])


def test_get_dists():
    reduced_index = r.get_reduced_index((MatchSpec("anaconda 1.4.0"), ))
    dist_strs = [prec.dist_str() for prec in reduced_index]
    assert add_subdir('channel-1::anaconda-1.4.0-np17py27_0') in dist_strs
    assert add_subdir('channel-1::freetype-2.4.10-0') in dist_strs


def test_get_reduced_index_unmanageable():
    index, r = get_index_r_4()
    index = index.copy()
    channels = r.channels
    prefix_path = join(TEST_DATA_DIR, "env_metadata", "envpy27osx")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    anchor_file = "lib/python2.7/site-packages/requests-2.19.1-py2.7.egg/EGG-INFO/PKG-INFO"
    py_rec = read_python_record(prefix_path, anchor_file, "2.7")
    assert py_rec.package_type == PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE

    index[py_rec] = py_rec
    new_r = Resolve(index, channels=channels)
    reduced_index = new_r.get_reduced_index((MatchSpec("requests"),))
    new_r2 = Resolve(reduced_index, True, channels=channels)
    assert len(new_r2.groups["requests"]) == 1, new_r2.groups["requests"]


def test_unsat_from_r1():
    # scipy 0.12.0b1 is not built for numpy 1.5, only 1.6 and 1.7
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['numpy 1.5*', 'scipy 0.12.0b1'])
    assert "numpy=1.5" in str(excinfo.value)
    assert "scipy==0.12.0b1 -> numpy[version='1.6.*|1.7.*']" in str(excinfo.value)
    # numpy 1.5 does not have a python 3 package

    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['numpy 1.5*', 'python 3*'])
    assert "numpy=1.5 -> python[version='2.6.*|2.7.*']" in str(excinfo.value)
    assert "python=3" in str(excinfo.value)

    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['numpy 1.5*', 'numpy 1.6*'])
    assert "numpy=1.5" in str(excinfo.value)
    assert "numpy=1.6" in str(excinfo.value)


def simple_rec(name='a', version='1.0', depends=None, build='0',
               build_number=0, channel='channel-1'):
    if depends is None:
        depends = []
    return PackageRecord(**{
        'name': name,
        'version': version,
        'depends': depends,
        'build': build,
        'build_number': build_number,
        'channel': channel,
    })


def test_unsat_simple():
    # a and b depend on conflicting versions of c
    index = (
        simple_rec(name='a', depends=['c >=1,<2']),
        simple_rec(name='b', depends=['c >=2,<3']),
        simple_rec(name='c', version='1.0'),
        simple_rec(name='c', version='2.0'),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['a', 'b'])
    assert "a -> c[version='>=1,<2']" in str(excinfo.value)
    assert "b -> c[version='>=2,<3']" in str(excinfo.value)

def test_unsat_simple_dont_find_conflicts():
    # a and b depend on conflicting versions of c
    index = (
        simple_rec(name='a', depends=['c >=1,<2']),
        simple_rec(name='b', depends=['c >=2,<3']),
        simple_rec(name='c', version='1.0'),
        simple_rec(name='c', version='2.0'),
    )
    with env_var("CONDA_UNSATISFIABLE_HINTS", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        r = Resolve(OrderedDict((prec, prec) for prec in index))
        with pytest.raises(UnsatisfiableError) as excinfo:
            r.install(['a', 'b '])
        assert "a -> c[version='>=1,<2']" not in str(excinfo.value)
        assert "b -> c[version='>=2,<3']" not in str(excinfo.value)


def test_unsat_shortest_chain_1():
    index = (
        simple_rec(name='a', depends=['d', 'c <1.3.0']),
        simple_rec(name='b', depends=['c']),
        simple_rec(name='c', version='1.3.6',),
        simple_rec(name='c', version='1.2.8',),
        simple_rec(name='d', depends=['c >=0.8.0']),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['c=1.3.6', 'a', 'b'])
    assert "a -> c[version='<1.3.0']" in str(excinfo.value)
    assert "b -> c" in str(excinfo.value)
    assert "c=1.3.6" in str(excinfo.value)


def test_unsat_shortest_chain_2():
    index = (
        simple_rec(name='a', depends=['d', 'c >=0.8.0']),
        simple_rec(name='b', depends=['c']),
        simple_rec(name='c', version='1.3.6',),
        simple_rec(name='c', version='1.2.8',),
        simple_rec(name='d', depends=['c <1.3.0']),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['c=1.3.6', 'a', 'b'])
    assert "a -> d -> c[version='<1.3.0']" in str(excinfo.value)
    assert "b -> c" in str(excinfo.value)
    assert "c=1.3.6" in str(excinfo.value)


def test_unsat_shortest_chain_3():
    index = (
        simple_rec(name='a', depends=['f', 'e']),
        simple_rec(name='b', depends=['c']),
        simple_rec(name='c', version='1.3.6',),
        simple_rec(name='c', version='1.2.8',),
        simple_rec(name='d', depends=['c >=0.8.0']),
        simple_rec(name='e', depends=['c <1.3.0']),
        simple_rec(name='f', depends=['d']),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['c=1.3.6', 'a', 'b'])
    assert "a -> e -> c[version='<1.3.0']" in str(excinfo.value)
    assert "b -> c" in str(excinfo.value)
    assert "c=1.3.6" in str(excinfo.value)


def test_unsat_shortest_chain_4():
    index = (
        simple_rec(name='a', depends=['py =3.7.1']),
        simple_rec(name="py_req_1"),
        simple_rec(name="py_req_2"),
        simple_rec(name='py', version='3.7.1', depends=['py_req_1', 'py_req_2']),
        simple_rec(name='py', version='3.6.1', depends=['py_req_1', 'py_req_2']),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['a', 'py=3.6.1'])
    print(str(excinfo.value))
    assert "a -> py=3.7.1" in str(excinfo.value)
    assert "py=3.6.1" in str(excinfo.value)
    assert "py=3.6.1 -> py_req_2" not in str(excinfo.value)

def test_unsat_chain():
    # a -> b -> c=1.x -> d=1.x
    # e      -> c=2.x -> d=2.x
    index = (
        simple_rec(name='a', depends=['b']),
        simple_rec(name='b', depends=['c >=1,<2']),
        simple_rec(name='c', version='1.0', depends=['d >=1,<2']),
        simple_rec(name='d', version='1.0'),

        simple_rec(name='e', depends=['c >=2,<3']),
        simple_rec(name='c', version='2.0', depends=['d >=2,<3']),
        simple_rec(name='d', version='2.0'),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['a', 'e'])
    assert "a -> b -> c[version='>=1,<2']" in str(excinfo.value)
    assert "e -> c[version='>=2,<3']" in str(excinfo.value)


def test_unsat_any_two_not_three():
    # can install any two of a, b and c but not all three
    index = (
        simple_rec(name='a', version='1.0', depends=['d >=1,<2']),
        simple_rec(name='a', version='2.0', depends=['d >=2,<3']),

        simple_rec(name='b', version='1.0', depends=['d >=1,<2']),
        simple_rec(name='b', version='2.0', depends=['d >=3,<4']),

        simple_rec(name='c', version='1.0', depends=['d >=2,<3']),
        simple_rec(name='c', version='2.0', depends=['d >=3,<4']),

        simple_rec(name='d', version='1.0'),
        simple_rec(name='d', version='2.0'),
        simple_rec(name='d', version='3.0'),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    # a and b can be installed
    installed1 = r.install(['a', 'b'])
    assert any(k.name == 'a' and k.version == '1.0' for k in installed1)
    assert any(k.name == 'b' and k.version == '1.0' for k in installed1)
    # a and c can be installed
    installed1 = r.install(['a', 'c'])
    assert any(k.name == 'a' and k.version == '2.0' for k in installed1)
    assert any(k.name == 'c' and k.version == '1.0' for k in installed1)
    # b and c can be installed
    installed1 = r.install(['b', 'c'])
    assert any(k.name == 'b' and k.version == '2.0' for k in installed1)
    assert any(k.name == 'c' and k.version == '2.0' for k in installed1)
    # a, b and c cannot be installed
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['a', 'b', 'c'])

    assert "a -> d[version='>=1,<2|>=2,<3']" in str(excinfo.value)
    assert "b -> d[version='>=1,<2|>=3,<4']" in str(excinfo.value)
    assert "c -> d[version='>=2,<3|>=3,<4']" in str(excinfo.value)


def test_unsat_expand_single():
    # if install maps to a single package, examine its dependencies
    index = (
        simple_rec(name='a', depends=['b', 'c']),
        simple_rec(name='b', depends=['d >=1,<2']),
        simple_rec(name='c', depends=['d >=2,<3']),
        simple_rec(name='d', version='1.0'),
        simple_rec(name='d', version='2.0'),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    with pytest.raises(UnsatisfiableError) as excinfo:
        r.install(['a'])
    assert "b -> d[version='>=1,<2']" in str(excinfo.value)
    assert "c -> d[version='>=2,<3']" in str(excinfo.value)


def test_unsat_missing_dep():
    # an install target has a missing dependency
    index = (
        simple_rec(name='a', depends=['b', 'c']),
        simple_rec(name='b', depends=['c >=2,<3']),
        simple_rec(name='c', version='1.0'),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    # this raises ResolvePackageNotFound not UnsatisfiableError
    assert raises(UnsatisfiableError, lambda: r.install(['a', 'b']))


def test_unsat_channel_priority():
    # b depends on c 2.x which is only available in channel-2
    index = (
        simple_rec(name='a', version='1.0', depends=['c'], channel='channel-1'),
        simple_rec(name='b', version='1.0', depends=['c >=2,<3'], channel='channel-1'),
        simple_rec(name='c', version='1.0', channel='channel-1'),

        simple_rec(name='a', version='2.0', depends=['c'], channel='channel-2'),
        simple_rec(name='b', version='2.0', depends=['c >=2,<3'], channel='channel-2'),
        simple_rec(name='c', version='1.0', channel='channel-2'),
        simple_rec(name='c', version='2.0', channel='channel-2'),
    )
    channels = (
        Channel('channel-1'),  # higher priority
        Channel('channel-2'),  # lower priority, missing c 2.0
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index), channels=channels)
    with env_var("CONDA_CHANNEL_PRIORITY", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        # channel-1 a and b packages (1.0) installed
        installed1 = r.install(['a', 'b'])
        assert any(k.name == 'a' and k.version == '1.0' for k in installed1)
        assert any(k.name == 'b' and k.version == '1.0' for k in installed1)
    with env_var("CONDA_CHANNEL_PRIORITY", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        # no channel priority, largest version of a and b (2.0) installed
        installed1 = r.install(['a', 'b'])
        assert any(k.name == 'a' and k.version == '2.0' for k in installed1)
        assert any(k.name == 'b' and k.version == '2.0' for k in installed1)
    with env_var("CONDA_CHANNEL_PRIORITY", "STRICT", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with pytest.raises(UnsatisfiableError) as excinfo:
            r.install(['a', 'b'])
        assert "b -> c[version='>=2,<3']" in str(excinfo.value)


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

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('mypackage'))) == add_subdir_to_iter({
        'defaults::mypackage-1.0-py33_0',
        'defaults::mypackage-1.1-py33_0',
    })
    assert set(prec.dist_str() for prec in r.get_reduced_index((MatchSpec('mypackage'), ))) == add_subdir_to_iter({
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
    })

    target_result = r.install(['mypackage'])
    assert target_result == r.install(['mypackage 1.1'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == add_subdir_to_iter([
        'defaults::mypackage-1.1-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ])
    assert raises(ResolvePackageNotFound, lambda: r.install(['mypackage 1.0']))
    assert raises(ResolvePackageNotFound, lambda: r.install(['mypackage 1.0', 'burgertime 1.0']))

    target_result = r.install(['anotherpackage 1.0'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == add_subdir_to_iter([
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
    ])

    target_result = r.install(['anotherpackage'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == add_subdir_to_iter([
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
    ])

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

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('mypackage'))) == add_subdir_to_iter({
        'defaults::mypackage-1.0-py33_0',
        'defaults::mypackage-1.1-py33_0',
        })
    assert set(prec.dist_str() for prec in r.get_reduced_index((MatchSpec('mypackage'), )).keys()) ==\
           add_subdir_to_iter({
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
    })

    target_result = r.install(['mypackage'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == add_subdir_to_iter([
        'defaults::mypackage-1.0-py33_0',
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ])
    assert raises(ResolvePackageNotFound, lambda: r.install(['mypackage 1.1']))

    target_result = r.install(['anotherpackage 1.0'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == add_subdir_to_iter([
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
    ])

    # If recursive checking is working correctly, this will give
    # anotherpackage 2.0, not anotherpackage 1.0
    target_result = r.install(['anotherpackage'])
    target_result = [rec.dist_str() for rec in target_result]
    assert target_result == add_subdir_to_iter([
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
    ])


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

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('package1'))) == add_subdir_to_iter({
        'defaults::package1-1.0-0',
    })
    assert set(prec.dist_str() for prec in r.get_reduced_index((MatchSpec('package1'), )).keys()) == add_subdir_to_iter({
        'defaults::package1-1.0-0',
        'defaults::package2-1.0-0',
    })
    result = r.install(['package1', 'package2'])
    assert r.install(['package1']) == r.install(['package2']) == result
    result = [r.dist_str() for r in result]
    assert result == add_subdir_to_iter([
        'defaults::package1-1.0-0',
        'defaults::package2-1.0-0',
    ])


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

    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('package1'))) == add_subdir_to_iter({
        'defaults::package1-1.0-0',
    })
    assert set(prec.dist_str() for prec in r.get_reduced_index((MatchSpec('package1'), )).keys()) == add_subdir_to_iter({
        'defaults::package1-1.0-0',
        'defaults::package2-2.0-0',
    })
    result = r.install(['package1'])
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
        'defaults::package1-1.0-0',
    ])
    result = r.install(['package1', 'package2'])
    assert result == r.install(['package1', 'package2 >1.0'])
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
        'defaults::package1-1.0-0',
        'defaults::package2-2.0-0',
    ])
    assert raises(UnsatisfiableError, lambda: r.install(['package1', 'package2 <2.0']))
    assert raises(UnsatisfiableError, lambda: r.install(['package1', 'package2 1.0']))


def test_irrational_version():
    result = r.install(['pytz 2012d', 'python 3*'], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::pytz-2012d-py33_0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ])


@pytest.mark.flaky(reruns=5, reruns_delay=2)
def test_no_features():
    # Without this, there would be another solution including 'scipy-0.11.0-np16py26_p3.tar.bz2'.
    result = r.install(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*'], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
        'channel-1::numpy-1.6.2-py26_4',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.6.8-6',
        'channel-1::readline-6.2-0',
        'channel-1::scipy-0.11.0-np16py26_3',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
    ])

    result = r.install(['python 2.6*', 'numpy 1.6*', 'scipy 0.11*', MatchSpec(track_features='mkl')], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
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
    ])

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
    assert result == add_subdir_to_iter([
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
    ])

    result = r2.solve(['pandas 0.12.0 np16py27_0', 'python 2.7*', MatchSpec(track_features='mkl')], returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
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
    ])


def test_broken_install():
    installed = r.install(['pandas', 'python 2.7*', 'numpy 1.6*'])
    _installed = [rec.dist_str() for rec in installed]
    assert _installed == add_subdir_to_iter([
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
    ])

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


def test_pip_depends_removed_on_inconsistent_env():
    installed = r.install(['python 2.7*'])
    pkg_names = [p.name for p in installed]
    assert 'python' in pkg_names
    assert 'pip' not in pkg_names
    # add pip as python dependency
    for pkg in installed:
        if pkg.name == 'python':
            pkg.depends += ('pip', )
        assert pkg.name != 'pip'
    bad_pkgs = r.bad_installed(installed, [])[0]
    assert bad_pkgs is None


def test_remove():
    installed = r.install(['pandas', 'python 2.7*'])
    _installed = [rec.dist_str() for rec in installed]
    assert _installed == add_subdir_to_iter([
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
    ])

    result = r.remove(['pandas'], installed=installed)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
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
    ])

    # Pandas requires numpy
    result = r.remove(['numpy'], installed=installed)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
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
    ])


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

    with env_var("CONDA_CHANNEL_PRIORITY", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol):
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


    with env_var("CONDA_CHANNEL_PRIORITY", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
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


@pytest.mark.integration
def test_channel_priority_2():
    this_index = index.copy()
    index4, r4 = get_index_r_4()
    this_index.update(index4)
    spec = (MatchSpec('pandas'), MatchSpec('python 2.7*'))
    channels = (Channel('channel-1'), Channel('channel-3'))
    this_r = Resolve(this_index, channels=channels)
    with env_var("CONDA_CHANNEL_PRIORITY", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        dists = this_r.get_reduced_index(spec)
        r2 = Resolve(dists, True, channels=channels)
        C = r2.gen_clauses()
        eqc, eqv, eqb, eqa, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
        eqc = {key: value for key, value in iteritems(eqc)}
        pprint(eqc)
        assert eqc == add_subdir_to_iter({
            'channel-4::mkl-2017.0.4-h4c4d0af_0': 1,
            'channel-4::mkl-2018.0.0-hb491cac_4': 1,
            'channel-4::mkl-2018.0.1-h19d6760_4': 1,
            'channel-4::mkl-2018.0.2-1': 1,
            'channel-4::mkl-2018.0.3-1': 1,
            'channel-4::nose-1.3.7-py27_2': 1,
            'channel-4::nose-1.3.7-py27heec2199_2': 1,
            'channel-4::numpy-1.11.3-py27h1b885b7_8': 1,
            'channel-4::numpy-1.11.3-py27h1b885b7_9': 1,
            'channel-4::numpy-1.11.3-py27h28100ab_6': 1,
            'channel-4::numpy-1.11.3-py27h28100ab_7': 1,
            'channel-4::numpy-1.11.3-py27h28100ab_8': 1,
            'channel-4::numpy-1.11.3-py27h2aefc1b_8': 1,
            'channel-4::numpy-1.11.3-py27h2aefc1b_9': 1,
            'channel-4::numpy-1.11.3-py27h3dfced4_4': 1,
            'channel-4::numpy-1.11.3-py27hcd700cb_6': 1,
            'channel-4::numpy-1.11.3-py27hcd700cb_7': 1,
            'channel-4::numpy-1.11.3-py27hcd700cb_8': 1,
            'channel-4::numpy-1.12.1-py27h9378851_1': 1,
            'channel-4::numpy-1.13.1-py27hd1b6e02_2': 1,
            'channel-4::numpy-1.13.3-py27_nomklh2b20989_4': 1,
            'channel-4::numpy-1.13.3-py27_nomklhfe0a00b_0': 1,
            'channel-4::numpy-1.13.3-py27h3dfced4_2': 1,
            'channel-4::numpy-1.13.3-py27ha266831_3': 1,
            'channel-4::numpy-1.13.3-py27hbcc08e0_0': 1,
            'channel-4::numpy-1.13.3-py27hdbf6ddf_4': 1,
            'channel-4::numpy-1.14.0-py27_nomklh7cdd4dd_0': 1,
            'channel-4::numpy-1.14.0-py27h3dfced4_0': 1,
            'channel-4::numpy-1.14.0-py27h3dfced4_1': 1,
            'channel-4::numpy-1.14.0-py27ha266831_2': 1,
            'channel-4::numpy-1.14.1-py27_nomklh5cab86c_2': 1,
            'channel-4::numpy-1.14.1-py27_nomklh7cdd4dd_1': 1,
            'channel-4::numpy-1.14.1-py27h3dfced4_1': 1,
            'channel-4::numpy-1.14.1-py27ha266831_2': 1,
            'channel-4::numpy-1.14.2-py27_nomklh2b20989_0': 1,
            'channel-4::numpy-1.14.2-py27_nomklh2b20989_1': 1,
            'channel-4::numpy-1.14.2-py27hdbf6ddf_0': 1,
            'channel-4::numpy-1.14.2-py27hdbf6ddf_1': 1,
            'channel-4::numpy-1.14.3-py27h28100ab_1': 1,
            'channel-4::numpy-1.14.3-py27h28100ab_2': 1,
            'channel-4::numpy-1.14.3-py27hcd700cb_1': 1,
            'channel-4::numpy-1.14.3-py27hcd700cb_2': 1,
            'channel-4::numpy-1.14.4-py27h28100ab_0': 1,
            'channel-4::numpy-1.14.4-py27hcd700cb_0': 1,
            'channel-4::numpy-1.14.5-py27h1b885b7_4': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_0': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_1': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_2': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_3': 1,
            'channel-4::numpy-1.14.5-py27h2aefc1b_4': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_0': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_1': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_2': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_3': 1,
            'channel-4::numpy-1.15.0-py27h1b885b7_0': 1,
            'channel-4::numpy-1.15.0-py27h2aefc1b_0': 1,
            'channel-4::numpy-1.9.3-py27_nomklhbee5d10_3': 1,
            'channel-4::numpy-1.9.3-py27h28100ab_5': 1,
            'channel-4::numpy-1.9.3-py27h28100ab_6': 1,
            'channel-4::numpy-1.9.3-py27h28100ab_7': 1,
            'channel-4::numpy-1.9.3-py27h7e35acb_3': 1,
            'channel-4::numpy-1.9.3-py27hcd700cb_5': 1,
            'channel-4::numpy-1.9.3-py27hcd700cb_6': 1,
            'channel-4::numpy-1.9.3-py27hcd700cb_7': 1,
            'channel-4::openssl-1.0.2l-h077ae2c_5': 1,
            'channel-4::openssl-1.0.2l-h9d1a558_3': 1,
            'channel-4::openssl-1.0.2l-hd940f6d_1': 1,
            'channel-4::openssl-1.0.2m-h26d622b_1': 1,
            'channel-4::openssl-1.0.2m-h8cfc7e7_0': 1,
            'channel-4::openssl-1.0.2n-hb7f436b_0': 1,
            'channel-4::openssl-1.0.2o-h14c3975_1': 1,
            'channel-4::openssl-1.0.2o-h20670df_0': 1,
            'channel-4::openssl-1.0.2p-h14c3975_0': 1,
            'channel-4::pandas-0.20.3-py27h820b67f_2': 1,
            'channel-4::pandas-0.20.3-py27hfd1eabf_2': 1,
            'channel-4::pandas-0.21.0-py27he307072_1': 1,
            'channel-4::pandas-0.21.1-py27h38cdd7d_0': 1,
            'channel-4::pandas-0.22.0-py27hf484d3e_0': 1,
            'channel-4::pandas-0.23.0-py27h637b7d7_0': 1,
            'channel-4::pandas-0.23.1-py27h637b7d7_0': 1,
            'channel-4::pandas-0.23.2-py27h04863e7_0': 1,
            'channel-4::pandas-0.23.3-py27h04863e7_0': 1,
            'channel-4::pandas-0.23.4-py27h04863e7_0': 1,
            'channel-4::python-2.7.13-hac47a24_15': 1,
            'channel-4::python-2.7.13-heccc3f1_16': 1,
            'channel-4::python-2.7.13-hfff3488_13': 1,
            'channel-4::python-2.7.14-h1571d57_29': 1,
            'channel-4::python-2.7.14-h1571d57_30': 1,
            'channel-4::python-2.7.14-h1571d57_31': 1,
            'channel-4::python-2.7.14-h1aa7481_19': 1,
            'channel-4::python-2.7.14-h435b27a_18': 1,
            'channel-4::python-2.7.14-h89e7a4a_22': 1,
            'channel-4::python-2.7.14-h91f54f5_26': 1,
            'channel-4::python-2.7.14-h931c8b0_15': 1,
            'channel-4::python-2.7.14-h9b67528_20': 1,
            'channel-4::python-2.7.14-ha6fc286_23': 1,
            'channel-4::python-2.7.14-hc2b0042_21': 1,
            'channel-4::python-2.7.14-hdd48546_24': 1,
            'channel-4::python-2.7.14-hf918d8d_16': 1,
            'channel-4::python-2.7.15-h1571d57_0': 1,
            'channel-4::pytz-2017.2-py27hcac29fa_1': 1,
            'channel-4::pytz-2017.3-py27h001bace_0': 1,
            'channel-4::pytz-2018.3-py27_0': 1,
            'channel-4::pytz-2018.4-py27_0': 1,
            'channel-4::pytz-2018.5-py27_0': 1,
            'channel-4::readline-7.0-ha6073c6_4': 1,
            'channel-4::readline-7.0-hac23ff0_3': 1,
            'channel-4::readline-7.0-hb321a52_4': 1,
            'channel-4::six-1.10.0-py27hdcd7534_1': 1,
            'channel-4::six-1.11.0-py27_1': 1,
            'channel-4::six-1.11.0-py27h5f960f1_1': 1,
            'channel-4::sqlite-3.20.1-h6d8b0f3_1': 1,
            'channel-4::sqlite-3.20.1-haaaaaaa_4': 1,
            'channel-4::sqlite-3.20.1-hb898158_2': 1,
            'channel-4::sqlite-3.21.0-h1bed415_0': 1,
            'channel-4::sqlite-3.21.0-h1bed415_2': 1,
            'channel-4::sqlite-3.22.0-h1bed415_0': 1,
            'channel-4::sqlite-3.23.1-he433501_0': 1,
            'channel-4::sqlite-3.24.0-h84994c4_0': 1,
            'channel-4::tk-8.6.7-h5979e9b_1': 1,
            'channel-4::tk-8.6.7-hc745277_3': 1,
            'channel-4::zlib-1.2.11-ha838bed_2': 1,
            'channel-4::zlib-1.2.11-hfbfcf68_1': 1,
        })
        installed_w_priority = [prec.dist_str() for prec in this_r.install(spec)]
        pprint(installed_w_priority)
        assert installed_w_priority == add_subdir_to_iter([
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
        ])

    # setting strict actually doesn't do anything here; just ensures it's not 'disabled'
    with env_var("CONDA_CHANNEL_PRIORITY", "strict", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        dists = this_r.get_reduced_index(spec)
        r2 = Resolve(dists, True, channels=channels)
        C = r2.gen_clauses()

        eqc, eqv, eqb, eqa, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
        eqc = {key: value for key, value in iteritems(eqc)}
        assert eqc == {}, eqc
        installed_w_strict = [prec.dist_str() for prec in this_r.install(spec)]
        assert installed_w_strict == add_subdir_to_iter([
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
        ]), installed_w_strict

    with env_var("CONDA_CHANNEL_PRIORITY", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        dists = this_r.get_reduced_index(spec)
        r2 = Resolve(dists, True, channels=channels)
        C = r2.gen_clauses()
        eqc, eqv, eqb, eqa, eqt = r2.generate_version_metrics(C, list(r2.groups.keys()))
        eqc = {key: value for key, value in iteritems(eqc)}
        pprint(eqc)
        assert eqc == add_subdir_to_iter({
            'channel-1::dateutil-1.5-py27_0': 1,
            'channel-1::mkl-10.3-0': 6,
            'channel-1::mkl-10.3-p1': 6,
            'channel-1::mkl-10.3-p2': 6,
            'channel-1::mkl-11.0-np16py27_p0': 5,
            'channel-1::mkl-11.0-np16py27_p1': 5,
            'channel-1::mkl-11.0-np17py27_p0': 5,
            'channel-1::mkl-11.0-np17py27_p1': 5,
            'channel-1::nose-1.1.2-py27_0': 3,
            'channel-1::nose-1.2.1-py27_0': 2,
            'channel-1::nose-1.3.0-py27_0': 1,
            'channel-1::numexpr-2.0.1-np16py27_1': 1,
            'channel-1::numexpr-2.0.1-np16py27_2': 1,
            'channel-1::numexpr-2.0.1-np16py27_3': 1,
            'channel-1::numexpr-2.0.1-np16py27_ce0': 1,
            'channel-1::numexpr-2.0.1-np16py27_p1': 1,
            'channel-1::numexpr-2.0.1-np16py27_p2': 1,
            'channel-1::numexpr-2.0.1-np16py27_p3': 1,
            'channel-1::numexpr-2.0.1-np16py27_pro0': 1,
            'channel-1::numexpr-2.0.1-np17py27_1': 1,
            'channel-1::numexpr-2.0.1-np17py27_2': 1,
            'channel-1::numexpr-2.0.1-np17py27_3': 1,
            'channel-1::numexpr-2.0.1-np17py27_ce0': 1,
            'channel-1::numexpr-2.0.1-np17py27_p1': 1,
            'channel-1::numexpr-2.0.1-np17py27_p2': 1,
            'channel-1::numexpr-2.0.1-np17py27_p3': 1,
            'channel-1::numexpr-2.0.1-np17py27_pro0': 1,
            'channel-1::numpy-1.6.2-py27_1': 16,
            'channel-1::numpy-1.6.2-py27_3': 16,
            'channel-1::numpy-1.6.2-py27_4': 16,
            'channel-1::numpy-1.6.2-py27_ce0': 16,
            'channel-1::numpy-1.6.2-py27_p1': 16,
            'channel-1::numpy-1.6.2-py27_p3': 16,
            'channel-1::numpy-1.6.2-py27_p4': 16,
            'channel-1::numpy-1.6.2-py27_pro0': 16,
            'channel-1::numpy-1.7.0-py27_0': 13,
            'channel-1::numpy-1.7.0-py27_p0': 13,
            'channel-1::numpy-1.7.0b2-py27_ce0': 15,
            'channel-1::numpy-1.7.0b2-py27_pro0': 15,
            'channel-1::numpy-1.7.0rc1-py27_0': 14,
            'channel-1::numpy-1.7.0rc1-py27_p0': 14,
            'channel-1::numpy-1.7.1-py27_0': 12,
            'channel-1::numpy-1.7.1-py27_p0': 12,
            'channel-1::openssl-1.0.1c-0': 5,
            'channel-1::pandas-0.10.0-np16py27_0': 11,
            'channel-1::pandas-0.10.0-np17py27_0': 11,
            'channel-1::pandas-0.10.1-np16py27_0': 10,
            'channel-1::pandas-0.10.1-np17py27_0': 10,
            'channel-1::pandas-0.11.0-np16py27_1': 9,
            'channel-1::pandas-0.11.0-np17py27_1': 9,
            'channel-1::pandas-0.8.1-np16py27_0': 14,
            'channel-1::pandas-0.8.1-np17py27_0': 14,
            'channel-1::pandas-0.9.0-np16py27_0': 13,
            'channel-1::pandas-0.9.0-np17py27_0': 13,
            'channel-1::pandas-0.9.1-np16py27_0': 12,
            'channel-1::pandas-0.9.1-np17py27_0': 12,
            'channel-1::python-2.7.3-2': 5,
            'channel-1::python-2.7.3-3': 5,
            'channel-1::python-2.7.3-4': 5,
            'channel-1::python-2.7.3-5': 5,
            'channel-1::python-2.7.3-6': 5,
            'channel-1::python-2.7.3-7': 5,
            'channel-1::python-2.7.4-0': 4,
            'channel-1::python-2.7.5-0': 3,
            'channel-1::pytz-2012d-py27_0': 7,
            'channel-1::pytz-2012j-py27_0': 6,
            'channel-1::pytz-2013b-py27_0': 5,
            'channel-1::readline-6.2-0': 1,
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
            'channel-1::six-1.2.0-py27_0': 3,
            'channel-1::six-1.3.0-py27_0': 2,
            'channel-1::sqlite-3.7.13-0': 5,
            'channel-1::tk-8.5.13-0': 1,
            'channel-1::zlib-1.2.7-0': 1,
            'channel-4::ca-certificates-2017.08.26-h1d4fec5_0': 1,
            'channel-4::certifi-2017.11.5-py27h71e7faf_0': 3,
            'channel-4::certifi-2017.7.27.1-py27h9ceb091_0': 4,
            'channel-4::certifi-2018.1.18-py27_0': 2,
            'channel-4::certifi-2018.4.16-py27_0': 1,
            'channel-4::intel-openmp-2017.0.4-hf7c01fb_0': 2,
            'channel-4::intel-openmp-2018.0.0-8': 1,
            'channel-4::intel-openmp-2018.0.0-h15fc484_7': 1,
            'channel-4::intel-openmp-2018.0.0-hc7b2577_8': 1,
            'channel-4::libedit-3.1-heed3624_0': 1,
            'channel-4::libgcc-ng-7.2.0-h7cc24e2_2': 1,
            'channel-4::libgcc-ng-7.2.0-hcbc56d2_1': 1,
            'channel-4::libgcc-ng-7.2.0-hdf63c60_3': 1,
            'channel-4::libstdcxx-ng-7.2.0-h24385c6_1': 1,
            'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2': 1,
            'channel-4::libstdcxx-ng-7.2.0-hdf63c60_3': 1,
            'channel-4::mkl-2017.0.4-h4c4d0af_0': 4,
            'channel-4::mkl-2018.0.0-hb491cac_4': 3,
            'channel-4::mkl-2018.0.1-h19d6760_4': 2,
            'channel-4::mkl-2018.0.2-1': 1,
            'channel-4::mkl_fft-1.0.1-py27h3010b51_0': 2,
            'channel-4::mkl_fft-1.0.2-py27h651fb7a_0': 1,
            'channel-4::ncurses-6.0-h06874d7_1': 1,
            'channel-4::ncurses-6.0-h9df7e31_2': 1,
            'channel-4::numpy-1.11.3-py27h1b885b7_8': 10,
            'channel-4::numpy-1.11.3-py27h1b885b7_9': 10,
            'channel-4::numpy-1.11.3-py27h28100ab_6': 10,
            'channel-4::numpy-1.11.3-py27h28100ab_7': 10,
            'channel-4::numpy-1.11.3-py27h28100ab_8': 10,
            'channel-4::numpy-1.11.3-py27h2aefc1b_8': 10,
            'channel-4::numpy-1.11.3-py27h2aefc1b_9': 10,
            'channel-4::numpy-1.11.3-py27h3dfced4_4': 10,
            'channel-4::numpy-1.11.3-py27hcd700cb_6': 10,
            'channel-4::numpy-1.11.3-py27hcd700cb_7': 10,
            'channel-4::numpy-1.11.3-py27hcd700cb_8': 10,
            'channel-4::numpy-1.12.1-py27h9378851_1': 9,
            'channel-4::numpy-1.13.1-py27hd1b6e02_2': 8,
            'channel-4::numpy-1.13.3-py27_nomklh2b20989_4': 7,
            'channel-4::numpy-1.13.3-py27_nomklhfe0a00b_0': 7,
            'channel-4::numpy-1.13.3-py27h3dfced4_2': 7,
            'channel-4::numpy-1.13.3-py27ha266831_3': 7,
            'channel-4::numpy-1.13.3-py27hbcc08e0_0': 7,
            'channel-4::numpy-1.13.3-py27hdbf6ddf_4': 7,
            'channel-4::numpy-1.14.0-py27_nomklh7cdd4dd_0': 6,
            'channel-4::numpy-1.14.0-py27h3dfced4_0': 6,
            'channel-4::numpy-1.14.0-py27h3dfced4_1': 6,
            'channel-4::numpy-1.14.0-py27ha266831_2': 6,
            'channel-4::numpy-1.14.1-py27_nomklh5cab86c_2': 5,
            'channel-4::numpy-1.14.1-py27_nomklh7cdd4dd_1': 5,
            'channel-4::numpy-1.14.1-py27h3dfced4_1': 5,
            'channel-4::numpy-1.14.1-py27ha266831_2': 5,
            'channel-4::numpy-1.14.2-py27_nomklh2b20989_0': 4,
            'channel-4::numpy-1.14.2-py27_nomklh2b20989_1': 4,
            'channel-4::numpy-1.14.2-py27hdbf6ddf_0': 4,
            'channel-4::numpy-1.14.2-py27hdbf6ddf_1': 4,
            'channel-4::numpy-1.14.3-py27h28100ab_1': 3,
            'channel-4::numpy-1.14.3-py27h28100ab_2': 3,
            'channel-4::numpy-1.14.3-py27hcd700cb_1': 3,
            'channel-4::numpy-1.14.3-py27hcd700cb_2': 3,
            'channel-4::numpy-1.14.4-py27h28100ab_0': 2,
            'channel-4::numpy-1.14.4-py27hcd700cb_0': 2,
            'channel-4::numpy-1.14.5-py27h1b885b7_4': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_0': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_1': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_2': 1,
            'channel-4::numpy-1.14.5-py27h28100ab_3': 1,
            'channel-4::numpy-1.14.5-py27h2aefc1b_4': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_0': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_1': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_2': 1,
            'channel-4::numpy-1.14.5-py27hcd700cb_3': 1,
            'channel-4::numpy-1.9.3-py27_nomklhbee5d10_3': 11,
            'channel-4::numpy-1.9.3-py27h28100ab_5': 11,
            'channel-4::numpy-1.9.3-py27h28100ab_6': 11,
            'channel-4::numpy-1.9.3-py27h28100ab_7': 11,
            'channel-4::numpy-1.9.3-py27h7e35acb_3': 11,
            'channel-4::numpy-1.9.3-py27hcd700cb_5': 11,
            'channel-4::numpy-1.9.3-py27hcd700cb_6': 11,
            'channel-4::numpy-1.9.3-py27hcd700cb_7': 11,
            'channel-4::numpy-base-1.11.3-py27h2b20989_6': 4,
            'channel-4::numpy-base-1.11.3-py27h2b20989_7': 4,
            'channel-4::numpy-base-1.11.3-py27h2b20989_8': 4,
            'channel-4::numpy-base-1.11.3-py27h3dfced4_9': 4,
            'channel-4::numpy-base-1.11.3-py27h7cdd4dd_9': 4,
            'channel-4::numpy-base-1.11.3-py27hdbf6ddf_6': 4,
            'channel-4::numpy-base-1.11.3-py27hdbf6ddf_7': 4,
            'channel-4::numpy-base-1.11.3-py27hdbf6ddf_8': 4,
            'channel-4::numpy-base-1.14.3-py27h0ea5e3f_1': 3,
            'channel-4::numpy-base-1.14.3-py27h2b20989_0': 3,
            'channel-4::numpy-base-1.14.3-py27h2b20989_2': 3,
            'channel-4::numpy-base-1.14.3-py27h9be14a7_1': 3,
            'channel-4::numpy-base-1.14.3-py27hdbf6ddf_0': 3,
            'channel-4::numpy-base-1.14.3-py27hdbf6ddf_2': 3,
            'channel-4::numpy-base-1.14.4-py27h2b20989_0': 2,
            'channel-4::numpy-base-1.14.4-py27hdbf6ddf_0': 2,
            'channel-4::numpy-base-1.14.5-py27h2b20989_0': 1,
            'channel-4::numpy-base-1.14.5-py27h2b20989_1': 1,
            'channel-4::numpy-base-1.14.5-py27h2b20989_2': 1,
            'channel-4::numpy-base-1.14.5-py27h2b20989_3': 1,
            'channel-4::numpy-base-1.14.5-py27h2b20989_4': 1,
            'channel-4::numpy-base-1.14.5-py27hdbf6ddf_0': 1,
            'channel-4::numpy-base-1.14.5-py27hdbf6ddf_1': 1,
            'channel-4::numpy-base-1.14.5-py27hdbf6ddf_2': 1,
            'channel-4::numpy-base-1.14.5-py27hdbf6ddf_3': 1,
            'channel-4::numpy-base-1.14.5-py27hdbf6ddf_4': 1,
            'channel-4::numpy-base-1.9.3-py27h2b20989_5': 5,
            'channel-4::numpy-base-1.9.3-py27h2b20989_6': 5,
            'channel-4::numpy-base-1.9.3-py27h2b20989_7': 5,
            'channel-4::numpy-base-1.9.3-py27hdbf6ddf_5': 5,
            'channel-4::numpy-base-1.9.3-py27hdbf6ddf_6': 5,
            'channel-4::numpy-base-1.9.3-py27hdbf6ddf_7': 5,
            'channel-4::openssl-1.0.2l-h077ae2c_5': 4,
            'channel-4::openssl-1.0.2l-h9d1a558_3': 4,
            'channel-4::openssl-1.0.2l-hd940f6d_1': 4,
            'channel-4::openssl-1.0.2m-h26d622b_1': 3,
            'channel-4::openssl-1.0.2m-h8cfc7e7_0': 3,
            'channel-4::openssl-1.0.2n-hb7f436b_0': 2,
            'channel-4::openssl-1.0.2o-h14c3975_1': 1,
            'channel-4::openssl-1.0.2o-h20670df_0': 1,
            'channel-4::pandas-0.20.3-py27h820b67f_2': 8,
            'channel-4::pandas-0.20.3-py27hfd1eabf_2': 8,
            'channel-4::pandas-0.21.0-py27he307072_1': 7,
            'channel-4::pandas-0.21.1-py27h38cdd7d_0': 6,
            'channel-4::pandas-0.22.0-py27hf484d3e_0': 5,
            'channel-4::pandas-0.23.0-py27h637b7d7_0': 4,
            'channel-4::pandas-0.23.1-py27h637b7d7_0': 3,
            'channel-4::pandas-0.23.2-py27h04863e7_0': 2,
            'channel-4::pandas-0.23.3-py27h04863e7_0': 1,
            'channel-4::python-2.7.13-hac47a24_15': 2,
            'channel-4::python-2.7.13-heccc3f1_16': 2,
            'channel-4::python-2.7.13-hfff3488_13': 2,
            'channel-4::python-2.7.14-h1571d57_29': 1,
            'channel-4::python-2.7.14-h1571d57_30': 1,
            'channel-4::python-2.7.14-h1571d57_31': 1,
            'channel-4::python-2.7.14-h1aa7481_19': 1,
            'channel-4::python-2.7.14-h435b27a_18': 1,
            'channel-4::python-2.7.14-h89e7a4a_22': 1,
            'channel-4::python-2.7.14-h91f54f5_26': 1,
            'channel-4::python-2.7.14-h931c8b0_15': 1,
            'channel-4::python-2.7.14-h9b67528_20': 1,
            'channel-4::python-2.7.14-ha6fc286_23': 1,
            'channel-4::python-2.7.14-hc2b0042_21': 1,
            'channel-4::python-2.7.14-hdd48546_24': 1,
            'channel-4::python-2.7.14-hf918d8d_16': 1,
            'channel-4::python-dateutil-2.6.1-py27h4ca5741_1': 3,
            'channel-4::python-dateutil-2.7.0-py27_0': 2,
            'channel-4::python-dateutil-2.7.2-py27_0': 1,
            'channel-4::pytz-2017.2-py27hcac29fa_1': 4,
            'channel-4::pytz-2017.3-py27h001bace_0': 3,
            'channel-4::pytz-2018.3-py27_0': 2,
            'channel-4::pytz-2018.4-py27_0': 1,
            'channel-4::setuptools-36.5.0-py27h68b189e_0': 6,
            'channel-4::setuptools-38.4.0-py27_0': 5,
            'channel-4::setuptools-38.5.1-py27_0': 4,
            'channel-4::setuptools-39.0.1-py27_0': 3,
            'channel-4::setuptools-39.1.0-py27_0': 2,
            'channel-4::setuptools-39.2.0-py27_0': 1,
            'channel-4::six-1.10.0-py27hdcd7534_1': 1,
            'channel-4::sqlite-3.20.1-h6d8b0f3_1': 4,
            'channel-4::sqlite-3.20.1-haaaaaaa_4': 4,
            'channel-4::sqlite-3.20.1-hb898158_2': 4,
            'channel-4::sqlite-3.21.0-h1bed415_0': 3,
            'channel-4::sqlite-3.21.0-h1bed415_2': 3,
            'channel-4::sqlite-3.22.0-h1bed415_0': 2,
            'channel-4::sqlite-3.23.1-he433501_0': 1,
        })
        installed_wo_priority = set([prec.dist_str() for prec in this_r.install(spec)])
        pprint(installed_wo_priority)
        assert installed_wo_priority == add_subdir_to_iter({
            'channel-4::blas-1.0-mkl',
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::intel-openmp-2018.0.3-0',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libgfortran-ng-7.2.0-hdf63c60_3',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::mkl-2018.0.3-1',
            'channel-4::mkl_fft-1.0.4-py27h4414c95_1',
            'channel-4::mkl_random-1.0.1-py27h4414c95_1',
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::numpy-1.15.0-py27h1b885b7_0',
            'channel-4::numpy-base-1.15.0-py27h3dfced4_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::pandas-0.23.4-py27h04863e7_0',
            'channel-4::python-2.7.15-h1571d57_0',
            'channel-4::python-dateutil-2.7.3-py27_0',
            'channel-4::pytz-2018.5-py27_0',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::six-1.11.0-py27_1',
            'channel-4::sqlite-3.24.0-h84994c4_0',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::zlib-1.2.11-ha838bed_2',
        })


def test_dependency_sort():
    specs = ['pandas','python 2.7*','numpy 1.6*']
    installed = r.install(specs)
    must_have = {prec.name: prec for prec in installed}
    installed = r.dependency_sort(must_have)

    results_should_be = add_subdir_to_iter([
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
    ])
    assert len(installed) == len(results_should_be)
    assert [prec.dist_str() for prec in installed] == results_should_be


def test_update_deps():
    installed = r.install(['python 2.7*', 'numpy 1.6*', 'pandas 0.10.1'])
    result = [rec.dist_str() for rec in installed]
    assert result == add_subdir_to_iter([
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
    ])

    # scipy, and pandas should all be updated here. pytz is a new
    # dependency of pandas. But numpy does not _need_ to be updated
    # to get the latest version of pandas, so it stays put.
    result = r.install(['pandas', 'python 2.7*'], installed=installed, update_deps=True, returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
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
    ])

    # pandas should be updated here. However, it's going to try to not update
    # scipy, so it won't be updated to the latest version (0.11.0).
    result = r.install(['pandas', 'python 2.7*'], installed=installed, update_deps=False, returnall=True)
    result = [rec.dist_str() for rec in result]
    assert result == add_subdir_to_iter([
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
    ])


def test_fast_error_on_unsat():
    installed = r.install(["zope.interface=4.1.1"])
    result = [rec.dist_str() for rec in installed]

    assert result == add_subdir_to_iter([
        'channel-1::nose-1.3.0-py33_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-3.3.2-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
        "channel-1::zope.interface-4.1.1.1-py33_0",
    ])

    _installed = r.install(['python 2.7*'], installed=installed)
    result = [rec.dist_str() for rec in _installed]
    assert result == add_subdir_to_iter([
        'channel-1::nose-1.3.0-py27_0',
        'channel-1::openssl-1.0.1c-0',
        'channel-1::python-2.7.5-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
        'channel-1::zope.interface-4.0.5-py27_0',
    ])

    r._reduced_index_cache.clear()
    with env_var("CONDA_UNSATISFIABLE_HINTS", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with pytest.raises(UnsatisfiableError):
            _installed = r.install(["python 2.7*"], installed=installed)


def test_surplus_features_1():
    index = (
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
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['package2', 'feature'])
    assert 'package1' not in set(d.name for d in install)


def test_surplus_features_2():
    index = (
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
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['package2', 'feature'])
    assert 'package1' not in set(d.name for d in install)


def test_get_reduced_index_broadening_with_unsatisfiable_early_dep():
    # Test that spec broadening reduction doesn't kill valid solutions
    #    In other words, the order of packages in the index should not affect the
    #    overall result of the reduced index.
    # see discussion at https://github.com/conda/conda/pull/8117#discussion_r249249815
    index = (
        PackageRecord(**{
            'name': 'a',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            # not satisfiable. This record should come first, so that its c==2
            # constraint tries to mess up the inclusion of the c record below,
            # which should be included as part of b's deps, but which is
            # broader than this dep.
            'depends': ['b', 'c==2'],
        }),
        PackageRecord(**{
            'name': 'a',
            'version': '2.0',
            'build': '0',
            'build_number': 0,
            'depends': ['b'],
        }),
        PackageRecord(**{
            'name': 'b',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'depends': ['c'],
        }),
        PackageRecord(**{
            'name': 'c',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            'depends': [],
        })
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))

    install = r.install(['a'])
    assert 'a' in set(d.name for d in install)
    assert 'b' in set(d.name for d in install)
    assert 'c' in set(d.name for d in install)


def test_get_reduced_index_broadening_preferred_solution():
    # test that order of index reduction does not eliminate what should be a preferred solution
    #    https://github.com/conda/conda/pull/8117#discussion_r249216068
    index = (
        PackageRecord(**{
            'name': 'top',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            # this is the first processed record, and imposes a broadening constraint on bottom
            #    if things are overly restricted, we'll end up with bottom 1.5 in our solution
            #    instead of the preferred (latest) 2.5
            'depends': ['middle', 'bottom==1.5'],
        }),
        PackageRecord(**{
            'name': 'top',
            'version': '2.0',
            'build': '0',
            'build_number': 0,
            'depends': ['middle'],
        }),
        PackageRecord(**{
            'name': 'middle',
            'version': '1.0',
            'build': '0',
            'build_number': 0,
            # this is a broad constraint on bottom, which should allow us to
            #    get the latest version (2.5)
            'depends': ['bottom'],
        }),
        PackageRecord(**{
            'name': 'bottom',
            'version': '1.5',
            'build': '0',
            'build_number': 0,
            'depends': [],
        }),
        PackageRecord(**{
            'name': 'bottom',
            'version': '2.5',
            'build': '0',
            'build_number': 0,
            'depends': [],
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))

    install = r.install(['top'])
    for d in install:
        if d.name == 'top':
            assert d.version == '2.0', "top version should be 2.0, but is {}".format(d.version)
        elif d.name == 'bottom':
            assert d.version == '2.5', "bottom version should be 2.5, but is {}".format(d.version)


def test_arch_preferred_when_otherwise_identical_dependencies():
    index2 = index.copy()
    package1_noarch = PackageRecord(**{
        "channel": "defaults",
        "subdir": "noarch",
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'depends': [],
        'name': 'package1',
        'requires': [],
        'version': '1.0',
    })
    index2[package1_noarch] = package1_noarch
    package1_linux64 = PackageRecord(**{
        "channel": "defaults",
        "subdir": context.subdir,
        "md5": "0123456789",
        "fn": "doesnt-matter-here",
        'build': '0',
        'build_number': 0,
        'depends': [],
        'name': 'package1',
        'requires': [],
        'version': '1.0',
    })
    index2[package1_linux64] = package1_linux64
    index2 = {key: value for key, value in iteritems(index2)}
    r = Resolve(index2)

    matches = r.find_matches(MatchSpec('package1'))
    assert len(matches) == 2
    assert set(prec.dist_str() for prec in r.find_matches(MatchSpec('package1'))) == {
        'defaults/noarch::package1-1.0-0',
        add_subdir('defaults::package1-1.0-0')
    }

    result = r.install(['package1'])
    result = [rec.dist_str() for rec in result]
    assert result == [
        add_subdir('defaults::package1-1.0-0'),
    ]


def test_arch_preferred_over_noarch_when_otherwise_equal():
    index = (
        PackageRecord(**{
            "build": "py36_0",
            "build_number": 0,
            "date": "2016-12-17",
            "license": "BSD",
            "md5": "9b4568068e3a7ac81be87902827d949e",
            "name": "itsdangerous",
            "size": 19688,
            "version": "0.24"
        }),
        PackageRecord(**{
            "arch": None,
            "binstar": {
            "channel": "main",
            "owner_id": "58596cc93d1b550ffad38672",
            "package_id": "5898cb9d9aba4511169c383a"
            },
            "build": "py_0",
            "build_number": 0,
            "has_prefix": False,
            "license": "BSD",
            "machine": None,
            "md5": "917e90ca4e80324b77e8df449d07eefc",
            "name": "itsdangerous",
            "noarch": "python",
            "operatingsystem": None,
            "platform": None,
            "requires": [],
            "size": 14098,
            "subdir": "noarch",
            "target-triplet": "None-any-None",
            "version": "0.24"
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['itsdangerous'])
    for d in install:
        assert d.subdir == context.subdir


def test_noarch_preferred_over_arch_when_version_greater():
    index = (
        PackageRecord(**{
            'name': 'abc',
            'version': '2.0',
            'build': '0',
            "subdir": "noarch",
            'build_number': 0,
        }),
        PackageRecord(**{
            'name': 'abc',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['abc'])
    for d in install:
        assert d.subdir == 'noarch'
        assert d.version == '2.0'


def test_noarch_preferred_over_arch_when_build_greater():
    index = (
        PackageRecord(**{
            'name': 'abc',
            'version': '1.0',
            'build': '1',
            "subdir": "noarch",
            'build_number': 1,
        }),
        PackageRecord(**{
            'name': 'abc',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['abc'])
    for d in install:
        assert d.subdir == 'noarch'
        assert d.build_number == 1


def test_arch_preferred_over_noarch_when_otherwise_equal_dep():
    index = (
        PackageRecord(**{
            "build": "py36_0",
            "build_number": 0,
            "date": "2016-12-17",
            "license": "BSD",
            "md5": "9b4568068e3a7ac81be87902827d949e",
            "name": "itsdangerous",
            "size": 19688,
            "version": "0.24"
        }),
        PackageRecord(**{
            "arch": None,
            "binstar": {
            "channel": "main",
            "owner_id": "58596cc93d1b550ffad38672",
            "package_id": "5898cb9d9aba4511169c383a"
            },
            "build": "py_0",
            "build_number": 0,
            "has_prefix": False,
            "license": "BSD",
            "machine": None,
            "md5": "917e90ca4e80324b77e8df449d07eefc",
            "name": "itsdangerous",
            "noarch": "python",
            "operatingsystem": None,
            "platform": None,
            "requires": [],
            "size": 14098,
            "subdir": "noarch",
            "target-triplet": "None-any-None",
            "version": "0.24"
        }),
        PackageRecord(**{
            'name': 'foo',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
            'depends': ['itsdangerous'],
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['foo'])
    for d in install:
        if d.name == 'itsdangerous':
            assert d.subdir == context.subdir


def test_noarch_preferred_over_arch_when_version_greater_dep():
    index = (
        PackageRecord(**{
            'name': 'abc',
            'version': '2.0',
            'build': '0',
            "subdir": "noarch",
            'build_number': 0,
        }),
        PackageRecord(**{
            'name': 'abc',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
        }),
        PackageRecord(**{
            'name': 'foo',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
            'depends': ['abc'],
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['foo'])
    for d in install:
        if d.name == 'abc':
            assert d.subdir == 'noarch'
            assert d.version == '2.0'


def test_noarch_preferred_over_arch_when_build_greater_dep():
    index = (
        PackageRecord(**{
            'name': 'abc',
            'version': '1.0',
            'build': '1',
            "subdir": "noarch",
            'build_number': 1,
        }),
        PackageRecord(**{
            'name': 'abc',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
        }),
        PackageRecord(**{
            'name': 'foo',
            'version': '1.0',
            'build': '0',
            "subdir": context.subdir,
            'build_number': 0,
            'depends': ['abc'],
        }),
    )
    r = Resolve(OrderedDict((prec, prec) for prec in index))
    install = r.install(['abc'])
    for d in install:
        if d.name == 'abc':
            assert d.subdir == 'noarch'
            assert d.build_number == 1
