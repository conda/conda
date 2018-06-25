# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from pprint import pprint

from conda._vendor.auxlib.decorators import memoize
from conda.base.context import reset_context
from conda.common.io import env_var
from conda.exceptions import CyclicalDependencyError
from conda.models.match_spec import MatchSpec
import conda.models.prefix_graph
from conda.models.prefix_graph import PrefixGraph
import pytest
from tests.core.test_solve import get_solver_4, get_solver_5

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

@memoize
def get_conda_build_record_set():
    specs = MatchSpec("conda"), MatchSpec("conda-build"), MatchSpec("intel-openmp"),
    with get_solver_4(specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


@memoize
def get_pandas_record_set():
    specs = MatchSpec("pandas"), MatchSpec("python=2.7"), MatchSpec("numpy 1.13")
    with get_solver_4(specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


@memoize
def get_windows_conda_build_record_set():
    specs = (MatchSpec("conda"), MatchSpec("conda-build"), MatchSpec("affine"),
             MatchSpec("colour"), MatchSpec("uses-spiffy-test-app"),)
    with get_solver_5(specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


@memoize
def get_sqlite_cyclical_record_set():
    # sqlite-3.20.1-haaaaaaa_4
    specs = MatchSpec("sqlite=3.20.1[build_number=4]"), MatchSpec("flask"),
    with get_solver_4(specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


def test_prefix_graph_1():
    # Basic initial test for public methods of PrefixGraph.

    records, specs = get_conda_build_record_set()
    graph = PrefixGraph(records, specs)

    nodes = tuple(rec.name for rec in graph.records)
    pprint(nodes)
    order = (
        'intel-openmp',
        'ca-certificates',
        'conda-env',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'patchelf',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
        'requests',
        'conda',
        'conda-build',
    )
    assert nodes == order

    python_node = graph.get_node_by_name('python')
    python_ancestors = graph.all_ancestors(python_node)
    nodes = tuple(rec.name for rec in python_ancestors)
    pprint(nodes)
    order = (
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'tk',
        'xz',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
    )
    assert nodes == order

    python_descendants = graph.all_descendants(python_node)
    nodes = tuple(rec.name for rec in python_descendants)
    pprint(nodes)
    order = (
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
        'requests',
        'conda',
        'conda-build',
    )
    assert nodes == order

    # test remove_specs
    removed_nodes = graph.remove_spec(MatchSpec("requests"))
    nodes = tuple(rec.name for rec in removed_nodes)
    pprint(nodes)
    order = (
        'requests',
        'conda',
        'conda-build',
    )
    assert nodes == order

    nodes = tuple(rec.name for rec in graph.records)
    pprint(nodes)
    order = (
        'conda-env',
        'intel-openmp',
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'patchelf',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
    )
    assert nodes == order

    spec_matches = {
        'channel-4::intel-openmp-2018.0.3-0': {'intel-openmp'},
    }
    assert {node.dist_str(): set(str(ms) for ms in specs) for node, specs in graph.spec_matches.items()} == spec_matches

    removed_nodes = graph.prune()
    nodes = tuple(rec.dist_str() for rec in graph.records)
    pprint(nodes)
    order = (
        'channel-4::intel-openmp-2018.0.3-0',
    )
    assert nodes == order

    removed_nodes = tuple(rec.name for rec in removed_nodes)
    order = (
        'conda-env',
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'patchelf',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
    )
    pprint(removed_nodes)
    assert removed_nodes == order


def test_prefix_graph_2():
    records, specs = get_conda_build_record_set()
    graph = PrefixGraph(records, specs)

    conda_build_node = graph.get_node_by_name('conda-build')
    del graph.spec_matches[conda_build_node]

    nodes = tuple(rec.name for rec in graph.records)
    pprint(nodes)
    order = (
        'intel-openmp',
        'ca-certificates',
        'conda-env',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'patchelf',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
        'requests',
        'conda',
        'conda-build',
    )
    assert nodes == order

    removed_nodes = graph.prune()
    remaining_nodes = tuple(rec.name for rec in graph.records)
    pprint(remaining_nodes)
    order = (
        'intel-openmp',
        'ca-certificates',
        'conda-env',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'certifi',
        'chardet',
        'idna',
        'pycosat',
        'pycparser',
        'pysocks',
        'ruamel_yaml',
        'six',
        'cffi',
        'cryptography',
        'pyopenssl',
        'urllib3',
        'requests',
        'conda',
    )
    assert remaining_nodes == order

    order = (
        'patchelf',
        'beautifulsoup4',
        'filelock',
        'glob2',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pyyaml',
        'conda-verify',
        'setuptools',
        'jinja2',
        'conda-build',
    )
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == order


def test_remove_youngest_descendant_nodes_with_specs():
    records, specs = get_conda_build_record_set()
    graph = PrefixGraph(records, tuple(specs) + (MatchSpec("requests"),))

    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()

    remaining_nodes = tuple(rec.name for rec in graph.records)
    pprint(remaining_nodes)
    order = (
        'ca-certificates',
        'conda-env',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'patchelf',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
        'requests',
        'conda',
    )
    assert remaining_nodes == order

    order = (
        'intel-openmp',
        'conda-build',
    )
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == order

    # again
    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()

    remaining_nodes = tuple(rec.name for rec in graph.records)
    pprint(remaining_nodes)
    order = (
        'conda-env',
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'patchelf',
        'tk',
        'xz',
        'yaml',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'beautifulsoup4',
        'certifi',
        'chardet',
        'filelock',
        'glob2',
        'idna',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pycparser',
        'pysocks',
        'pyyaml',
        'ruamel_yaml',
        'six',
        'cffi',
        'conda-verify',
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
        'requests',
    )
    assert remaining_nodes == order

    order = (
        'conda',
    )
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == order

    # now test prune
    removed_nodes = graph.prune()

    remaining_nodes = tuple(rec.name for rec in graph.records)
    pprint(remaining_nodes)
    order = (
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'tk',
        'xz',
        'zlib',
        'libedit',
        'readline',
        'sqlite',
        'python',
        'asn1crypto',
        'certifi',
        'chardet',
        'idna',
        'pycparser',
        'pysocks',
        'six',
        'cffi',
        'cryptography',
        'pyopenssl',
        'urllib3',
        'requests',
    )
    assert remaining_nodes == order

    order = (
        'conda-env',
        'patchelf',
        'yaml',
        'beautifulsoup4',
        'filelock',
        'glob2',
        'markupsafe',
        'pkginfo',
        'psutil',
        'pycosat',
        'pyyaml',
        'ruamel_yaml',
        'conda-verify',
        'setuptools',
        'jinja2',
    )
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == order


def test_windows_sort_orders_1():
    # This test makes sure the windows-specific parts of _toposort_prepare_graph
    # are behaving correctly.

    old_on_win = conda.models.prefix_graph.on_win
    conda.models.prefix_graph.on_win = True
    try:
        records, specs = get_windows_conda_build_record_set()
        graph = PrefixGraph(records, specs)

        nodes = tuple(rec.dist_str() for rec in graph.records)
        print(nodes)
        order = (
            'channel-5::ca-certificates-2018.03.07-0',
            'channel-5::conda-env-2.6.0-h36134e3_1',
            'channel-5::vs2015_runtime-14.0.25123-3',
            'channel-5::vc-14-h0510ff6_3',
            'channel-5::openssl-1.0.2o-h8ea7d77_0',
            'channel-5::python-3.6.5-h0c2934d_0',
            'channel-5::yaml-0.1.7-hc54c509_2',
            'channel-5::pywin32-223-py36hfa6e2cd_1',
            'channel-5::menuinst-1.4.14-py36hfa6e2cd_0',  # on_win, menuinst should be very early
            'channel-5::asn1crypto-0.24.0-py36_0',
            'channel-5::beautifulsoup4-4.6.0-py36hd4cc5e8_1',
            'channel-5::certifi-2018.4.16-py36_0',
            'channel-5::chardet-3.0.4-py36h420ce6e_1',
            'channel-5::filelock-3.0.4-py36_0',
            'channel-5::glob2-0.6-py36hdf76b57_0',
            'channel-5::idna-2.7-py36_0',
            'channel-5::markupsafe-1.0-py36h0e26971_1',
            'channel-5::pkginfo-1.4.2-py36_1',
            'channel-5::psutil-5.4.6-py36hfa6e2cd_0',
            'channel-5::pycosat-0.6.3-py36h413d8a4_0',
            'channel-5::pycparser-2.18-py36hd053e01_1',
            'channel-5::pyyaml-3.12-py36h1d1928f_1',
            'channel-5::ruamel_yaml-0.15.40-py36hfa6e2cd_2',
            'channel-5::six-1.11.0-py36h4db2310_1',
            'channel-5::win_inet_pton-1.0.1-py36he67d7fd_1',
            'channel-5::wincertstore-0.2-py36h7fe50ca_0',
            'channel-5::cffi-1.11.5-py36h945400d_0',
            'channel-5::conda-verify-2.0.0-py36h065de53_0',
            'channel-5::pysocks-1.6.8-py36_0',
            'channel-5::setuptools-39.2.0-py36_0',
            'channel-5::cryptography-2.2.2-py36hfa6e2cd_0',
            'channel-5::jinja2-2.10-py36h292fed1_0',
            'channel-5::wheel-0.31.1-py36_0',
            'channel-5::pip-10.0.1-py36_0',  # pip always comes after python
            'channel-5::pyopenssl-18.0.0-py36_0',
            'channel-5::urllib3-1.23-py36_0',
            'channel-5::requests-2.19.1-py36_0',
            'channel-5::conda-4.5.4-py36_0',  # on_win, conda comes before all noarch: python packages (affine, colour, spiffy-test-app, uses-spiffy-test-app)
            'channel-5::affine-2.1.0-pyh128a3a6_1',
            'channel-5::colour-0.1.4-pyhd67b51d_0',
            'channel-5::conda-build-3.10.9-py36_0',
            'channel-5::spiffy-test-app-0.5-pyh6afbcc8_0',
            'channel-5::uses-spiffy-test-app-2.0-pyh18698f2_0',
        )
        assert nodes == order
    finally:
        conda.models.prefix_graph.on_win = old_on_win


def test_windows_sort_orders_2():
    # This test makes sure the windows-specific parts of _toposort_prepare_graph
    # are behaving correctly.

    with env_var('CONDA_ALLOW_CYCLES', 'false', reset_context):
        old_on_win = conda.models.prefix_graph.on_win
        conda.models.prefix_graph.on_win = False
        try:
            records, specs = get_windows_conda_build_record_set()
            graph = PrefixGraph(records, specs)

            python_node = graph.get_node_by_name('python')
            pip_node = graph.get_node_by_name('pip')
            assert pip_node in graph.graph[python_node]
            assert python_node in graph.graph[pip_node]

            nodes = tuple(rec.dist_str() for rec in graph.records)
            print(nodes)
            order = (
                'channel-5::ca-certificates-2018.03.07-0',
                'channel-5::conda-env-2.6.0-h36134e3_1',
                'channel-5::vs2015_runtime-14.0.25123-3',
                'channel-5::vc-14-h0510ff6_3',
                'channel-5::openssl-1.0.2o-h8ea7d77_0',
                'channel-5::python-3.6.5-h0c2934d_0',
                'channel-5::yaml-0.1.7-hc54c509_2',
                'channel-5::affine-2.1.0-pyh128a3a6_1',
                'channel-5::asn1crypto-0.24.0-py36_0',
                'channel-5::beautifulsoup4-4.6.0-py36hd4cc5e8_1',
                'channel-5::certifi-2018.4.16-py36_0',
                'channel-5::chardet-3.0.4-py36h420ce6e_1',
                'channel-5::colour-0.1.4-pyhd67b51d_0',
                'channel-5::filelock-3.0.4-py36_0',
                'channel-5::glob2-0.6-py36hdf76b57_0',
                'channel-5::idna-2.7-py36_0',
                'channel-5::markupsafe-1.0-py36h0e26971_1',
                'channel-5::pkginfo-1.4.2-py36_1',
                'channel-5::psutil-5.4.6-py36hfa6e2cd_0',
                'channel-5::pycosat-0.6.3-py36h413d8a4_0',
                'channel-5::pycparser-2.18-py36hd053e01_1',
                'channel-5::pywin32-223-py36hfa6e2cd_1',
                'channel-5::pyyaml-3.12-py36h1d1928f_1',
                'channel-5::ruamel_yaml-0.15.40-py36hfa6e2cd_2',
                'channel-5::six-1.11.0-py36h4db2310_1',
                'channel-5::spiffy-test-app-0.5-pyh6afbcc8_0',
                'channel-5::win_inet_pton-1.0.1-py36he67d7fd_1',
                'channel-5::wincertstore-0.2-py36h7fe50ca_0',
                'channel-5::cffi-1.11.5-py36h945400d_0',
                'channel-5::conda-verify-2.0.0-py36h065de53_0',
                'channel-5::menuinst-1.4.14-py36hfa6e2cd_0',  # not on_win, menuinst isn't changed
                'channel-5::pysocks-1.6.8-py36_0',
                'channel-5::setuptools-39.2.0-py36_0',
                'channel-5::uses-spiffy-test-app-2.0-pyh18698f2_0',
                'channel-5::cryptography-2.2.2-py36hfa6e2cd_0',
                'channel-5::jinja2-2.10-py36h292fed1_0',
                'channel-5::wheel-0.31.1-py36_0',
                'channel-5::pip-10.0.1-py36_0',  # pip always comes after python
                'channel-5::pyopenssl-18.0.0-py36_0',
                'channel-5::urllib3-1.23-py36_0',
                'channel-5::requests-2.19.1-py36_0',
                'channel-5::conda-4.5.4-py36_0',  # not on_win, no special treatment for noarch: python packages (affine, colour, spiffy-test-app, uses-spiffy-test-app)
                'channel-5::conda-build-3.10.9-py36_0',
            )
            assert nodes == order
        finally:
            conda.models.prefix_graph.on_win = old_on_win


def test_sort_without_prep():
    # Test the _toposort_prepare_graph method, here by not running it at all.
    # The method is invoked in every other test.  This is what happens when it's not invoked.

    with patch.object(conda.models.prefix_graph.PrefixGraph, '_toposort_prepare_graph', return_value=None):
        records, specs = get_windows_conda_build_record_set()
        graph = PrefixGraph(records, specs)

        python_node = graph.get_node_by_name('python')
        pip_node = graph.get_node_by_name('pip')
        assert pip_node in graph.graph[python_node]
        assert python_node in graph.graph[pip_node]

        nodes = tuple(rec.dist_str() for rec in graph.records)
        print(nodes)
        order = (
            'channel-5::ca-certificates-2018.03.07-0',
            'channel-5::conda-env-2.6.0-h36134e3_1',
            'channel-5::vs2015_runtime-14.0.25123-3',
            'channel-5::vc-14-h0510ff6_3',
            'channel-5::openssl-1.0.2o-h8ea7d77_0',
            'channel-5::yaml-0.1.7-hc54c509_2',
            'channel-5::affine-2.1.0-pyh128a3a6_1',
            'channel-5::asn1crypto-0.24.0-py36_0',
            'channel-5::beautifulsoup4-4.6.0-py36hd4cc5e8_1',
            'channel-5::certifi-2018.4.16-py36_0',
            'channel-5::chardet-3.0.4-py36h420ce6e_1',
            'channel-5::colour-0.1.4-pyhd67b51d_0',
            'channel-5::filelock-3.0.4-py36_0',
            'channel-5::glob2-0.6-py36hdf76b57_0',
            'channel-5::idna-2.7-py36_0',
            'channel-5::markupsafe-1.0-py36h0e26971_1',
            'channel-5::pkginfo-1.4.2-py36_1',
            'channel-5::psutil-5.4.6-py36hfa6e2cd_0',
            'channel-5::pycosat-0.6.3-py36h413d8a4_0',
            'channel-5::pycparser-2.18-py36hd053e01_1',
            'channel-5::cffi-1.11.5-py36h945400d_0',
            'channel-5::python-3.6.5-h0c2934d_0',
            'channel-5::pywin32-223-py36hfa6e2cd_1',
            'channel-5::pyyaml-3.12-py36h1d1928f_1',
            'channel-5::ruamel_yaml-0.15.40-py36hfa6e2cd_2',
            'channel-5::six-1.11.0-py36h4db2310_1',
            'channel-5::spiffy-test-app-0.5-pyh6afbcc8_0',
            'channel-5::win_inet_pton-1.0.1-py36he67d7fd_1',
            'channel-5::wincertstore-0.2-py36h7fe50ca_0',
            'channel-5::conda-verify-2.0.0-py36h065de53_0',
            'channel-5::cryptography-2.2.2-py36hfa6e2cd_0',
            'channel-5::menuinst-1.4.14-py36hfa6e2cd_0',
            'channel-5::pysocks-1.6.8-py36_0',
            'channel-5::setuptools-39.2.0-py36_0',
            'channel-5::uses-spiffy-test-app-2.0-pyh18698f2_0',
            'channel-5::jinja2-2.10-py36h292fed1_0',
            'channel-5::pyopenssl-18.0.0-py36_0',
            'channel-5::wheel-0.31.1-py36_0',
            'channel-5::pip-10.0.1-py36_0',
            'channel-5::urllib3-1.23-py36_0',
            'channel-5::requests-2.19.1-py36_0',
            'channel-5::conda-4.5.4-py36_0',
            'channel-5::conda-build-3.10.9-py36_0',
        )
        assert nodes == order

        with env_var('CONDA_ALLOW_CYCLES', 'false', reset_context):
            records, specs = get_windows_conda_build_record_set()
            with pytest.raises(CyclicalDependencyError):
                graph = PrefixGraph(records, specs)


def test_deep_cyclical_dependency():
    # Basically, the whole purpose of this test is to make sure nothing blows up with
    # recursion errors or anything like that.  Cyclical dependencies will always lead to
    # problems, and the tests here document the behavior.

    # "sqlite-3.20.1-haaaaaaa_4.tar.bz2": {
    #   "build": "haaaaaaa_4",
    #   "build_number": 4,
    #   "depends": [
    #     "libedit",
    #     "libgcc-ng >=7.2.0",
    #     "jinja2 2.9.6"
    #   ],
    #   "license": "Public-Domain (http://www.sqlite.org/copyright.html)",
    #   "md5": "deadbeefdd677bc3ed98ddd4deadbeef",
    #   "name": "sqlite",
    #   "sha256": "deadbeefabd915d2f13da177a29e264e59a0ae3c6fd2a31267dcc6a8deadbeef",
    #   "size": 1540584,
    #   "subdir": "linux-64",
    #   "timestamp": 1505666646842,
    #   "version": "3.20.1"
    # },
    graph = PrefixGraph(*get_sqlite_cyclical_record_set())

    nodes = tuple(rec.name for rec in graph.records)
    pprint(nodes)
    order = (
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'tk',
        'xz',
        'zlib',
        'libedit',
        'readline',
        'certifi',
        'click',
        'itsdangerous',
        'markupsafe',
        'python',
        'setuptools',
        'werkzeug',
        'jinja2',
        'flask',
        'sqlite',  # deep cyclical dependency; guess this is what we get
    )
    assert nodes == order
    sqlite_record = next(rec for rec in graph.graph if rec.name == 'sqlite')
    assert sqlite_record.dist_str() == 'channel-4::sqlite-3.20.1-haaaaaaa_4'  # deep cyclical dependency

    # test remove spec
    # because of this deep cyclical dependency, removing jinja2 will remove sqlite and python
    expected_removal = (
        'certifi',
        'click',
        'itsdangerous',
        'markupsafe',
        'python',
        'setuptools',
        'werkzeug',
        'jinja2',
        'flask',
        'sqlite',
    )

    removed_nodes = graph.remove_spec(MatchSpec("sqlite"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_spec(MatchSpec("python"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_spec(MatchSpec("jinja2"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_spec(MatchSpec("markupsafe"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal


    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    expected_removal = (
        'flask',
    )
    assert removed_nodes == expected_removal

    removed_nodes = graph.prune()
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    expected_removal = (
        'click',
        'itsdangerous',
        'werkzeug',
    )
    assert removed_nodes == expected_removal

    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    expected_removal = (
        # None, because of the cyclical dependency?
    )
    assert removed_nodes == expected_removal


    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    markupsafe_node = graph.get_node_by_name('markupsafe')
    markupsafe_ancestors = graph.all_ancestors(markupsafe_node)
    nodes = tuple(rec.name for rec in markupsafe_ancestors)
    pprint(nodes)
    order = (
        'ca-certificates',
        'libgcc-ng',
        'libstdcxx-ng',
        'libffi',
        'ncurses',
        'openssl',
        'tk',
        'xz',
        'zlib',
        'libedit',
        'readline',
        'certifi',
        'markupsafe',
        'python',
        'setuptools',
        'jinja2',
        'sqlite',
    )
    assert nodes == order
    sqlite_record = next(rec for rec in graph.graph if rec.name == 'sqlite')
    assert sqlite_record.dist_str() == 'channel-4::sqlite-3.20.1-haaaaaaa_4'  # extra sanity check

    markupsafe_descendants = graph.all_descendants(markupsafe_node)
    nodes = tuple(rec.name for rec in markupsafe_descendants)
    pprint(nodes)
    order = (
        'certifi',
        'click',
        'itsdangerous',
        'markupsafe',
        'python',
        'setuptools',
        'werkzeug',
        'jinja2',
        'flask',
        'sqlite',
    )
    assert nodes == order
