# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from pprint import pprint
import platform
import sys
import copy

import pytest

from conda.auxlib.ish import dals
from conda.base.context import context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import on_linux
from conda.common.io import env_var, env_vars
from conda.core.solve import DepsModifier, _get_solver_class, UpdateModifier
from conda.exceptions import UnsatisfiableError, SpecsConfigurationConflictError
from conda.models.channel import Channel
from conda.models.records import PrefixRecord
from conda.models.enums import PackageType
from conda.resolve import MatchSpec
from conda.testing.helpers import add_subdir_to_iter, get_solver, get_solver_2, get_solver_4, \
    get_solver_aggregate_1, get_solver_aggregate_2, get_solver_cuda, get_solver_must_unfreeze, \
    convert_to_dist_str, CHANNEL_DIR

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

Solver = _get_solver_class()


def test_solve_1(tmpdir):
    specs = MatchSpec("numpy"),

    with get_solver(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()
        # print(convert_to_dist_str(final_state))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-3.3.2-0',
            'channel-1::numpy-1.7.1-py33_0',
        ))
        assert convert_to_dist_str(final_state) == order

    specs_to_add = MatchSpec("python=2"),
    with get_solver(tmpdir, specs_to_add=specs_to_add,
                    prefix_records=final_state, history_specs=specs) as solver:
        final_state = solver.solve_final_state()
        # print(convert_to_dist_str(final_state))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.7.1-py27_0',
        ))
        assert convert_to_dist_str(final_state) == order


def test_solve_2(tmpdir):
    specs = MatchSpec("numpy"),

    with get_solver_aggregate_1(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()
        # print(convert_to_dist_str(final_state))
        order = add_subdir_to_iter((
            'channel-2::mkl-2017.0.3-0',
            'channel-2::openssl-1.0.2l-0',
            'channel-2::readline-6.2-2',
            'channel-2::sqlite-3.13.0-0',
            'channel-2::tk-8.5.18-0',
            'channel-2::xz-5.2.3-0',
            'channel-2::zlib-1.2.11-0',
            'channel-2::python-3.6.2-0',
            'channel-2::numpy-1.13.1-py36_0'
        ))
        assert convert_to_dist_str(final_state) == order

    specs_to_add = MatchSpec("channel-4::numpy"),
    with get_solver_aggregate_1(tmpdir, specs_to_add=specs_to_add,
                    prefix_records=final_state, history_specs=specs) as solver:
        solver.solve_final_state()
        extra_prec = PrefixRecord(_hash=5842798532132402024, name='mkl', version='2017.0.3',
                                  build='0', build_number=0, channel=Channel("channel-2/osx-64"),
                                  subdir='osx-64', fn='mkl-2017.0.3-0.tar.bz2',
                                  md5='76cfa5d21e73db338ffccdbe0af8a727',
                                  url='https://conda.anaconda.org/channel-2/osx-64/mkl-2017.0.3-0.tar.bz2',
                                  arch='x86_64', platform='darwin', depends=(), constrains=(),
                                  track_features=(), features=(), license='proprietary - Intel',
                                  license_family='Proprietary', timestamp=0, date='2017-06-26', size=135839394)

        solver_ssc = copy.copy(solver.ssc)
        ssc = solver.ssc
        ssc.add_back_map = [MatchSpec("mkl")]
        # Do a transformation from set -> list for precs (done in _run_sat)
        sol_precs = [_ for _ in ssc.solution_precs]
        ssc.solution_precs = copy.copy(sol_precs)
        # Add extra prec to the ssc being used
        sol_precs.append(extra_prec)
        solver_ssc.solution_precs = sol_precs

        # Last modification to ssc before finding orphaned packages is done by run_sat
        solver._run_sat = Mock(return_value=ssc)
        # Give solver the modified ssc
        solver.ssc = solver_ssc
        final_state = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_ALL)
        prec_names = [_.name for _ in final_state]
        assert len(prec_names) == len(set(prec_names))


def test_virtual_package_solver(tmpdir):
    specs = MatchSpec("cudatoolkit"),

    with env_var('CONDA_OVERRIDE_CUDA', '10.0'):
        with get_solver_cuda(tmpdir, specs) as solver:
            _ = solver.solve_final_state()
            ssc = solver.ssc
            # Check the cuda virtual package is included in the solver
            assert '__cuda' in ssc.specs_map.keys()

            # Check that the environment is consistent after installing a
            # package which *depends* on a virtual package
            for pkgs in ssc.solution_precs:
                if pkgs.name == 'cudatoolkit':
                    # make sure this package depends on the __cuda virtual
                    # package as a dependency since this is requirement of the
                    # test the test
                    assert '__cuda' in pkgs.depends[0]
            assert ssc.r.bad_installed(ssc.solution_precs, ())[1] is None


def test_solve_msgs_exclude_vp(tmpdir):
    # Sovler hints should exclude virtual packages that are not dependencies
    specs = MatchSpec("python =2.7.5"), MatchSpec("readline =5.0"),

    with env_var('CONDA_OVERRIDE_CUDA', '10.0'):
        with get_solver_cuda(tmpdir, specs) as solver:
            with pytest.raises(UnsatisfiableError) as exc:
                final_state = solver.solve_final_state()

    assert "__cuda==10.0" not in str(exc.value).strip()


def test_cuda_1(tmpdir):
    specs = MatchSpec("cudatoolkit"),

    with env_var('CONDA_OVERRIDE_CUDA', '9.2'):
        with get_solver_cuda(tmpdir, specs) as solver:
            final_state = solver.solve_final_state()
            # print(convert_to_dist_str(final_state))
            order = add_subdir_to_iter((
                'channel-1::cudatoolkit-9.0-0',
            ))
            assert convert_to_dist_str(final_state) == order


def test_cuda_2(tmpdir):
    specs = MatchSpec("cudatoolkit"),

    with env_var('CONDA_OVERRIDE_CUDA', '10.0'):
        with get_solver_cuda(tmpdir, specs) as solver:
            final_state = solver.solve_final_state()
            # print(convert_to_dist_str(final_state))
            order = add_subdir_to_iter((
                'channel-1::cudatoolkit-10.0-0',
            ))
            assert convert_to_dist_str(final_state) == order


def test_cuda_fail_1(tmpdir):
    specs = MatchSpec("cudatoolkit"),

    # No cudatoolkit in index for CUDA 8.0
    with env_var('CONDA_OVERRIDE_CUDA', '8.0'):
        with get_solver_cuda(tmpdir, specs) as solver:
            with pytest.raises(UnsatisfiableError) as exc:
                final_state = solver.solve_final_state()

    if sys.platform == "darwin":
        plat = "osx-64"
    elif sys.platform == "linux":
        plat = "linux-64"
    elif sys.platform == "win32":
        if platform.architecture()[0] == "32bit":
            plat = "win-32"
        else:
            plat = "win-64"
    else:
        plat = "linux-64"

    assert str(exc.value).strip() == dals("""The following specifications were found to be incompatible with your system:

  - feature:/{}::__cuda==8.0=0
  - cudatoolkit -> __cuda[version='>=10.0|>=9.0']

Your installed version is: 8.0""".format(plat))


def test_cuda_fail_2(tmpdir):
    specs = MatchSpec("cudatoolkit"),

    # No CUDA on system
    with env_var('CONDA_OVERRIDE_CUDA', ''):
        with get_solver_cuda(tmpdir, specs) as solver:
            with pytest.raises(UnsatisfiableError) as exc:
                final_state = solver.solve_final_state()

    assert str(exc.value).strip() == dals("""The following specifications were found to be incompatible with your system:

  - cudatoolkit -> __cuda[version='>=10.0|>=9.0']

Your installed version is: not available""")


def test_cuda_constrain_absent(tmpdir):
    specs = MatchSpec("cuda-constrain"),

    with env_var('CONDA_OVERRIDE_CUDA', ''):
        with get_solver_cuda(tmpdir, specs) as solver:
            final_state = solver.solve_final_state()
            # print(convert_to_dist_str(final_state))
            order = add_subdir_to_iter((
                'channel-1::cuda-constrain-11.0-0',
            ))
            assert convert_to_dist_str(final_state) == order


@pytest.mark.skip(reason="known broken; fix to be implemented")
def test_cuda_constrain_sat(tmpdir):
    specs = MatchSpec("cuda-constrain"),

    with env_var('CONDA_OVERRIDE_CUDA', '10.0'):
        with get_solver_cuda(tmpdir, specs) as solver:
            final_state = solver.solve_final_state()
            # print(convert_to_dist_str(final_state))
            order = add_subdir_to_iter((
                'channel-1::cuda-constrain-10.0-0',
            ))
            assert convert_to_dist_str(final_state) == order


@pytest.mark.skip(reason="known broken; fix to be implemented")
def test_cuda_constrain_unsat(tmpdir):
    specs = MatchSpec("cuda-constrain"),

    # No cudatoolkit in index for CUDA 8.0
    with env_var('CONDA_OVERRIDE_CUDA', '8.0'):
        with get_solver_cuda(tmpdir, specs) as solver:
            with pytest.raises(UnsatisfiableError) as exc:
                final_state = solver.solve_final_state()

    assert str(exc.value).strip() == dals("""The following specifications were found to be incompatible with your system:

  - feature:|@/{}::__cuda==8.0=0
  - __cuda[version='>=10.0'] -> feature:/linux-64::__cuda==8.0=0

Your installed version is: 8.0""".format(context.subdir))


@pytest.mark.skipif(not on_linux, reason="linux-only test")
def test_cuda_glibc_sat(tmpdir):
    specs = MatchSpec("cuda-glibc"),

    with env_var('CONDA_OVERRIDE_CUDA', '10.0'), env_var('CONDA_OVERRIDE_GLIBC', '2.23'):
        with get_solver_cuda(tmpdir, specs) as solver:
            final_state = solver.solve_final_state()
            # print(convert_to_dist_str(final_state))
            order = add_subdir_to_iter((
                'channel-1::cuda-glibc-10.0-0',
            ))
            assert convert_to_dist_str(final_state) == order


@pytest.mark.skip(reason="known broken; fix to be implemented")
@pytest.mark.skipif(not on_linux, reason="linux-only test")
def test_cuda_glibc_unsat_depend(tmpdir):
    specs = MatchSpec("cuda-glibc"),

    with env_var('CONDA_OVERRIDE_CUDA', '8.0'), env_var('CONDA_OVERRIDE_GLIBC', '2.23'):
        with get_solver_cuda(tmpdir, specs) as solver:
            with pytest.raises(UnsatisfiableError) as exc:
                final_state = solver.solve_final_state()

    assert str(exc.value).strip() == dals("""The following specifications were found to be incompatible with your system:

  - feature:|@/{}::__cuda==8.0=0
  - __cuda[version='>=10.0'] -> feature:/linux-64::__cuda==8.0=0

Your installed version is: 8.0""".format(context.subdir))


@pytest.mark.skip(reason="known broken; fix to be implemented")
@pytest.mark.skipif(not on_linux, reason="linux-only test")
def test_cuda_glibc_unsat_constrain(tmpdir):
    specs = MatchSpec("cuda-glibc"),

    with env_var('CONDA_OVERRIDE_CUDA', '10.0'), env_var('CONDA_OVERRIDE_GLIBC', '2.12'):
        with get_solver_cuda(tmpdir, specs) as solver:
            with pytest.raises(UnsatisfiableError) as exc:
                final_state = solver.solve_final_state()


def test_prune_1(tmpdir):
    specs = MatchSpec("numpy=1.6"), MatchSpec("python=2.7.3"), MatchSpec("accelerate"),

    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        pprint(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::libnvvm-1.0-p0',
            'channel-1::mkl-rt-11.0-p0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.3-7',
            'channel-1::bitarray-0.8.1-py27_0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::mkl-service-1.0.0-py27_p0',
            'channel-1::numpy-1.6.2-py27_p4',
            'channel-1::numba-0.8.1-np16py27_0',
            'channel-1::numexpr-2.1-np16py27_p0',
            'channel-1::scipy-0.12.0-np16py27_p0',
            'channel-1::numbapro-0.11.0-np16py27_p0',
            'channel-1::scikit-learn-0.13.1-np16py27_p0',
            'channel-1::mkl-11.0-np16py27_p0',
            'channel-1::accelerate-1.1.0-np16py27_p0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_remove = MatchSpec("numbapro"),
    with get_solver(tmpdir, specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = add_subdir_to_iter((
            'channel-1::accelerate-1.1.0-np16py27_p0',
            'channel-1::mkl-11.0-np16py27_p0',
            'channel-1::scikit-learn-0.13.1-np16py27_p0',
            'channel-1::numbapro-0.11.0-np16py27_p0',
            'channel-1::scipy-0.12.0-np16py27_p0',
            'channel-1::numexpr-2.1-np16py27_p0',
            'channel-1::numba-0.8.1-np16py27_0',
            'channel-1::numpy-1.6.2-py27_p4',
            'channel-1::mkl-service-1.0.0-py27_p0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::bitarray-0.8.1-py27_0',
            'channel-1::llvm-3.2-0',
            'channel-1::mkl-rt-11.0-p0',
            'channel-1::libnvvm-1.0-p0',
        ))
        link_order = add_subdir_to_iter((
            'channel-1::numpy-1.6.2-py27_4',
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order


def test_force_remove_1(tmpdir):
    specs = MatchSpec("numpy[version=*,build=*py27*]"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.7.1-py27_0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    # without force_remove, taking out python takes out everything that depends on it, too,
    #    so numpy goes away.  All of pythons' deps are also pruned.
    specs_to_remove = MatchSpec("python"),
    with get_solver(tmpdir, specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        # openssl remains because it is in the aggressive_update_packages set,
        #    but everything else gets removed
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
        ))
        assert convert_to_dist_str(final_state_2) == order

    # with force remove, we remove only the explicit specs that we provide
    #    this leaves an inconsistent env
    specs_to_remove = MatchSpec("python"),
    with get_solver(tmpdir, specs_to_remove=specs_to_remove, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(force_remove=True)
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
        ))
        assert convert_to_dist_str(final_state_2) == order

    # re-solving restores order
    with get_solver(tmpdir, prefix_records=final_state_2) as solver:
        final_state_3 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_3))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numpy-1.7.1-py27_0'
        ))
        assert convert_to_dist_str(final_state_3) == order


def test_no_deps_1(tmpdir):
    specs = MatchSpec("python=2"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_add = MatchSpec("numba"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            'channel-1::numba-0.8.1-np17py27_0'
        ))
        assert convert_to_dist_str(final_state_2) == order

    specs_to_add = MatchSpec("numba"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier='NO_DEPS')
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::numba-0.8.1-np17py27_0',
        ))
        assert convert_to_dist_str(final_state_2) == order


def test_only_deps_1(tmpdir):
    specs = MatchSpec("numba[version=*,build=*py27*]"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.11.2-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
        ))
        assert convert_to_dist_str(final_state_1) == order


def test_only_deps_2(tmpdir):
    specs = MatchSpec("numpy=1.5"), MatchSpec("python=2.7.3"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::numpy-1.5.1-py27_4',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_add = MatchSpec("numba=0.5"),
    with get_solver(tmpdir, specs_to_add) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.5-0',
            'channel-1::llvmpy-0.10.0-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            # 'channel-1::numba-0.5.0-np17py27_0',  # not in the order because only_deps
        ))
        assert convert_to_dist_str(final_state_2) == order

    # fails because numpy=1.5 is in our history as an explicit spec
    specs_to_add = MatchSpec("numba=0.5"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        with pytest.raises(UnsatisfiableError):
            final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)

    specs_to_add = MatchSpec("numba=0.5"), MatchSpec("numpy")
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(deps_modifier=DepsModifier.ONLY_DEPS)
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.7.3-7',
            'channel-1::llvmpy-0.10.0-py27_0',
            'channel-1::meta-0.4.2.dev-py27_0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',
            # 'channel-1::numba-0.5.0-np17py27_0',   # not in the order because only_deps
        ))
        assert convert_to_dist_str(final_state_2) == order


def test_update_all_1(tmpdir):
    specs = MatchSpec("numpy=1.5"), MatchSpec("python=2.6"), MatchSpec("system[version=*,build_number=0]")
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-0',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.6.8-6',
            'channel-1::numpy-1.5.1-py26_4',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_add = MatchSpec("numba=0.6"), MatchSpec("numpy")
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-0',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.6.8-6',
            'channel-1::llvmpy-0.10.2-py26_0',
            'channel-1::nose-1.3.0-py26_0',
            'channel-1::numpy-1.7.1-py26_0',
            'channel-1::numba-0.6.0-np17py26_0',
        ))
        assert convert_to_dist_str(final_state_2) == order

    specs_to_add = MatchSpec("numba=0.6"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_ALL)
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-2.6.8-6',  # stick with python=2.6 even though UPDATE_ALL
            'channel-1::llvmpy-0.10.2-py26_0',
            'channel-1::nose-1.3.0-py26_0',
            'channel-1::numpy-1.7.1-py26_0',
            'channel-1::numba-0.6.0-np17py26_0',
        ))
        assert convert_to_dist_str(final_state_2) == order


def test_broken_install(tmpdir):
    specs = MatchSpec("pandas=0.11.0=np16py27_1"), MatchSpec("python=2.7")
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order_original = add_subdir_to_iter((
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
            'channel-1::pandas-0.11.0-np16py27_1',
        ))
        assert convert_to_dist_str(final_state_1) == order_original
        assert solver._r.environment_is_consistent(final_state_1)

    # Add an incompatible numpy; installation should be untouched
    final_state_1_modified = list(final_state_1)
    numpy_matcher = MatchSpec("channel-1::numpy==1.7.1=py33_p0")
    numpy_prec = next(prec for prec in solver._index if numpy_matcher.match(prec))
    final_state_1_modified[7] = numpy_prec
    assert not solver._r.environment_is_consistent(final_state_1_modified)

    specs_to_add = MatchSpec("flask"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1_modified, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            "channel-1::numpy-1.7.1-py33_p0",
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::jinja2-2.6-py27_0',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::werkzeug-0.8.3-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::flask-0.9-py27_0',
            'channel-1::pandas-0.11.0-np16py27_1'
        ))
        assert convert_to_dist_str(final_state_2) == order
        assert not solver._r.environment_is_consistent(final_state_2)

    # adding numpy spec again snaps the packages back to a consistent state
    specs_to_add = MatchSpec("flask"), MatchSpec("numpy 1.6.*"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1_modified, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::jinja2-2.6-py27_0',
            'channel-1::numpy-1.6.2-py27_4',
            'channel-1::pytz-2013b-py27_0',
            'channel-1::six-1.3.0-py27_0',
            'channel-1::werkzeug-0.8.3-py27_0',
            'channel-1::dateutil-2.1-py27_1',
            'channel-1::flask-0.9-py27_0',
            'channel-1::scipy-0.12.0-np16py27_0',
            'channel-1::pandas-0.11.0-np16py27_1',
        ))
        assert convert_to_dist_str(final_state_2) == order
        assert solver._r.environment_is_consistent(final_state_2)

    # Add an incompatible pandas; installation should be untouched, then fixed
    final_state_2_mod = list(final_state_1)
    pandas_matcher = MatchSpec('channel-1::pandas==0.11.0=np17py27_1')
    pandas_prec = next(prec for prec in solver._index if pandas_matcher.match(prec))
    final_state_2_mod[12] = pandas_prec
    assert not solver._r.environment_is_consistent(final_state_2_mod)


def test_conda_downgrade(tmpdir):
    specs = MatchSpec("conda-build"),
    with env_var("CONDA_CHANNEL_PRIORITY", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with get_solver_aggregate_1(tmpdir, specs) as solver:
            final_state_1 = solver.solve_final_state()
            pprint(convert_to_dist_str(final_state_1))
            order = add_subdir_to_iter((
                'channel-4::ca-certificates-2018.03.07-0',
                'channel-2::conda-env-2.6.0-0',
                'channel-2::libffi-3.2.1-1',
                'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
                'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
                'channel-2::zlib-1.2.11-0',
                'channel-4::ncurses-6.1-hf484d3e_0',
                'channel-4::openssl-1.0.2p-h14c3975_0',
                'channel-4::patchelf-0.9-hf484d3e_2',
                'channel-4::tk-8.6.7-hc745277_3',
                'channel-4::xz-5.2.4-h14c3975_4',
                'channel-4::yaml-0.1.7-had09818_2',
                'channel-4::libedit-3.1.20170329-h6b74fdf_2',
                'channel-4::readline-7.0-ha6073c6_4',
                'channel-4::sqlite-3.24.0-h84994c4_0',
                'channel-4::python-3.7.0-hc3d631a_0',
                'channel-4::asn1crypto-0.24.0-py37_0',
                'channel-4::beautifulsoup4-4.6.3-py37_0',
                'channel-4::certifi-2018.8.13-py37_0',
                'channel-4::chardet-3.0.4-py37_1',
                'channel-4::cryptography-vectors-2.3-py37_0',
                'channel-4::filelock-3.0.4-py37_0',
                'channel-4::glob2-0.6-py37_0',
                'channel-4::idna-2.7-py37_0',
                'channel-4::markupsafe-1.0-py37h14c3975_1',
                'channel-4::pkginfo-1.4.2-py37_1',
                'channel-4::psutil-5.4.6-py37h14c3975_0',
                'channel-4::pycosat-0.6.3-py37h14c3975_0',
                'channel-4::pycparser-2.18-py37_1',
                'channel-4::pysocks-1.6.8-py37_0',
                'channel-4::pyyaml-3.13-py37h14c3975_0',
                'channel-4::ruamel_yaml-0.15.46-py37h14c3975_0',
                'channel-4::six-1.11.0-py37_1',
                'channel-4::cffi-1.11.5-py37h9745a5d_0',
                'channel-4::setuptools-40.0.0-py37_0',
                'channel-4::cryptography-2.3-py37hb7f436b_0',
                'channel-4::jinja2-2.10-py37_0',
                'channel-4::pyopenssl-18.0.0-py37_0',
                'channel-4::urllib3-1.23-py37_0',
                'channel-4::requests-2.19.1-py37_0',
                'channel-4::conda-4.5.10-py37_0',
                'channel-4::conda-build-3.12.1-py37_0'
            ))
            assert convert_to_dist_str(final_state_1) == order

    specs_to_add = MatchSpec("itsdangerous"),  # MatchSpec("conda"),
    saved_sys_prefix = sys.prefix
    try:
        sys.prefix = tmpdir.strpath
        with get_solver_aggregate_1(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                                    history_specs=specs) as solver:
            unlink_precs, link_precs = solver.solve_for_diff()
            pprint(convert_to_dist_str(unlink_precs))
            pprint(convert_to_dist_str(link_precs))
            unlink_order = (
                # no conda downgrade
            )
            link_order = add_subdir_to_iter((
                'channel-2::itsdangerous-0.24-py_0',
            ))
            assert convert_to_dist_str(unlink_precs) == unlink_order
            assert convert_to_dist_str(link_precs) == link_order

        specs_to_add = MatchSpec("itsdangerous"), MatchSpec("conda"),
        with get_solver_aggregate_1(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                                    history_specs=specs) as solver:
            unlink_precs, link_precs = solver.solve_for_diff()
            pprint(convert_to_dist_str(unlink_precs))
            pprint(convert_to_dist_str(link_precs))
            assert convert_to_dist_str(unlink_precs) == unlink_order
            assert convert_to_dist_str(link_precs) == link_order

        specs_to_add = MatchSpec("itsdangerous"), MatchSpec("conda<4.4.10"), MatchSpec("python")
        with get_solver_aggregate_1(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                                    history_specs=specs) as solver:
            unlink_precs, link_precs = solver.solve_for_diff()
            pprint(convert_to_dist_str(unlink_precs))
            pprint(convert_to_dist_str(link_precs))
            unlink_order = add_subdir_to_iter((
                # now conda gets downgraded
                'channel-4::conda-build-3.12.1-py37_0',
                'channel-4::conda-4.5.10-py37_0',
                'channel-4::requests-2.19.1-py37_0',
                'channel-4::urllib3-1.23-py37_0',
                'channel-4::pyopenssl-18.0.0-py37_0',
                'channel-4::jinja2-2.10-py37_0',
                'channel-4::cryptography-2.3-py37hb7f436b_0',
                'channel-4::setuptools-40.0.0-py37_0',
                'channel-4::cffi-1.11.5-py37h9745a5d_0',
                'channel-4::six-1.11.0-py37_1',
                'channel-4::ruamel_yaml-0.15.46-py37h14c3975_0',
                'channel-4::pyyaml-3.13-py37h14c3975_0',
                'channel-4::pysocks-1.6.8-py37_0',
                'channel-4::pycparser-2.18-py37_1',
                'channel-4::pycosat-0.6.3-py37h14c3975_0',
                'channel-4::psutil-5.4.6-py37h14c3975_0',
                'channel-4::pkginfo-1.4.2-py37_1',
                'channel-4::markupsafe-1.0-py37h14c3975_1',
                'channel-4::idna-2.7-py37_0',
                'channel-4::glob2-0.6-py37_0',
                'channel-4::filelock-3.0.4-py37_0',
                'channel-4::cryptography-vectors-2.3-py37_0',
                'channel-4::chardet-3.0.4-py37_1',
                'channel-4::certifi-2018.8.13-py37_0',
                'channel-4::beautifulsoup4-4.6.3-py37_0',
                'channel-4::asn1crypto-0.24.0-py37_0',
                'channel-4::python-3.7.0-hc3d631a_0',
                'channel-4::sqlite-3.24.0-h84994c4_0',
                'channel-4::readline-7.0-ha6073c6_4',
                'channel-4::libedit-3.1.20170329-h6b74fdf_2',
                'channel-4::yaml-0.1.7-had09818_2',
                'channel-4::xz-5.2.4-h14c3975_4',
                'channel-4::tk-8.6.7-hc745277_3',
                'channel-4::openssl-1.0.2p-h14c3975_0',
                'channel-4::ncurses-6.1-hf484d3e_0',
            ))
            link_order = add_subdir_to_iter((
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::xz-5.2.3-0',
                'channel-2::yaml-0.1.6-0',
                'channel-2::python-3.6.2-0',
                'channel-2::asn1crypto-0.22.0-py36_0',
                'channel-4::beautifulsoup4-4.6.3-py36_0',
                'channel-2::certifi-2016.2.28-py36_0',
                'channel-4::chardet-3.0.4-py36_1',
                'channel-4::filelock-3.0.4-py36_0',
                'channel-4::glob2-0.6-py36_0',
                'channel-2::idna-2.6-py36_0',
                'channel-2::itsdangerous-0.24-py36_0',
                'channel-2::markupsafe-1.0-py36_0',
                'channel-4::pkginfo-1.4.2-py36_1',
                'channel-2::psutil-5.2.2-py36_0',
                'channel-2::pycosat-0.6.2-py36_0',
                'channel-2::pycparser-2.18-py36_0',
                'channel-2::pyparsing-2.2.0-py36_0',
                'channel-2::pyyaml-3.12-py36_0',
                'channel-2::requests-2.14.2-py36_0',
                'channel-2::ruamel_yaml-0.11.14-py36_1',
                'channel-2::six-1.10.0-py36_0',
                'channel-2::cffi-1.10.0-py36_0',
                'channel-2::packaging-16.8-py36_0',
                'channel-2::setuptools-36.4.0-py36_1',
                'channel-2::cryptography-1.8.1-py36_0',
                'channel-2::jinja2-2.9.6-py36_0',
                'channel-2::pyopenssl-17.0.0-py36_0',
                'channel-2::conda-4.3.30-py36h5d9f9f4_0',
                'channel-4::conda-build-3.12.1-py36_0'
            ))
            assert convert_to_dist_str(unlink_precs) == unlink_order
            assert convert_to_dist_str(link_precs) == link_order
    finally:
        sys.prefix = saved_sys_prefix


def test_unfreeze_when_required(tmpdir):
    # The available packages are:
    # libfoo 1.0, 2.0
    # libbar 1.0, 2.0
    # foobar 1.0 : depends on libfoo 1.0, libbar 2.0
    # foobar 2.0 : depends on libfoo 2.0, libbar 2.0
    # qux 1.0: depends on libfoo 1.0, libbar 2.0
    # qux 2.0: depends on libfoo 2.0, libbar 1.0
    #
    # qux 1.0 and foobar 1.0 can be installed at the same time but
    # if foobar is installed first it must be downgraded from 2.0.
    # If foobar is frozen then no solution exists.

    specs = [MatchSpec("foobar"), MatchSpec('qux')]
    with get_solver_must_unfreeze(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-freeze::libbar-2.0-0',
            'channel-freeze::libfoo-1.0-0',
            'channel-freeze::foobar-1.0-0',
            'channel-freeze::qux-1.0-0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs = MatchSpec("foobar"),
    with get_solver_must_unfreeze(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-freeze::libbar-2.0-0',
            'channel-freeze::libfoo-2.0-0',
            'channel-freeze::foobar-2.0-0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    # When frozen there is no solution - but conda tries really hard to not freeze things that conflict
    #    this section of the test broke when we improved the detection of conflicting specs.
    # specs_to_add = MatchSpec("qux"),
    # with get_solver_must_unfreeze(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
    #     with pytest.raises(UnsatisfiableError):
    #         solver.solve_final_state(update_modifier=UpdateModifier.FREEZE_INSTALLED)

    specs_to_add = MatchSpec("qux"),
    with get_solver_must_unfreeze(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_SPECS)
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-freeze::libbar-2.0-0',
            'channel-freeze::libfoo-1.0-0',
            'channel-freeze::foobar-1.0-0',
            'channel-freeze::qux-1.0-0',
        ))
        assert convert_to_dist_str(final_state_2) == order


def test_auto_update_conda(tmpdir):
    specs = MatchSpec("conda=1.3"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::yaml-0.1.4-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::pyyaml-3.10-py27_0',
            'channel-1::conda-1.3.5-py27_0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    with env_vars({"CONDA_AUTO_UPDATE_CONDA": "yes"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        specs_to_add = MatchSpec("pytz"),
        with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print(convert_to_dist_str(final_state_2))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::yaml-0.1.4-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.7.5-0',
                'channel-1::pytz-2013b-py27_0',
                'channel-1::pyyaml-3.10-py27_0',
                'channel-1::conda-1.3.5-py27_0',
            ))
            assert convert_to_dist_str(final_state_2) == order

    saved_sys_prefix = sys.prefix
    try:
        sys.prefix = tmpdir.strpath
        with env_vars({"CONDA_AUTO_UPDATE_CONDA": "yes"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            specs_to_add = MatchSpec("pytz"),
            with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
                final_state_2 = solver.solve_final_state()
                # PrefixDag(final_state_2, specs).open_url()
                print(convert_to_dist_str(final_state_2))
                order = add_subdir_to_iter((
                    'channel-1::openssl-1.0.1c-0',
                    'channel-1::readline-6.2-0',
                    'channel-1::sqlite-3.7.13-0',
                    'channel-1::system-5.8-1',
                    'channel-1::tk-8.5.13-0',
                    'channel-1::yaml-0.1.4-0',
                    'channel-1::zlib-1.2.7-0',
                    'channel-1::python-2.7.5-0',
                    'channel-1::pytz-2013b-py27_0',
                    'channel-1::pyyaml-3.10-py27_0',
                    'channel-1::conda-1.5.2-py27_0',
                ))
                assert convert_to_dist_str(final_state_2) == order

        with env_vars({"CONDA_AUTO_UPDATE_CONDA": "no"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            specs_to_add = MatchSpec("pytz"),
            with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
                final_state_2 = solver.solve_final_state()
                # PrefixDag(final_state_2, specs).open_url()
                print(convert_to_dist_str(final_state_2))
                order = add_subdir_to_iter((
                    'channel-1::openssl-1.0.1c-0',
                    'channel-1::readline-6.2-0',
                    'channel-1::sqlite-3.7.13-0',
                    'channel-1::system-5.8-1',
                    'channel-1::tk-8.5.13-0',
                    'channel-1::yaml-0.1.4-0',
                    'channel-1::zlib-1.2.7-0',
                    'channel-1::python-2.7.5-0',
                    'channel-1::pytz-2013b-py27_0',
                    'channel-1::pyyaml-3.10-py27_0',
                    'channel-1::conda-1.3.5-py27_0',
                ))
                assert convert_to_dist_str(final_state_2) == order
    finally:
        sys.prefix = saved_sys_prefix


def test_explicit_conda_downgrade(tmpdir):
    specs = MatchSpec("conda=1.5"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::yaml-0.1.4-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::pyyaml-3.10-py27_0',
            'channel-1::conda-1.5.2-py27_0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    with env_vars({"CONDA_AUTO_UPDATE_CONDA": "yes"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        specs_to_add = MatchSpec("conda=1.3"),
        with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            # PrefixDag(final_state_2, specs).open_url()
            print(convert_to_dist_str(final_state_2))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::yaml-0.1.4-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.7.5-0',
                'channel-1::pyyaml-3.10-py27_0',
                'channel-1::conda-1.3.5-py27_0',
            ))
            assert convert_to_dist_str(final_state_2) == order

    saved_sys_prefix = sys.prefix
    try:
        sys.prefix = tmpdir.strpath
        with env_vars({"CONDA_AUTO_UPDATE_CONDA": "yes"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            specs_to_add = MatchSpec("conda=1.3"),
            with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
                final_state_2 = solver.solve_final_state()
                # PrefixDag(final_state_2, specs).open_url()
                print(convert_to_dist_str(final_state_2))
                order = add_subdir_to_iter((
                    'channel-1::openssl-1.0.1c-0',
                    'channel-1::readline-6.2-0',
                    'channel-1::sqlite-3.7.13-0',
                    'channel-1::system-5.8-1',
                    'channel-1::tk-8.5.13-0',
                    'channel-1::yaml-0.1.4-0',
                    'channel-1::zlib-1.2.7-0',
                    'channel-1::python-2.7.5-0',
                    'channel-1::pyyaml-3.10-py27_0',
                    'channel-1::conda-1.3.5-py27_0',
                ))
                assert convert_to_dist_str(final_state_2) == order

        with env_vars({"CONDA_AUTO_UPDATE_CONDA": "no"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            specs_to_add = MatchSpec("conda=1.3"),
            with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
                final_state_2 = solver.solve_final_state()
                # PrefixDag(final_state_2, specs).open_url()
                print(convert_to_dist_str(final_state_2))
                order = add_subdir_to_iter((
                    'channel-1::openssl-1.0.1c-0',
                    'channel-1::readline-6.2-0',
                    'channel-1::sqlite-3.7.13-0',
                    'channel-1::system-5.8-1',
                    'channel-1::tk-8.5.13-0',
                    'channel-1::yaml-0.1.4-0',
                    'channel-1::zlib-1.2.7-0',
                    'channel-1::python-2.7.5-0',
                    'channel-1::pyyaml-3.10-py27_0',
                    'channel-1::conda-1.3.5-py27_0',
                ))
                assert convert_to_dist_str(final_state_2) == order
    finally:
        sys.prefix = saved_sys_prefix


def test_aggressive_update_packages(tmpdir):
    def solve(prev_state, specs_to_add, order):
        final_state_1, specs = prev_state
        specs_to_add = tuple(MatchSpec(spec_str) for spec_str in specs_to_add)
        with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state()
            print(convert_to_dist_str(final_state_2))
            assert convert_to_dist_str(final_state_2) == order
        concat_specs = specs + specs_to_add
        return final_state_2, concat_specs
    # test with "libpng", "cmake": both have multiple versions and no requirements in "channel-1"

    empty_state = ((), ())
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": ""}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        base_state = solve(
            empty_state, ["libpng=1.2"],
            add_subdir_to_iter((
                'channel-1::libpng-1.2.50-0',
            )))

    # # ~~has "libpng" restricted to "=1.2" by history_specs~~ NOPE!
    # In conda 4.6 making aggressive_update *more* aggressive, making it override history specs.
    state_1 = base_state
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": "libpng"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        solve(
            state_1, ["cmake=2.8.9"],
            add_subdir_to_iter((
                'channel-1::cmake-2.8.9-0',
                'channel-1::libpng-1.5.13-1',
            )))
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": ""}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        state_1_2 = solve(
            state_1, ["cmake=2.8.9"],
            add_subdir_to_iter((
                'channel-1::cmake-2.8.9-0',
                'channel-1::libpng-1.2.50-0',
            )))
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": "libpng"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        solve(
            state_1_2, ["cmake>2.8.9"],
            add_subdir_to_iter((
                'channel-1::cmake-2.8.10.2-0',
                'channel-1::libpng-1.5.13-1',
            )))

    # use new history_specs to remove "libpng" version restriction
    state_2 = (base_state[0], (MatchSpec("libpng"),))
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": "libpng"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        solve(
            state_2, ["cmake=2.8.9"],
            add_subdir_to_iter((
                'channel-1::cmake-2.8.9-0',
                'channel-1::libpng-1.5.13-1',
            )))
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": ""}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        state_2_2 = solve(
            state_2, ["cmake=2.8.9"],
            add_subdir_to_iter((
                'channel-1::cmake-2.8.9-0',
                'channel-1::libpng-1.2.50-0',
            )))
    with env_vars({"CONDA_AGGRESSIVE_UPDATE_PACKAGES": "libpng"}, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        solve(
            state_2_2, ["cmake>2.8.9"],
            add_subdir_to_iter((
                'channel-1::cmake-2.8.10.2-0',
                'channel-1::libpng-1.5.13-1',
            )))

def test_python2_update(tmpdir):
    # Here we're actually testing that a user-request will uninstall incompatible packages
    # as necessary.
    specs = MatchSpec("conda"), MatchSpec("python=2")
    with get_solver_4(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        pprint(convert_to_dist_str(final_state_1))
        order1 = add_subdir_to_iter((
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::conda-env-2.6.0-1',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::yaml-0.1.7-had09818_2',
            'channel-4::zlib-1.2.11-ha838bed_2',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::sqlite-3.24.0-h84994c4_0',
            'channel-4::python-2.7.15-h1571d57_0',
            'channel-4::asn1crypto-0.24.0-py27_0',
            'channel-4::certifi-2018.8.13-py27_0',
            'channel-4::chardet-3.0.4-py27_1',
            'channel-4::cryptography-vectors-2.3-py27_0',
            'channel-4::enum34-1.1.6-py27_1',
            'channel-4::futures-3.2.0-py27_0',
            'channel-4::idna-2.7-py27_0',
            'channel-4::ipaddress-1.0.22-py27_0',
            'channel-4::pycosat-0.6.3-py27h14c3975_0',
            'channel-4::pycparser-2.18-py27_1',
            'channel-4::pysocks-1.6.8-py27_0',
            'channel-4::ruamel_yaml-0.15.46-py27h14c3975_0',
            'channel-4::six-1.11.0-py27_1',
            'channel-4::cffi-1.11.5-py27h9745a5d_0',
            'channel-4::cryptography-2.3-py27hb7f436b_0',
            'channel-4::pyopenssl-18.0.0-py27_0',
            'channel-4::urllib3-1.23-py27_0',
            'channel-4::requests-2.19.1-py27_0',
            'channel-4::conda-4.5.10-py27_0',
        ))
        assert convert_to_dist_str(final_state_1) == order1

    specs_to_add = MatchSpec("python=3"),
    with get_solver_4(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        pprint(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::conda-env-2.6.0-1',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::xz-5.2.4-h14c3975_4',
            'channel-4::yaml-0.1.7-had09818_2',
            'channel-4::zlib-1.2.11-ha838bed_2',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::sqlite-3.24.0-h84994c4_0',
            'channel-4::python-3.7.0-hc3d631a_0',
            'channel-4::asn1crypto-0.24.0-py37_0',
            'channel-4::certifi-2018.8.13-py37_0',
            'channel-4::chardet-3.0.4-py37_1',
            'channel-4::idna-2.7-py37_0',
            'channel-4::pycosat-0.6.3-py37h14c3975_0',
            'channel-4::pycparser-2.18-py37_1',
            'channel-4::pysocks-1.6.8-py37_0',
            'channel-4::ruamel_yaml-0.15.46-py37h14c3975_0',
            'channel-4::six-1.11.0-py37_1',
            'channel-4::cffi-1.11.5-py37h9745a5d_0',
            'channel-4::cryptography-2.2.2-py37h14c3975_0',
            'channel-4::pyopenssl-18.0.0-py37_0',
            'channel-4::urllib3-1.23-py37_0',
            'channel-4::requests-2.19.1-py37_0',
            'channel-4::conda-4.5.10-py37_0',
        ))
        assert convert_to_dist_str(final_state_2) == order


def test_update_deps_1(tmpdir):
    specs = MatchSpec("python=2"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        # print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs2 = MatchSpec("numpy=1.7.0"), MatchSpec("python=2.7.3")
    with get_solver(tmpdir, specs2, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.0-py27_0',
        ))
        assert convert_to_dist_str(final_state_2) == order

    specs_to_add = MatchSpec("iopro"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_2, history_specs=specs2) as solver:
        final_state_3a = solver.solve_final_state()
        print(convert_to_dist_str(final_state_3a))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.3-7',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.0-py27_0',
            'channel-1::iopro-1.5.0-np17py27_p0',
        ))
        assert convert_to_dist_str(final_state_3a) == order

    specs_to_add = MatchSpec("iopro"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_2, history_specs=specs2) as solver:
        final_state_3 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_DEPS)
        pprint(convert_to_dist_str(final_state_3))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',   # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',  # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            'channel-1::iopro-1.5.0-np17py27_p0',
        ))
        assert convert_to_dist_str(final_state_3) == order

    specs_to_add = MatchSpec("iopro"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_2, history_specs=specs2) as solver:
        final_state_3 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_DEPS,
                                                 deps_modifier=DepsModifier.ONLY_DEPS)
        pprint(convert_to_dist_str(final_state_3))
        order = add_subdir_to_iter((
            'channel-1::unixodbc-2.3.1-0',
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',   # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::numpy-1.7.1-py27_0',  # with update_deps, numpy should switch from 1.7.0 to 1.7.1
            # 'channel-1::iopro-1.5.0-np17py27_p0',
        ))
        assert convert_to_dist_str(final_state_3) == order


def test_update_deps_2(tmpdir):
    specs = MatchSpec("flask==0.12"), MatchSpec("jinja2==2.8")
    with get_solver_aggregate_2(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        pprint(convert_to_dist_str(final_state_1))
        order1 = add_subdir_to_iter((
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::xz-5.2.4-h14c3975_4',
            'channel-4::zlib-1.2.11-ha838bed_2',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::sqlite-3.24.0-h84994c4_0',
            'channel-4::python-3.6.6-hc3d631a_0',
            'channel-4::certifi-2018.8.13-py36_0',
            'channel-4::click-6.7-py36_0',
            'channel-4::itsdangerous-0.24-py36_1',
            'channel-4::markupsafe-1.0-py36h14c3975_1',
            'channel-4::werkzeug-0.14.1-py36_0',
            'channel-4::setuptools-40.0.0-py36_0',
            'channel-2::jinja2-2.8-py36_1',
            'channel-2::flask-0.12-py36_0',
        ))
        assert convert_to_dist_str(final_state_1) == order1

    # The "conda update flask" case is held back by the jinja2==2.8 user-requested spec.
    specs_to_add = MatchSpec("flask"),
    with get_solver_aggregate_2(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = add_subdir_to_iter((
            'channel-2::flask-0.12-py36_0',
        ))
        link_order = add_subdir_to_iter((
            'channel-4::flask-0.12.2-py36hb24657c_0',
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order

    # Now solve with UPDATE_DEPS
    specs_to_add = MatchSpec("flask"),
    with get_solver_aggregate_2(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_precs, link_precs = solver.solve_for_diff(update_modifier=UpdateModifier.UPDATE_DEPS)
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = add_subdir_to_iter((
            'channel-2::flask-0.12-py36_0',
            'channel-2::jinja2-2.8-py36_1',
        ))
        link_order = add_subdir_to_iter((
            'channel-4::jinja2-2.10-py36_0',
            'channel-4::flask-1.0.2-py36_1',
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order


def test_fast_update_with_update_modifier_not_set(tmpdir):
    specs = MatchSpec("python=2"), MatchSpec("openssl==1.0.2l"), MatchSpec("sqlite=3.21"),
    with get_solver_4(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        pprint(convert_to_dist_str(final_state_1))
        order1 = add_subdir_to_iter((
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::ncurses-6.0-h9df7e31_2',
            'channel-4::openssl-1.0.2l-h077ae2c_5',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::zlib-1.2.11-ha838bed_2',
            'channel-4::libedit-3.1-heed3624_0',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::sqlite-3.21.0-h1bed415_2',
            'channel-4::python-2.7.14-h89e7a4a_22',
        ))
        assert convert_to_dist_str(final_state_1) == order1

    specs_to_add = MatchSpec("python"),
    with get_solver_4(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = add_subdir_to_iter((
            'channel-4::python-2.7.14-h89e7a4a_22',
            'channel-4::libedit-3.1-heed3624_0',
            'channel-4::openssl-1.0.2l-h077ae2c_5',
            'channel-4::ncurses-6.0-h9df7e31_2'
        ))
        link_order = add_subdir_to_iter((
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::xz-5.2.4-h14c3975_4',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::python-3.6.4-hc3d631a_1',  # python is upgraded
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order

    specs_to_add = MatchSpec("sqlite"),
    with get_solver_4(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = add_subdir_to_iter((
            'channel-4::python-2.7.14-h89e7a4a_22',
            'channel-4::sqlite-3.21.0-h1bed415_2',
            'channel-4::libedit-3.1-heed3624_0',
            'channel-4::openssl-1.0.2l-h077ae2c_5',
            'channel-4::ncurses-6.0-h9df7e31_2',
        ))
        link_order = add_subdir_to_iter((
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::sqlite-3.24.0-h84994c4_0',  # sqlite is upgraded
            'channel-4::python-2.7.15-h1571d57_0',  # python is not upgraded
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order

    specs_to_add = MatchSpec("sqlite"), MatchSpec("python"),
    with get_solver_4(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state(update_modifier=UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE)
        pprint(convert_to_dist_str(final_state_2))
        assert convert_to_dist_str(final_state_2) == order1


@pytest.mark.integration
def test_pinned_1(tmpdir):
    specs = MatchSpec("numpy"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        pprint(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-3.3.2-0',
            'channel-1::numpy-1.7.1-py33_0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    with env_var("CONDA_PINNED_PACKAGES", "python=2.6&iopro<=1.4.2", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        specs = MatchSpec("system=5.8=0"),
        with get_solver(tmpdir, specs) as solver:
            final_state_1 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            pprint(convert_to_dist_str(final_state_1))
            order = add_subdir_to_iter((
                'channel-1::system-5.8-0',
            ))
            assert convert_to_dist_str(final_state_1) == order

        # ignore_pinned=True
        specs_to_add = MatchSpec("python"),
        with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                        history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state(ignore_pinned=True)
            # PrefixDag(final_state_1, specs).open_url()
            pprint(convert_to_dist_str(final_state_2))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-0',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-3.3.2-0',
            ))
            assert convert_to_dist_str(final_state_2) == order

        # ignore_pinned=False
        specs_to_add = MatchSpec("python"),
        with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                        history_specs=specs) as solver:
            final_state_2 = solver.solve_final_state(ignore_pinned=False)
            # PrefixDag(final_state_1, specs).open_url()
            pprint(convert_to_dist_str(final_state_2))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-0',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::python-2.6.8-6',
            ))
            assert convert_to_dist_str(final_state_2) == order

        # incompatible CLI and configured specs
        specs_to_add = MatchSpec("scikit-learn==0.13"),
        with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                        history_specs=specs) as solver:
            with pytest.raises(SpecsConfigurationConflictError) as exc:
                solver.solve_final_state(ignore_pinned=False)
            kwargs = exc.value._kwargs
            assert kwargs["requested_specs"] == ["scikit-learn==0.13"]
            assert kwargs["pinned_specs"] == ["python=2.6"]

        specs_to_add = MatchSpec("numba"),
        history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"),
        with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_2,
                        history_specs=history_specs) as solver:
            final_state_3 = solver.solve_final_state()
            # PrefixDag(final_state_1, specs).open_url()
            pprint(convert_to_dist_str(final_state_3))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-0',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::llvm-3.2-0',
                'channel-1::python-2.6.8-6',
                'channel-1::argparse-1.2.1-py26_0',
                'channel-1::llvmpy-0.11.2-py26_0',
                'channel-1::numpy-1.7.1-py26_0',
                'channel-1::numba-0.8.1-np17py26_0',
            ))
            assert convert_to_dist_str(final_state_3) == order

        specs_to_add = MatchSpec("python"),
        history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"), MatchSpec("numba"),
        with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_3,
                        history_specs=history_specs) as solver:
            final_state_4 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_DEPS)
            # PrefixDag(final_state_1, specs).open_url()
            pprint(convert_to_dist_str(final_state_4))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::llvm-3.2-0',
                'channel-1::python-2.6.8-6',
                'channel-1::argparse-1.2.1-py26_0',
                'channel-1::llvmpy-0.11.2-py26_0',
                'channel-1::numpy-1.7.1-py26_0',
                'channel-1::numba-0.8.1-np17py26_0',
            ))
            assert convert_to_dist_str(final_state_4) == order

        specs_to_add = MatchSpec("python"),
        history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"), MatchSpec("numba"),
        with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_4,
                        history_specs=history_specs) as solver:
            final_state_5 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_ALL)
            # PrefixDag(final_state_1, specs).open_url()
            pprint(convert_to_dist_str(final_state_5))
            order = add_subdir_to_iter((
                'channel-1::openssl-1.0.1c-0',
                'channel-1::readline-6.2-0',
                'channel-1::sqlite-3.7.13-0',
                'channel-1::system-5.8-1',
                'channel-1::tk-8.5.13-0',
                'channel-1::zlib-1.2.7-0',
                'channel-1::llvm-3.2-0',
                'channel-1::python-2.6.8-6',
                'channel-1::argparse-1.2.1-py26_0',
                'channel-1::llvmpy-0.11.2-py26_0',
                'channel-1::numpy-1.7.1-py26_0',
                'channel-1::numba-0.8.1-np17py26_0',
            ))
            assert convert_to_dist_str(final_state_5) == order

    # now update without pinning
    specs_to_add = MatchSpec("python"),
    history_specs = MatchSpec("python"), MatchSpec("system=5.8=0"), MatchSpec("numba"),
    with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_4,
                    history_specs=history_specs) as solver:
        final_state_5 = solver.solve_final_state(update_modifier=UpdateModifier.UPDATE_ALL)
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_5))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::llvm-3.2-0',
            'channel-1::python-3.3.2-0',
            'channel-1::llvmpy-0.11.2-py33_0',
            'channel-1::numpy-1.7.1-py33_0',
            'channel-1::numba-0.8.1-np17py33_0',
        ))
        assert convert_to_dist_str(final_state_5) == order


def test_no_update_deps_1(tmpdir):  # i.e. FREEZE_DEPS
    # NOTE: So far, NOT actually testing the FREEZE_DEPS flag.  I'm unable to contrive a
    # situation where it's actually needed.

    specs = MatchSpec("python=2"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_add = MatchSpec("zope.interface"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
            'channel-1::nose-1.3.0-py27_0',
            'channel-1::zope.interface-4.0.5-py27_0',
        ))
        assert convert_to_dist_str(final_state_2) == order

    specs_to_add = MatchSpec("zope.interface>4.1"),
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        with pytest.raises(UnsatisfiableError):
            final_state_2 = solver.solve_final_state()

    # allow python to float
    specs_to_add = MatchSpec("zope.interface>4.1"), MatchSpec("python")
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        final_state_2 = solver.solve_final_state()
        # PrefixDag(final_state_2, specs).open_url()
        print(convert_to_dist_str(final_state_2))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-3.3.2-0',
            'channel-1::nose-1.3.0-py33_0',
            'channel-1::zope.interface-4.1.1.1-py33_0',
        ))
        assert convert_to_dist_str(final_state_2) == order


def test_force_reinstall_1(tmpdir):
    specs = MatchSpec("python=2"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_add = specs
    with get_solver(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_dists, link_dists = solver.solve_for_diff()
        assert not unlink_dists
        assert not link_dists

        unlink_dists, link_dists = solver.solve_for_diff(force_reinstall=True)
        assert len(unlink_dists) == len(link_dists) == 1
        assert unlink_dists[0] == link_dists[0]

        unlink_dists, link_dists = solver.solve_for_diff()
        assert not unlink_dists
        assert not link_dists


def test_force_reinstall_2(tmpdir):
    specs = MatchSpec("python=2"),
    with get_solver(tmpdir, specs) as solver:
        unlink_dists, link_dists = solver.solve_for_diff(force_reinstall=True)
        assert not unlink_dists
        # PrefixDag(final_state_1, specs).open_url()
        print(convert_to_dist_str(link_dists))
        order = add_subdir_to_iter((
            'channel-1::openssl-1.0.1c-0',
            'channel-1::readline-6.2-0',
            'channel-1::sqlite-3.7.13-0',
            'channel-1::system-5.8-1',
            'channel-1::tk-8.5.13-0',
            'channel-1::zlib-1.2.7-0',
            'channel-1::python-2.7.5-0',
        ))
        assert convert_to_dist_str(link_dists) == order


def test_timestamps_1(tmpdir):
    specs = MatchSpec("python=3.6.2"),
    with get_solver_4(tmpdir, specs) as solver:
        unlink_dists, link_dists = solver.solve_for_diff(force_reinstall=True)
        assert not unlink_dists
        pprint(convert_to_dist_str(link_dists))
        order = add_subdir_to_iter((
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::ncurses-6.0-h9df7e31_2',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::xz-5.2.4-h14c3975_4',
            'channel-4::zlib-1.2.11-ha838bed_2',
            'channel-4::libedit-3.1-heed3624_0',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::sqlite-3.23.1-he433501_0',
            'channel-4::python-3.6.2-hca45abc_19',  # this package has a later timestamp but lower hash value
                                                    # than the alternate 'channel-4::python-3.6.2-hda45abc_19'
        ))
        assert convert_to_dist_str(link_dists) == order

def test_channel_priority_churn_minimized(tmpdir):
    specs = MatchSpec("conda-build"), MatchSpec("itsdangerous"),
    with get_solver_aggregate_2(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()

    pprint(convert_to_dist_str(final_state))

    with get_solver_aggregate_2(tmpdir, [MatchSpec('itsdangerous')],
                                prefix_records=final_state, history_specs=specs) as solver:
        solver.channels.reverse()
        unlink_dists, link_dists = solver.solve_for_diff(
            update_modifier=UpdateModifier.FREEZE_INSTALLED)
        pprint(convert_to_dist_str(unlink_dists))
        pprint(convert_to_dist_str(link_dists))
        assert len(unlink_dists) == 1
        assert len(link_dists) == 1


def test_remove_with_constrained_dependencies(tmpdir):
    # This is a regression test for #6904. Up through conda 4.4.10, removal isn't working
    # correctly with constrained dependencies.
    specs = MatchSpec("conda"), MatchSpec("conda-build"),
    with get_solver_4(tmpdir, specs) as solver:
        unlink_dists_1, link_dists_1 = solver.solve_for_diff()
        assert not unlink_dists_1
        pprint(convert_to_dist_str(link_dists_1))
        assert not unlink_dists_1
        order = add_subdir_to_iter((
            'channel-4::ca-certificates-2018.03.07-0',
            'channel-4::conda-env-2.6.0-1',
            'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
            'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
            'channel-4::libffi-3.2.1-hd88cf55_4',
            'channel-4::ncurses-6.1-hf484d3e_0',
            'channel-4::openssl-1.0.2p-h14c3975_0',
            'channel-4::patchelf-0.9-hf484d3e_2',
            'channel-4::tk-8.6.7-hc745277_3',
            'channel-4::xz-5.2.4-h14c3975_4',
            'channel-4::yaml-0.1.7-had09818_2',
            'channel-4::zlib-1.2.11-ha838bed_2',
            'channel-4::libedit-3.1.20170329-h6b74fdf_2',
            'channel-4::readline-7.0-ha6073c6_4',
            'channel-4::sqlite-3.24.0-h84994c4_0',
            'channel-4::python-3.7.0-hc3d631a_0',
            'channel-4::asn1crypto-0.24.0-py37_0',
            'channel-4::beautifulsoup4-4.6.3-py37_0',
            'channel-4::certifi-2018.8.13-py37_0',
            'channel-4::chardet-3.0.4-py37_1',
            'channel-4::cryptography-vectors-2.3-py37_0',
            'channel-4::filelock-3.0.4-py37_0',
            'channel-4::glob2-0.6-py37_0',
            'channel-4::idna-2.7-py37_0',
            'channel-4::markupsafe-1.0-py37h14c3975_1',
            'channel-4::pkginfo-1.4.2-py37_1',
            'channel-4::psutil-5.4.6-py37h14c3975_0',
            'channel-4::pycosat-0.6.3-py37h14c3975_0',
            'channel-4::pycparser-2.18-py37_1',
            'channel-4::pysocks-1.6.8-py37_0',
            'channel-4::pyyaml-3.13-py37h14c3975_0',
            'channel-4::ruamel_yaml-0.15.46-py37h14c3975_0',
            'channel-4::six-1.11.0-py37_1',
            'channel-4::cffi-1.11.5-py37h9745a5d_0',
            'channel-4::setuptools-40.0.0-py37_0',
            'channel-4::cryptography-2.3-py37hb7f436b_0',
            'channel-4::jinja2-2.10-py37_0',
            'channel-4::pyopenssl-18.0.0-py37_0',
            'channel-4::urllib3-1.23-py37_0',
            'channel-4::requests-2.19.1-py37_0',
            'channel-4::conda-4.5.10-py37_0',
            'channel-4::conda-build-3.12.1-py37_0',
        ))
        assert convert_to_dist_str(link_dists_1) == order

    specs_to_remove = MatchSpec("pycosat"),
    with get_solver_4(tmpdir, specs_to_remove=specs_to_remove, prefix_records=link_dists_1, history_specs=specs) as solver:
        unlink_dists_2, link_dists_2 = solver.solve_for_diff()
        assert not link_dists_2
        pprint(convert_to_dist_str(unlink_dists_2))
        order = add_subdir_to_iter((
            'channel-4::conda-build-3.12.1-py37_0',
            'channel-4::conda-4.5.10-py37_0',
            'channel-4::pycosat-0.6.3-py37h14c3975_0',
        ))
        for spec in order:
            assert spec in convert_to_dist_str(unlink_dists_2)


def test_priority_1(tmpdir):
    with env_var("CONDA_SUBDIR", "linux-64", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        specs = MatchSpec("pandas"), MatchSpec("python=2.7"),
        with env_var("CONDA_CHANNEL_PRIORITY", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with get_solver_aggregate_1(tmpdir, specs) as solver:
                final_state_1 = solver.solve_final_state()
                pprint(convert_to_dist_str(final_state_1))
                order = add_subdir_to_iter((
                    'channel-2::mkl-2017.0.3-0',
                    'channel-2::openssl-1.0.2l-0',
                    'channel-2::readline-6.2-2',
                    'channel-2::sqlite-3.13.0-0',
                    'channel-2::tk-8.5.18-0',
                    'channel-2::zlib-1.2.11-0',
                    'channel-2::python-2.7.13-0',
                    'channel-2::numpy-1.13.1-py27_0',
                    'channel-2::pytz-2017.2-py27_0',
                    'channel-2::six-1.10.0-py27_0',
                    'channel-2::python-dateutil-2.6.1-py27_0',
                    'channel-2::pandas-0.20.3-py27_0',
                ))
                assert convert_to_dist_str(final_state_1) == order

        with env_var("CONDA_CHANNEL_PRIORITY", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with get_solver_aggregate_1(tmpdir, specs, prefix_records=final_state_1,
                                        history_specs=specs) as solver:
                final_state_2 = solver.solve_final_state()
                pprint(convert_to_dist_str(final_state_2))
                # python and pandas will be updated as they are explicit specs.  Other stuff may or may not,
                #     as required to satisfy python and pandas
                order = add_subdir_to_iter((
                    'channel-4::python-2.7.15-h1571d57_0',
                    'channel-4::pandas-0.23.4-py27h04863e7_0',
                ))
                for spec in order:
                    assert spec in convert_to_dist_str(final_state_2)

        # channel priority taking effect here.  channel-2 should be the channel to draw from.  Downgrades expected.
        # python and pandas will be updated as they are explicit specs.  Other stuff may or may not,
        #     as required to satisfy python and pandas
        with get_solver_aggregate_1(tmpdir, specs, prefix_records=final_state_2,
                                    history_specs=specs) as solver:
            final_state_3 = solver.solve_final_state()
            pprint(convert_to_dist_str(final_state_3))
            order = add_subdir_to_iter((
                'channel-2::python-2.7.13-0',
                'channel-2::pandas-0.20.3-py27_0',
            ))
            for spec in order:
                assert spec in convert_to_dist_str(final_state_3)

        specs_to_add = MatchSpec("six<1.10"),
        specs_to_remove = MatchSpec("pytz"),
        with get_solver_aggregate_1(tmpdir, specs_to_add=specs_to_add, specs_to_remove=specs_to_remove,
                                    prefix_records=final_state_3, history_specs=specs) as solver:
            final_state_4 = solver.solve_final_state()
            pprint(convert_to_dist_str(final_state_4))
            order = add_subdir_to_iter((
                'channel-2::python-2.7.13-0',
                'channel-2::six-1.9.0-py27_0',
            ))
            for spec in order:
                assert spec in convert_to_dist_str(final_state_4)
            assert 'pandas' not in convert_to_dist_str(final_state_4)


def test_features_solve_1(tmpdir):
    # in this test, channel-2 is a view of pkgs/free/linux-64
    #   and channel-4 is a view of the newer pkgs/main/linux-64
    # The channel list, equivalent to context.channels is ('channel-2', 'channel-4')
    specs = (MatchSpec("python=2.7"), MatchSpec("numpy"), MatchSpec("nomkl"))
    with env_var("CONDA_CHANNEL_PRIORITY", "True", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with get_solver_aggregate_1(tmpdir, specs) as solver:
            final_state_1 = solver.solve_final_state()
            pprint(convert_to_dist_str(final_state_1))
            order = add_subdir_to_iter((
                'channel-2::nomkl-1.0-0',
                'channel-2::libgfortran-3.0.0-1',
                'channel-2::openssl-1.0.2l-0',
                'channel-2::readline-6.2-2',
                'channel-2::sqlite-3.13.0-0',
                'channel-2::tk-8.5.18-0',
                'channel-2::zlib-1.2.11-0',
                'channel-2::openblas-0.2.19-0',
                'channel-2::python-2.7.13-0',
                'channel-2::numpy-1.13.1-py27_nomkl_0',
            ))
            assert convert_to_dist_str(final_state_1) == order

    with env_var("CONDA_CHANNEL_PRIORITY", "False", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with get_solver_aggregate_1(tmpdir, specs) as solver:
            final_state_1 = solver.solve_final_state()
            pprint(convert_to_dist_str(final_state_1))
            order = add_subdir_to_iter((
                'channel-4::blas-1.0-openblas',
                'channel-4::ca-certificates-2018.03.07-0',
                'channel-2::libffi-3.2.1-1',
                'channel-4::libgcc-ng-8.2.0-hdf63c60_0',
                'channel-4::libgfortran-ng-7.2.0-hdf63c60_3',
                'channel-4::libstdcxx-ng-8.2.0-hdf63c60_0',
                'channel-2::zlib-1.2.11-0',
                'channel-4::libopenblas-0.2.20-h9ac9557_7',
                'channel-4::ncurses-6.1-hf484d3e_0',
                'channel-4::nomkl-3.0-0',
                'channel-4::openssl-1.0.2p-h14c3975_0',
                'channel-4::tk-8.6.7-hc745277_3',
                'channel-4::libedit-3.1.20170329-h6b74fdf_2',
                'channel-4::readline-7.0-ha6073c6_4',
                'channel-4::sqlite-3.24.0-h84994c4_0',
                'channel-4::python-2.7.15-h1571d57_0',
                'channel-4::numpy-base-1.15.0-py27h7cdd4dd_0',
                'channel-4::numpy-1.15.0-py27h2aefc1b_0',
            ))
            assert convert_to_dist_str(final_state_1) == order


@pytest.mark.integration  # this test is slower, so we'll lump it into integration
def test_freeze_deps_1(tmpdir):
    specs = MatchSpec("six=1.7"),
    with get_solver_2(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
        pprint(convert_to_dist_str(final_state_1))
        order = add_subdir_to_iter((
            'channel-2::openssl-1.0.2l-0',
            'channel-2::readline-6.2-2',
            'channel-2::sqlite-3.13.0-0',
            'channel-2::tk-8.5.18-0',
            'channel-2::xz-5.2.3-0',
            'channel-2::zlib-1.2.11-0',
            'channel-2::python-3.4.5-0',
            'channel-2::six-1.7.3-py34_0',
        ))
        assert convert_to_dist_str(final_state_1) == order

    specs_to_add = MatchSpec("bokeh"),
    with get_solver_2(tmpdir, specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = ()
        link_order = add_subdir_to_iter((
            'channel-2::mkl-2017.0.3-0',
            'channel-2::yaml-0.1.6-0',
            'channel-2::backports_abc-0.5-py34_0',
            'channel-2::markupsafe-1.0-py34_0',
            'channel-2::numpy-1.13.0-py34_0',
            'channel-2::pyyaml-3.12-py34_0',
            'channel-2::requests-2.14.2-py34_0',
            'channel-2::setuptools-27.2.0-py34_0',
            'channel-2::jinja2-2.9.6-py34_0',
            'channel-2::python-dateutil-2.6.1-py34_0',
            'channel-2::tornado-4.4.2-py34_0',
            'channel-2::bokeh-0.12.4-py34_0',
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order

    # now we can't install the latest bokeh 0.12.5, but instead we get bokeh 0.12.4
    specs_to_add = MatchSpec("bokeh"),
    with get_solver_2(tmpdir, specs_to_add, prefix_records=final_state_1,
                      history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = ()
        link_order = add_subdir_to_iter((
            'channel-2::mkl-2017.0.3-0',
            'channel-2::yaml-0.1.6-0',
            'channel-2::backports_abc-0.5-py34_0',
            'channel-2::markupsafe-1.0-py34_0',
            'channel-2::numpy-1.13.0-py34_0',
            'channel-2::pyyaml-3.12-py34_0',
            'channel-2::requests-2.14.2-py34_0',
            'channel-2::setuptools-27.2.0-py34_0',
            'channel-2::jinja2-2.9.6-py34_0',
            'channel-2::python-dateutil-2.6.1-py34_0',
            'channel-2::tornado-4.4.2-py34_0',
            'channel-2::bokeh-0.12.4-py34_0',
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order

    # here, the python=3.4 spec can't be satisfied, so it's dropped, and we go back to py27
    with pytest.raises(UnsatisfiableError):
        specs_to_add = MatchSpec("bokeh=0.12.5"),
        with get_solver_2(tmpdir, specs_to_add, prefix_records=final_state_1,
                        history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
            unlink_precs, link_precs = solver.solve_for_diff()

    # adding the explicit python spec allows conda to change the python versions.
    # one possible outcome is that this updates to python 3.6.  That is not desirable because of the
    #    explicit "six=1.7" request in the history.  It should only neuter that spec if there's no way
    #    to solve it with that spec.
    specs_to_add = MatchSpec("bokeh=0.12.5"), MatchSpec("python")
    with get_solver_2(tmpdir, specs_to_add, prefix_records=final_state_1,
                      history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
        unlink_precs, link_precs = solver.solve_for_diff()
        pprint(convert_to_dist_str(unlink_precs))
        pprint(convert_to_dist_str(link_precs))
        unlink_order = add_subdir_to_iter((
            'channel-2::six-1.7.3-py34_0',
            'channel-2::python-3.4.5-0',
            'channel-2::xz-5.2.3-0',
        ))
        link_order = add_subdir_to_iter((
            'channel-2::mkl-2017.0.3-0',
            'channel-2::yaml-0.1.6-0',
            'channel-2::python-2.7.13-0',
            'channel-2::backports-1.0-py27_0',
            'channel-2::backports_abc-0.5-py27_0',
            'channel-2::certifi-2016.2.28-py27_0',
            'channel-2::futures-3.1.1-py27_0',
            'channel-2::markupsafe-1.0-py27_0',
            'channel-2::numpy-1.13.1-py27_0',
            'channel-2::pyyaml-3.12-py27_0',
            'channel-2::requests-2.14.2-py27_0',
            'channel-2::six-1.7.3-py27_0',
            'channel-2::python-dateutil-2.6.1-py27_0',
            'channel-2::setuptools-36.4.0-py27_1',
            'channel-2::singledispatch-3.4.0.3-py27_0',
            'channel-2::ssl_match_hostname-3.5.0.1-py27_0',
            'channel-2::jinja2-2.9.6-py27_0',
            'channel-2::tornado-4.5.2-py27_0',
            'channel-2::bokeh-0.12.5-py27_1',
        ))
        assert convert_to_dist_str(unlink_precs) == unlink_order
        assert convert_to_dist_str(link_precs) == link_order

    # here, the python=3.4 spec can't be satisfied, so it's dropped, and we go back to py27
    specs_to_add = MatchSpec("bokeh=0.12.5"),
    with get_solver_2(tmpdir, specs_to_add, prefix_records=final_state_1,
                      history_specs=(MatchSpec("six=1.7"), MatchSpec("python=3.4"))) as solver:
        with pytest.raises(UnsatisfiableError):
            solver.solve_final_state(update_modifier=UpdateModifier.FREEZE_INSTALLED)


# class PrivateEnvTests(TestCase):

#     def setUp(self):
#         self.prefix = '/a/test/c/prefix'

#         self.preferred_env = "_spiffy-test-app_"
#         self.preferred_env_prefix = join(self.prefix, 'envs', self.preferred_env)

#         # self.save_path_conflict = os.environ.get('CONDA_PATH_CONFLICT')
#         self.saved_values = {}
#         self.saved_values['CONDA_ROOT_PREFIX'] = os.environ.get('CONDA_ROOT_PREFIX')
#         self.saved_values['CONDA_ENABLE_PRIVATE_ENVS'] = os.environ.get('CONDA_ENABLE_PRIVATE_ENVS')

#         # os.environ['CONDA_PATH_CONFLICT'] = 'prevent'
#         os.environ['CONDA_ROOT_PREFIX'] = self.prefix
#         os.environ['CONDA_ENABLE_PRIVATE_ENVS'] = 'true'

#         reset_context()

#     def tearDown(self):
#         for key, value in iteritems(self.saved_values):
#             if value is not None:
#                 os.environ[key] = value
#             else:
#                 del os.environ[key]

#         reset_context()

    # @patch.object(Context, 'prefix_specified')
    # def test_simple_install_uninstall(self, prefix_specified):
    #     prefix_specified.__get__ = Mock(return_value=False)
    #
    #     specs = MatchSpec("spiffy-test-app"),
    #     with get_solver_3(specs) as solver:
    #         final_state_1 = solver.solve_final_state()
    #         # PrefixDag(final_state_1, specs).open_url()
    #         print(convert_to_dist_str(final_state_1))
    #         order = (
    #             'channel-1::openssl-1.0.2l-0',
    #             'channel-1::readline-6.2-2',
    #             'channel-1::sqlite-3.13.0-0',
    #             'channel-1::tk-8.5.18-0',
    #             'channel-1::zlib-1.2.8-3',
    #             'channel-1::python-2.7.13-0',
    #             'channel-1::spiffy-test-app-2.0-py27hf99fac9_0',
    #         )
    #         assert tuple(final_state_1) == tuple(solver._index[Dist(d)] for d in order)
    #
    #     specs_to_add = MatchSpec("uses-spiffy-test-app"),
    #     with get_solver_3(specs_to_add, prefix_records=final_state_1, history_specs=specs) as solver:
    #         final_state_2 = solver.solve_final_state()
    #         # PrefixDag(final_state_2, specs).open_url()
    #         print(convert_to_dist_str(final_state_2))
    #         order = (
    #
    #         )
    #         assert tuple(final_state_2) == tuple(solver._index[Dist(d)] for d in order)
    #
    #     specs = specs + specs_to_add
    #     specs_to_remove = MatchSpec("uses-spiffy-test-app"),
    #     with get_solver_3(specs_to_remove=specs_to_remove, prefix_records=final_state_2,
    #                       history_specs=specs) as solver:
    #         final_state_3 = solver.solve_final_state()
    #         # PrefixDag(final_state_2, specs).open_url()
    #         print(convert_to_dist_str(final_state_3))
    #         order = (
    #
    #         )
    #         assert tuple(final_state_3) == tuple(solver._index[Dist(d)] for d in order)


def test_current_repodata_usage(tmpdir):
    # force this to False, because otherwise tests fail when run with old conda-build
    with env_var('CONDA_USE_ONLY_TAR_BZ2', False, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        solver = _get_solver_class()(
            tmpdir.strpath, (Channel(CHANNEL_DIR),), ('win-64',),
            specs_to_add=[MatchSpec('zlib')], repodata_fn='current_repodata.json'
        )
        final_state = solver.solve_final_state()
        # zlib 1.2.11, vc 14.1, vs2015_runtime, virtual package for vc track_feature
        assert final_state
        checked = False
        for prec in final_state:
            if prec.name == 'zlib':
                assert prec.version == '1.2.11'
                assert prec.fn.endswith('.conda')
                checked = True
        if not checked:
            raise ValueError("Didn't have expected state in solve (needed zlib record)")


def test_current_repodata_fallback(tmpdir):
    solver = _get_solver_class()(
        tmpdir.strpath, (Channel(CHANNEL_DIR),), ('win-64',),
        specs_to_add=[MatchSpec('zlib=1.2.8')]
    )
    final_state = solver.solve_final_state()
    # zlib 1.2.11, zlib 1.2.8, vc 14.1, vs2015_runtime, virtual package for vc track_feature
    assert final_state
    checked = False
    for prec in final_state:
        if prec.name == 'zlib':
            assert prec.version == '1.2.8'
            assert prec.fn.endswith('.tar.bz2')
            checked = True
    if not checked:
        raise ValueError("Didn't have expected state in solve (needed zlib record)")


def test_downgrade_python_prevented_with_sane_message(tmpdir):
    specs = MatchSpec("python=2.6"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()
    # PrefixDag(final_state_1, specs).open_url()
    pprint(convert_to_dist_str(final_state_1))
    order = add_subdir_to_iter((
        'channel-1::openssl-1.0.1c-0',
        'channel-1::readline-6.2-0',
        'channel-1::sqlite-3.7.13-0',
        'channel-1::system-5.8-1',
        'channel-1::tk-8.5.13-0',
        'channel-1::zlib-1.2.7-0',
        'channel-1::python-2.6.8-6',
    ))
    assert convert_to_dist_str(final_state_1) == order

    # incompatible CLI and configured specs
    specs_to_add = MatchSpec("scikit-learn==0.13"),
    with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        with pytest.raises(UnsatisfiableError) as exc:
            solver.solve_final_state()

        error_msg = str(exc.value).strip()
        assert "incompatible with the existing python installation in your environment:" in error_msg
        assert "- scikit-learn==0.13 -> python=2.7" in error_msg
        assert "Your python: python=2.6" in error_msg

    specs_to_add = MatchSpec("unsatisfiable-with-py26"),
    with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        with pytest.raises(UnsatisfiableError) as exc:
            solver.solve_final_state()
        error_msg = str(exc.value).strip()
        assert "incompatible with the existing python installation in your environment:" in error_msg
        assert "- unsatisfiable-with-py26 -> python=2.7" in error_msg
        assert "Your python: python=2.6"

fake_index = [
    PrefixRecord(
        package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test", fn="mypkg-0.1.1",
        build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
    ),
    PrefixRecord(
        package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.0", channel="test", subdir="conda-test", fn="mypkg-0.1.1",
        build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
    ),
    PrefixRecord(
        package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test", subdir="conda-test", fn="mypkgnot-1.1.1",
        build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg 0.1.0'], constrains=[]
    )
]


def test_packages_in_solution_change_already_newest(tmpdir):
    specs = MatchSpec("mypkg")
    pre_packages = {"mypkg": [("mypkg", "0.1.1")]}
    post_packages = {"mypkg": [("mypkg", "0.1.1")]}
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[specs])
    constrained = solver.get_constrained_packages(pre_packages, post_packages, fake_index)
    assert len(constrained) == 0


def test_packages_in_solution_change_needs_update(tmpdir):
    specs = MatchSpec("mypkg")
    pre_packages = {"mypkg": [("mypkg", "0.1.0")]}
    post_packages = {"mypkg": [("mypkg", "0.1.1")]}
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[specs])
    constrained = solver.get_constrained_packages(pre_packages, post_packages, fake_index)
    assert len(constrained) == 0


def test_packages_in_solution_change_constrained(tmpdir):
    specs = MatchSpec("mypkg")
    pre_packages = {"mypkg": [("mypkg", "0.1.0")]}
    post_packages = {"mypkg": [("mypkg", "0.1.0")]}
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[specs])
    constrained = solver.get_constrained_packages(pre_packages, post_packages, fake_index)
    assert len(constrained) == 1


def test_determine_constricting_specs_conflicts(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.0", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg 0.1.0'], constrains=[]
        )
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert any(i for i in constricting if i[0] == "mypkgnot")


def test_determine_constricting_specs_conflicts_upperbound(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg <=0.1.1'], constrains=[]
        )
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert any(i for i in constricting if i[0] == "mypkgnot")


def test_determine_constricting_specs_multi_conflicts(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg <=0.1.1'], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="notmypkg", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg 0.1.1'], constrains=[]
        )
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert any(i for i in constricting if i[0] == "mypkgnot")
    assert any(i for i in constricting if i[0] == "notmypkg")


def test_determine_constricting_specs_no_conflicts_upperbound_compound_depends(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg >=0.1.1,<0.2.1'], constrains=[]
        )
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert constricting is None


def test_determine_constricting_specs_no_conflicts_version_star(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg 0.1.*'], constrains=[]
        )
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert constricting is None


def test_determine_constricting_specs_no_conflicts_free(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert constricting is None


def test_determine_constricting_specs_no_conflicts_no_upperbound(tmpdir):
    solution_prec = [
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkg", version="0.1.1", channel="test", subdir="conda-test",
            fn="mypkg-0.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=[], constrains=[]
        ),
        PrefixRecord(
            package_type=PackageType.NOARCH_GENERIC, name="mypkgnot", version="1.1.1", channel="test",
            subdir="conda-test", fn="mypkgnot-1.1.1",
            build="pypi_0", build_number=1, paths_data=None, files=None, depends=['mypkg >=0.0.5'], constrains=[]
        )
    ]
    spec = MatchSpec("mypkg")
    solver = _get_solver_class()(tmpdir, (Channel(CHANNEL_DIR),), ('linux-64',),
                                 specs_to_add=[spec])
    constricting = solver.determine_constricting_specs(spec, solution_prec)
    assert constricting is None


@pytest.mark.integration
def test_indirect_dep_optimized_by_version_over_package_count(tmpdir):
    """We need to adjust the Anaconda metapackage - custom version - so that it keeps
    dependencies on all of its components.  That custom package is intended to free up constraints.  However,
    We learned the hard way that the changes in conda 4.7 can end up removing all components, because
    anaconda-custom doesn't actually depend on them.

    So, here we go: a new metapackage that we hotfix anaconda-custom to depend on.  This new metapackage
    is versioned similarly to the real anaconda metapackages, for the sake of accounting for
    different package collections in different anaconda versions.  This test is for the case where a newer
    version of that new metapackage has fewer deps (but newer version).  We want it to prefer the newer
    version.
    """
    specs = MatchSpec("anaconda=1.4"),
    with get_solver(tmpdir, specs) as solver:
        final_state_1 = solver.solve_final_state()

    # start out with the oldest anaconda.  Using that state, free up zeromq.  Doing this should result in
    #    two things:
    #    * the anaconda metapackage goes to the "custom" version
    #    * zeromq goes up one build number, from 0 to 1.
    #    * all the other packages from the original anaconda metapackage get removed.
    #      Only the packages from the _dummy_anaconda_impl remain, but they are new.
    # This does NOT work if you omit the anaconda matchspec here.  It is part of the history,
    #     and it must be supplied as an explicit spec to override that history.
    specs_to_add = MatchSpec("zeromq"), MatchSpec("anaconda")
    with get_solver(tmpdir, specs_to_add=specs_to_add, prefix_records=final_state_1,
                    history_specs=specs) as solver:
        final_state = solver.solve_final_state()

        # anaconda, _dummy_anaconda_impl, zeromq.  NOT bzip2
        #    note that bzip2 is extra - it would be one less removal - that's the big test here.
        #    bzip2 is part of the older _dummy_anaconda_impl

        for prec in final_state:
            if prec.name == 'anaconda':
                assert prec.version == '1.5.0'
            elif prec.name == 'zeromq':
                assert prec.build_number == 1
            elif prec.name == '_dummy_anaconda_impl':
                assert prec.version == "2.0"
