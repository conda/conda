# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

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

    nodes = tuple(rec.dist_str() for rec in graph.records)
    print(nodes)
    order = (
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8',
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
        'channel-4::conda-4.4.10-py36_0',
        'channel-4::conda-build-3.5.1-py36_0',
    )
    assert nodes == order

    python_node = graph.get_node_by_name('python')
    python_ancestors = graph.all_ancestors(python_node)
    nodes = tuple(rec.dist_str() for rec in python_ancestors)
    print(nodes)
    order = (
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
    )
    assert nodes == order

    python_descendants = graph.all_descendants(python_node)
    nodes = tuple(rec.dist_str() for rec in python_descendants)
    print(nodes)
    order = (
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
        'channel-4::conda-4.4.10-py36_0',
        'channel-4::conda-build-3.5.1-py36_0',
    )
    assert nodes == order

    # test remove_specs
    removed_nodes = graph.remove_spec(MatchSpec("requests"))
    nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(nodes)
    order = (
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
        'channel-4::conda-4.4.10-py36_0',
        'channel-4::conda-build-3.5.1-py36_0',
    )
    assert nodes == order

    nodes = tuple(rec.dist_str() for rec in graph.records)
    print(nodes)
    order = (
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8',
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
    )
    assert nodes == order

    spec_matches = {
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8': {'intel-openmp'},
    }
    assert {node.dist_str(): set(str(ms) for ms in specs) for node, specs in graph.spec_matches.items()} == spec_matches

    removed_nodes = graph.prune()
    nodes = tuple(rec.dist_str() for rec in graph.records)
    print(nodes)
    order = (
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8',
    )
    assert nodes == order

    order = (
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
    )
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == order


def test_prefix_graph_2():
    records, specs = get_conda_build_record_set()
    graph = PrefixGraph(records, specs)

    conda_build_node = graph.get_node_by_name('conda-build')
    del graph.spec_matches[conda_build_node]

    nodes = tuple(rec.dist_str() for rec in graph.records)
    print(nodes)
    order = (
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8',
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
        'channel-4::conda-4.4.10-py36_0',
        'channel-4::conda-build-3.5.1-py36_0',
    )
    assert nodes == order

    removed_nodes = graph.prune()
    remaining_nodes = tuple(rec.dist_str() for rec in graph.records)
    print(remaining_nodes)
    order = (
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8',
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
        'channel-4::conda-4.4.10-py36_0',
    )
    assert remaining_nodes == order

    order = (
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::conda-build-3.5.1-py36_0',
    )
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == order


def test_remove_youngest_descendant_nodes_with_specs():
    records, specs = get_conda_build_record_set()
    graph = PrefixGraph(records, tuple(specs) + (MatchSpec("requests"),))

    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()

    remaining_nodes = tuple(rec.dist_str() for rec in graph.records)
    print(remaining_nodes)
    order = (
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
        'channel-4::conda-4.4.10-py36_0',
    )
    assert remaining_nodes == order

    order = (
        'channel-4::intel-openmp-2018.0.0-hc7b2577_8',
        'channel-4::conda-build-3.5.1-py36_0',
    )
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == order

    # again
    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()

    remaining_nodes = tuple(rec.dist_str() for rec in graph.records)
    print(remaining_nodes)
    order = (
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
    )
    assert remaining_nodes == order

    order = (
        'channel-4::conda-4.4.10-py36_0',
    )
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == order

    # now test prune
    removed_nodes = graph.prune()

    remaining_nodes = tuple(rec.dist_str() for rec in graph.records)
    print(remaining_nodes)
    order = (
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::sqlite-3.22.0-h1bed415_0',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::asn1crypto-0.24.0-py36_0',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::chardet-3.0.4-py36h0f667ec_1',
        'channel-4::idna-2.6-py36h82fb2a8_1',
        'channel-4::pycparser-2.18-py36hf9f622e_1',
        'channel-4::pysocks-1.6.7-py36hd97a5b1_1',
        'channel-4::six-1.11.0-py36h372c433_1',
        'channel-4::cffi-1.11.4-py36h9745a5d_0',
        'channel-4::cryptography-2.1.4-py36hd09be54_0',
        'channel-4::pyopenssl-17.5.0-py36h20ba746_0',
        'channel-4::urllib3-1.22-py36hbe7ace6_0',
        'channel-4::requests-2.18.4-py36he2e5f8d_1',
    )
    assert remaining_nodes == order

    order = (
        'channel-4::conda-env-2.6.0-h36134e3_1',
        'channel-4::patchelf-0.9-hf79760b_2',
        'channel-4::yaml-0.1.7-had09818_2',
        'channel-4::beautifulsoup4-4.6.0-py36h49b8c8c_1',
        'channel-4::filelock-3.0.4-py36_0',
        'channel-4::glob2-0.6-py36he249c77_0',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::pkginfo-1.4.1-py36h215d178_1',
        'channel-4::psutil-5.4.3-py36h14c3975_0',
        'channel-4::pycosat-0.6.3-py36h0a5515d_0',
        'channel-4::pyyaml-3.12-py36hafb9ca4_1',
        'channel-4::ruamel_yaml-0.15.35-py36h14c3975_1',
        'channel-4::conda-verify-2.0.0-py36h98955d8_0',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::jinja2-2.10-py36ha16c418_0',
    )
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
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

    nodes = tuple(rec.dist_str() for rec in graph.records)
    print(nodes)
    order = (
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::click-6.7-py36h5253387_0',
        'channel-4::itsdangerous-0.24-py36h93cc618_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::werkzeug-0.14.1-py36_0',
        'channel-4::jinja2-2.9.6-py36h489bce4_1',
        'channel-4::flask-0.12.2-py36hb24657c_0',
        'channel-4::sqlite-3.20.1-haaaaaaa_4',  # deep cyclical dependency; guess this is what we get
    )
    assert nodes == order

    # test remove spec
    # because of this deep cyclical dependency, removing jinja2 will remove sqlite and python
    expected_removal = (
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::click-6.7-py36h5253387_0',
        'channel-4::itsdangerous-0.24-py36h93cc618_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::werkzeug-0.14.1-py36_0',
        'channel-4::jinja2-2.9.6-py36h489bce4_1',
        'channel-4::flask-0.12.2-py36hb24657c_0',
        'channel-4::sqlite-3.20.1-haaaaaaa_4',
    )

    removed_nodes = graph.remove_spec(MatchSpec("sqlite"))
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_spec(MatchSpec("python"))
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_spec(MatchSpec("jinja2"))
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_spec(MatchSpec("markupsafe"))
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    assert removed_nodes == expected_removal


    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    expected_removal = (
        'channel-4::flask-0.12.2-py36hb24657c_0',
    )
    assert removed_nodes == expected_removal

    removed_nodes = graph.prune()
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    expected_removal = (
        'channel-4::click-6.7-py36h5253387_0',
        'channel-4::itsdangerous-0.24-py36h93cc618_1',
        'channel-4::werkzeug-0.14.1-py36_0',
    )
    assert removed_nodes == expected_removal

    removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
    removed_nodes = tuple(rec.dist_str() for rec in removed_nodes)
    print(removed_nodes)
    expected_removal = (
        # None, because of the cyclical dependency?
    )
    assert removed_nodes == expected_removal


    graph = PrefixGraph(*get_sqlite_cyclical_record_set())
    markupsafe_node = graph.get_node_by_name('markupsafe')
    markupsafe_ancestors = graph.all_ancestors(markupsafe_node)
    nodes = tuple(rec.dist_str() for rec in markupsafe_ancestors)
    print(nodes)
    order = (
        'channel-4::ca-certificates-2017.08.26-h1d4fec5_0',
        'channel-4::libgcc-ng-7.2.0-h7cc24e2_2',
        'channel-4::libstdcxx-ng-7.2.0-h7a57d05_2',
        'channel-4::libffi-3.2.1-hd88cf55_4',
        'channel-4::ncurses-6.0-h9df7e31_2',
        'channel-4::openssl-1.0.2n-hb7f436b_0',
        'channel-4::tk-8.6.7-hc745277_3',
        'channel-4::xz-5.2.3-h55aa19d_2',
        'channel-4::zlib-1.2.11-ha838bed_2',
        'channel-4::libedit-3.1-heed3624_0',
        'channel-4::readline-7.0-ha6073c6_4',
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::jinja2-2.9.6-py36h489bce4_1',
        'channel-4::sqlite-3.20.1-haaaaaaa_4',
    )
    assert nodes == order

    markupsafe_descendants = graph.all_descendants(markupsafe_node)
    nodes = tuple(rec.dist_str() for rec in markupsafe_descendants)
    print(nodes)
    order = (
        'channel-4::certifi-2018.1.18-py36_0',
        'channel-4::click-6.7-py36h5253387_0',
        'channel-4::itsdangerous-0.24-py36h93cc618_1',
        'channel-4::markupsafe-1.0-py36hd9260cd_1',
        'channel-4::python-3.6.4-hc3d631a_1',
        'channel-4::setuptools-38.5.1-py36_0',
        'channel-4::werkzeug-0.14.1-py36_0',
        'channel-4::jinja2-2.9.6-py36h489bce4_1',
        'channel-4::flask-0.12.2-py36hb24657c_0',
        'channel-4::sqlite-3.20.1-haaaaaaa_4',
    )
    assert nodes == order
