# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from pprint import pprint

from conda.auxlib.decorators import memoize
from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_var
from conda.exceptions import CyclicalDependencyError
from conda.models.match_spec import MatchSpec
import conda.models.prefix_graph
from conda.models.prefix_graph import PrefixGraph, GeneralGraph
from conda.models.records import PackageRecord
from conda.testing.helpers import add_subdir_to_iter, get_solver_4, get_solver_5

import pytest

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

@memoize
def get_conda_build_record_set(tmpdir):
    specs = MatchSpec("conda"), MatchSpec("conda-build"), MatchSpec("intel-openmp"),
    with get_solver_4(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


@memoize
def get_pandas_record_set(tmpdir):
    specs = MatchSpec("pandas"), MatchSpec("python=2.7"), MatchSpec("numpy 1.13")
    with get_solver_4(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


@memoize
def get_windows_conda_build_record_set(tmpdir):
    specs = (MatchSpec("conda"), MatchSpec("conda-build"), MatchSpec("affine"),
             MatchSpec("colour"), MatchSpec("uses-spiffy-test-app"),)
    with get_solver_5(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


@memoize
def get_sqlite_cyclical_record_set(tmpdir):
    # sqlite-3.20.1-haaaaaaa_4
    specs = MatchSpec("sqlite=3.20.1[build_number=4]"), MatchSpec("flask"),
    with get_solver_4(tmpdir, specs) as solver:
        final_state = solver.solve_final_state()
    return final_state, frozenset(specs)


def test_prefix_graph_1(tmpdir):
    # Basic initial test for public methods of PrefixGraph.

    records, specs = get_conda_build_record_set(tmpdir)
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
        'cryptography-vectors',
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
        'cryptography-vectors',
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
        'cryptography-vectors',
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
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
    )
    assert nodes == order

    spec_matches = add_subdir_to_iter({
        'channel-4::intel-openmp-2018.0.3-0': {'intel-openmp'},
    })
    assert {node.dist_str(): set(str(ms) for ms in specs) for node, specs in graph.spec_matches.items()} == spec_matches

    removed_nodes = graph.prune()
    nodes = tuple(rec.dist_str() for rec in graph.records)
    pprint(nodes)
    order = add_subdir_to_iter((
        'channel-4::intel-openmp-2018.0.3-0',
    ))
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
        'cryptography-vectors',
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
        'setuptools',
        'cryptography',
        'jinja2',
        'pyopenssl',
        'urllib3',
    )
    pprint(removed_nodes)
    assert removed_nodes == order


def test_prefix_graph_2(tmpdir):
    records, specs = get_conda_build_record_set(tmpdir)
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
        'cryptography-vectors',
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
        'cryptography-vectors',
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
        'setuptools',
        'jinja2',
        'conda-build',
    )
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == order


def test_remove_youngest_descendant_nodes_with_specs(tmpdir):
    records, specs = get_conda_build_record_set(tmpdir)
    graph = PrefixGraph(records, tuple(specs) + (MatchSpec("python:requests"),))

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
        'cryptography-vectors',
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
        'cryptography-vectors',
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
        'cryptography-vectors',
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
        'setuptools',
        'jinja2',
    )
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == order


def test_windows_sort_orders_1(tmpdir):
    # This test makes sure the windows-specific parts of _toposort_prepare_graph
    # are behaving correctly.

    old_on_win = conda.models.prefix_graph.on_win
    conda.models.prefix_graph.on_win = True
    try:
        records, specs = get_windows_conda_build_record_set(tmpdir)
        graph = PrefixGraph(records, specs)

        nodes = tuple(rec.name for rec in graph.records)
        pprint(nodes)
        order = (
            'ca-certificates',
            'conda-env',
            'vs2015_runtime',
            'vc',
            'openssl',
            'python',
            'yaml',
            'pywin32',
            'menuinst',  # on_win, menuinst should be very early
            'affine',
            'asn1crypto',
            'beautifulsoup4',
            'certifi',
            'chardet',
            'colour',
            'cryptography-vectors',
            'filelock',
            'glob2',
            'idna',
            'markupsafe',
            'pkginfo',
            'psutil',
            'pycosat',
            'pycparser',
            'pyyaml',
            'ruamel_yaml',
            'six',
            'win_inet_pton',
            'wincertstore',
            'cffi',
            'pysocks',
            'setuptools',
            'cryptography',
            'jinja2',
            'wheel',
            'pip',  # pip always comes after python
            'pyopenssl',
            'urllib3',
            'requests',
            'conda',  # on_win, conda comes before all noarch: python packages (affine, colour, spiffy-test-app, uses-spiffy-test-app)
            'conda-build',
            'spiffy-test-app',
            'uses-spiffy-test-app',
        )
        assert nodes == order
    finally:
        conda.models.prefix_graph.on_win = old_on_win


def test_windows_sort_orders_2(tmpdir):
    # This test makes sure the windows-specific parts of _toposort_prepare_graph
    # are behaving correctly.

    with env_var('CONDA_ALLOW_CYCLES', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        old_on_win = conda.models.prefix_graph.on_win
        conda.models.prefix_graph.on_win = False
        try:
            records, specs = get_windows_conda_build_record_set(tmpdir)
            graph = PrefixGraph(records, specs)

            python_node = graph.get_node_by_name('python')
            pip_node = graph.get_node_by_name('pip')
            assert pip_node in graph.graph[python_node]
            assert python_node in graph.graph[pip_node]

            nodes = tuple(rec.name for rec in graph.records)
            pprint(nodes)
            order = (
                'ca-certificates',
                'conda-env',
                'vs2015_runtime',
                'vc',
                'openssl',
                'python',
                'yaml',
                'affine',
                'asn1crypto',
                'beautifulsoup4',
                'certifi',
                'chardet',
                'colour',
                'cryptography-vectors',
                'filelock',
                'glob2',
                'idna',
                'markupsafe',
                'pkginfo',
                'psutil',
                'pycosat',
                'pycparser',
                'pywin32',
                'pyyaml',
                'ruamel_yaml',
                'six',
                'spiffy-test-app',
                'win_inet_pton',
                'wincertstore',
                'cffi',
                'menuinst',  # not on_win, menuinst isn't changed
                'pysocks',
                'setuptools',
                'uses-spiffy-test-app',
                'cryptography',
                'jinja2',
                'wheel',
                'pip',  # pip always comes after python
                'pyopenssl',
                'urllib3',
                'requests',
                'conda',  # not on_win, no special treatment for noarch: python packages (affine, colour, spiffy-test-app, uses-spiffy-test-app)
                'conda-build',
            )
            assert nodes == order
        finally:
            conda.models.prefix_graph.on_win = old_on_win


def test_sort_without_prep(tmpdir):
    # Test the _toposort_prepare_graph method, here by not running it at all.
    # The method is invoked in every other test.  This is what happens when it's not invoked.

    with patch.object(conda.models.prefix_graph.PrefixGraph, '_toposort_prepare_graph', return_value=None):
        records, specs = get_windows_conda_build_record_set(tmpdir)
        graph = PrefixGraph(records, specs)

        python_node = graph.get_node_by_name('python')
        pip_node = graph.get_node_by_name('pip')
        assert pip_node in graph.graph[python_node]
        assert python_node in graph.graph[pip_node]

        nodes = tuple(rec.name for rec in graph.records)
        pprint(nodes)
        order = (
            'ca-certificates',
            'conda-env',
            'vs2015_runtime',
            'vc',
            'openssl',
            'yaml',
            'affine',
            'asn1crypto',
            'beautifulsoup4',
            'certifi',
            'chardet',
            'colour',
            'cryptography-vectors',
            'filelock',
            'glob2',
            'idna',
            'markupsafe',
            'pkginfo',
            'psutil',
            'pycosat',
            'pycparser',
            'cffi',
            'python',
            'pywin32',
            'pyyaml',
            'ruamel_yaml',
            'six',
            'spiffy-test-app',
            'win_inet_pton',
            'wincertstore',
            'cryptography',
            'menuinst',
            'pysocks',
            'setuptools',
            'uses-spiffy-test-app',
            'jinja2',
            'pyopenssl',
            'wheel',
            'pip',
            'urllib3',
            'requests',
            'conda',
            'conda-build',
        )
        assert nodes == order

        with env_var('CONDA_ALLOW_CYCLES', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            records, specs = get_windows_conda_build_record_set(tmpdir)
            with pytest.raises(CyclicalDependencyError):
                graph = PrefixGraph(records, specs)


def test_deep_cyclical_dependency(tmpdir):
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
    graph = PrefixGraph(*get_sqlite_cyclical_record_set(tmpdir))

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

    graph = PrefixGraph(*get_sqlite_cyclical_record_set(tmpdir))
    removed_nodes = graph.remove_spec(MatchSpec("python"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set(tmpdir))
    removed_nodes = graph.remove_spec(MatchSpec("jinja2"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal

    graph = PrefixGraph(*get_sqlite_cyclical_record_set(tmpdir))
    removed_nodes = graph.remove_spec(MatchSpec("markupsafe"))
    removed_nodes = tuple(rec.name for rec in removed_nodes)
    pprint(removed_nodes)
    assert removed_nodes == expected_removal


    graph = PrefixGraph(*get_sqlite_cyclical_record_set(tmpdir))
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


    graph = PrefixGraph(*get_sqlite_cyclical_record_set(tmpdir))
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


def test_general_graph_bfs_simple():
    a = PackageRecord(name="a", version="1", build="0", build_number=0, depends=["b", "c", "d"])
    b = PackageRecord(name="b", version="1", build="0", build_number=0, depends=["e"])
    c = PackageRecord(name="c", version="1", build="0", build_number=0)
    d = PackageRecord(name="d", version="1", build="0", build_number=0, depends=["f", "g"])
    e = PackageRecord(name="e", version="1", build="0", build_number=0)
    f = PackageRecord(name="f", version="1", build="0", build_number=0)
    g = PackageRecord(name="g", version="1", build="0", build_number=0)
    records = [a, b, c, d, e, f, g]
    graph = GeneralGraph(records)

    a_to_c = graph.breadth_first_search_by_name(MatchSpec("a"), MatchSpec("c"))
    assert a_to_c == [MatchSpec("a"), MatchSpec("c")]

    a_to_f = graph.breadth_first_search_by_name(MatchSpec("a"), MatchSpec("f"))
    assert a_to_f == [MatchSpec("a"), MatchSpec("d"), MatchSpec("f")]

    a_to_a = graph.breadth_first_search_by_name(MatchSpec("a"), MatchSpec("a"))
    assert a_to_a == [MatchSpec("a")]

    a_to_not_exist = graph.breadth_first_search_by_name(MatchSpec("a"), MatchSpec("z"))
    assert a_to_not_exist is None

    backwards = graph.breadth_first_search_by_name(MatchSpec("d"), MatchSpec("a"))
    assert backwards is None


def test_general_graph_bfs_version():
    a = PackageRecord(name="a", version="1", build="0", build_number=0, depends=["b", "c", "d"])
    b = PackageRecord(name="b", version="1", build="0", build_number=0, depends=["e"])
    c = PackageRecord(name="c", version="1", build="0", build_number=0, depends=["g=1"])
    d = PackageRecord(name="d", version="1", build="0", build_number=0, depends=["f", "g=2"])
    e = PackageRecord(name="e", version="1", build="0", build_number=0)
    f = PackageRecord(name="f", version="1", build="0", build_number=0)
    g1 = PackageRecord(name="g", version="1", build="0", build_number=0)
    g2 = PackageRecord(name="g", version="2", build="0", build_number=0)
    records = [a, b, c, d, e, f, g1, g2]
    graph = GeneralGraph(records)

    a_to_g1 = graph.breadth_first_search_by_name(MatchSpec("a"), MatchSpec("g=1"))
    assert a_to_g1 == [MatchSpec("a"), MatchSpec("c"), MatchSpec("g=1")]

    a_to_g2 = graph.breadth_first_search_by_name(MatchSpec("a"), MatchSpec("g=2"))
    assert a_to_g2 == [MatchSpec("a"), MatchSpec("d"), MatchSpec("g=2")]
