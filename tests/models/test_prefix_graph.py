# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

from conda._vendor.auxlib.decorators import memoize
from conda.models.match_spec import MatchSpec
from conda.models.prefix_graph import PrefixGraph
from conda.resolve import dashlist
from tests.core.test_solve import get_solver_4

log = getLogger(__name__)


@memoize
def get_conda_build_record_set():
    specs = MatchSpec("conda"), MatchSpec("conda-build"), MatchSpec("intel-openmp"),
    with get_solver_4(specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


def get_pandas_record_set():
    specs = MatchSpec("pandas"), MatchSpec("python=2.7"), MatchSpec("numpy 1.13")
    with get_solver_4(specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


def test_prefix_graph_1():
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
