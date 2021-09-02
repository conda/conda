# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test for python distribution information and metadata handling."""
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
from errno import ENOENT
import os
from os.path import basename, lexists
from pprint import pprint
import tempfile

from conda.common.compat import odict
from conda.common.path import get_python_site_packages_short_path
from conda.common.pkg_formats.python import (
    MetadataWarning, PySpec, PythonDistribution, PythonDistributionMetadata,
    PythonEggInfoDistribution, PythonInstalledDistribution, get_default_marker_context,
    get_dist_file_from_egg_link, get_site_packages_anchor_files, interpret, norm_package_name,
    norm_package_version, parse_specification, pypi_name_to_conda_name, split_spec,
)
from conda.common.url import join_url
import pytest
from tests.data.env_metadata import METADATA_VERSION_PATHS


# Helpers
# -----------------------------------------------------------------------------
def _create_test_files(test_files):
    """
    Helper method to create files in a folder with fname and given content.

    test_files = (
        ('folder', 'fname', 'content'),  # Create a file in folder with content
        ('', 'fname', 'content'),        # Create a file with content
        ('folder', '', ''),              # Create a folder
    )
    """
    temp_path = tempfile.mkdtemp()
    fpaths = []
    for folder, fname, content in test_files:
        fpath = os.path.join(temp_path, folder, fname)
        try:
            os.makedirs(os.path.dirname(fpath))
        except Exception:
            pass

        with open(fpath, 'w') as fh:
            fh.write(content)
        fpaths.append(fpath)
    return temp_path, fpaths


def _print_output(*args):
    """Helper function to print output in case of failed tests."""
    for arg in args:
        print(arg)
    print('\n')


# Test module helper functions
# -----------------------------------------------------------------------------
def test_norm_package_name():
    test_names = (
        (None, ''),
        ('', ''),
        ('pyOpenssl', 'pyopenssl'),
        ('py.Openssl', 'py-openssl'),
        ('py-Openssl', 'py-openssl'),
        ('py_Openssl', 'py-openssl'),
        ('zope.interface', 'zope-interface'),
    )
    for (name, expected_name) in test_names:
        parsed_name = norm_package_name(name)
        _print_output(name, parsed_name, expected_name)
        assert parsed_name == expected_name


def test_pypi_name_to_conda_name():
    test_cases = (
        (None, ''),
        ('', ''),
        ('graphviz', 'python-graphviz'),
    )
    for (name, expected_name) in test_cases:
        parsed_name = pypi_name_to_conda_name(name)
        _print_output(name, parsed_name, expected_name)
        assert parsed_name == expected_name


def test_norm_package_version():
    test_cases = (
        (None, ''),
        ('', ''),
        ('>=2', '>=2'),
        ('(>=2)', '>=2'),
        (' (>=2) ', '>=2'),
        ('>=2,<3', '>=2,<3'),
        ('>=2, <3', '>=2,<3'),
        (' (>=2, <3) ', '>=2,<3'),
    )
    for (version, expected_version) in test_cases:
        parsed_version = norm_package_version(version)
        _print_output(version, parsed_version, expected_version)
        assert parsed_version == expected_version


def test_split_spec():
    test_cases = (
        # spec, separator, (spec_start, spec_end)
        ('', ';', ('', '')),
        ('start;end', ';', ('start', 'end')),
        ('start ; end', ';', ('start', 'end')),
        (' start ; end ', ';', ('start', 'end')),
        ('start@end', '@', ('start', 'end')),
        ('start @ end', '@', ('start', 'end')),
        (' start @ end ', '@', ('start', 'end')),
    )
    for spec, sep, expected_output in test_cases:
        output = split_spec(spec, sep)
        _print_output(spec, output, expected_output)
        assert output == expected_output


def test_parse_specification():
    test_reqs = {
        '':
            PySpec('', [], '', '', ''),
        'requests':
            PySpec('requests', [], '', '', ''),
        'requests >1.1':
            PySpec('requests', [], '>1.1', '', ''),
        'requests[security]':
            PySpec('requests', ['security'], '', '', ''),
        'requests[security] (>=1.1.0)':
            PySpec('requests', ['security'], '>=1.1.0', '', ''),
        'requests[security]>=1.5.0':
            PySpec('requests', ['security'], '>=1.5.0', '', ''),
        'requests[security] (>=4.5.0) ; something >= 27':
            PySpec('requests', ['security'], '>=4.5.0', 'something >= 27', ''),
        'requests[security]>=3.3.0;something >= 2.7 ':
            PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7', ''),
        'requests[security]>=3.3.0;something >= 2.7 or something_else == 1':
            PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7 or something_else == 1', ''),
        'requests[security] >=3.3.0 ; something >= 2.7 or something_else == 1':
            PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7 or something_else == 1', ''),
        'requests[security] (>=3.3.0) ; something >= 2.7 or something_else == 1':
            PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7 or something_else == 1', ''),
        'requests[security] (>=3.3.0<4.4) ; something >= 2.7 or something_else == 1':
            PySpec('requests', ['security'], '>=3.3.0<4.4', 'something >= 2.7 or something_else == 1', ''),
        'pyOpenSSL>=0.14':
            PySpec('pyopenssl', [], '>=0.14', '', ''),
        'py.OpenSSL>=0.14':
            PySpec('py-openssl', [], '>=0.14', '', ''),
        'py-OpenSSL>=0.14':
            PySpec('py-openssl', [], '>=0.14', '', ''),
        'py_OpenSSL>=0.14':
            PySpec('py-openssl', [], '>=0.14', '', ''),
        'zope.interface (>3.5.0)':
            PySpec('zope-interface', [], '>3.5.0', '', ''),
        "A":
            PySpec('a', [], '', '', ''),
        "A.B-C_D":
            PySpec('a-b-c-d', [], '', '', ''),
        "aa":
            PySpec('aa', [], '', '', ''),
        "name":
            PySpec('name', [], '', '', ''),
        "name<=1":
            PySpec('name', [], '<=1', '', ''),
        "name>=3":
            PySpec('name', [], '>=3', '', ''),
        "name>=3,<2":
            PySpec('name', [], '>=3,<2', '', ''),
        " name ( >= 3,  < 2 ) ":
            PySpec('name', [], '>=3,<2', '', ''),
        "name@http://foo.com":
            PySpec('name', [], '', '', 'http://foo.com'),
        " name [ fred , bar ] ( >= 3 , < 2 ) ":
            PySpec('name', ['fred', 'bar'], '>=3,<2', '', ''),
        " name [fred,bar] ( >= 3 , < 2 )  @  http://foo.com ; python_version=='2.7' ":
            PySpec('name', ['fred', 'bar'], '>=3,<2', "python_version=='2.7'", 'http://foo.com'),
        " name [fred,bar] @ http://foo.com ; python_version=='2.7' ":
            PySpec('name', ['fred', 'bar'], '', "python_version=='2.7'", 'http://foo.com'),
        "name[quux, strange];python_version<'2.7' and platform_version=='2'":
            PySpec('name', ['quux', 'strange'], '', "python_version<'2.7' and platform_version=='2'", ''),
        "name; os_name=='a' or os_name=='b'":
            PySpec('name', [], '', "os_name=='a' or os_name=='b'", ''),
        "name; os_name=='a' and os_name=='b' or os_name=='c'":
            PySpec('name', [], '', "os_name=='a' and os_name=='b' or os_name=='c'", ''),
        "name; os_name=='a' and (os_name=='b' or os_name=='c')":
            PySpec('name', [], '', "os_name=='a' and (os_name=='b' or os_name=='c')", ''),
        " name; os_name=='a' or os_name=='b' and os_name=='c' ":
            PySpec('name', [], '', "os_name=='a' or os_name=='b' and os_name=='c'", ''),
        " name ; (os_name=='a' or os_name=='b') and os_name=='c' ":
            PySpec('name', [], '', "(os_name=='a' or os_name=='b') and os_name=='c'", ''),
        '>=3,<2':
            PySpec('', [], '>=3,<2', '', ''),
        ' ( >=3 , <2 ) ':
            PySpec('', [], '>=3,<2', '', ''),
        '>=2.7,!=3.0.*,!=3.1.*,!=3.2.*':
            PySpec('', [], '>=2.7,!=3.0.*,!=3.1.*,!=3.2.*', '', ''),
        'name>=1.0.0-beta.1,<2.0.0':
            PySpec('name', [], '>=1.0.0.beta.1,<2.0.0', '', ''),
        'name==1.0.0+localhash':
            PySpec('name', [], '==1.0.0+localhash', '', ''),
    }
    for req, expected_req in test_reqs.items():
        parsed_req = parse_specification(req)
        _print_output(req, parsed_req, expected_req)
        assert parsed_req == expected_req


def test_get_site_packages_anchor_files():
    test_cases_valid = (
        # dir, filename, content
        ('bar.dist-info', 'RECORD', ''),
        ('foo.egg-info', 'PKG-INFO', ''),
        ('', 'cheese.egg-info', ''),
        ('', 'spam.egg-link', ''),
    )
    test_cases_invalid = (
        ('a.eggs', 'RECORD', ''),
        ('b.eggs', 'PKG-INFO', ''),
        ('', 'zoom.path', ''),
        ('', 'zoom.pth', ''),
        ('', 'something', ''),
    )

    # Create test case dirs/files on temp folder
    temp_path, fpaths = _create_test_files(test_cases_valid + test_cases_invalid)
    ref_dir = os.path.basename(temp_path)

    outputs = get_site_packages_anchor_files(temp_path, ref_dir)

    # Generate valid output
    expected_outputs = set()
    for folder, fname, content in test_cases_valid:
        expected_output = '/'.join([ref_dir, folder, fname]).replace('//', '/')
        expected_outputs.add(expected_output)

    _print_output(outputs, expected_outputs)
    assert sorted(outputs) == sorted(expected_outputs)


def test_get_dist_file_from_egg_link():
    test_files = (
        ('egg1.egg-info', 'PKG-INFO', ''),
    )
    temp_path, fpaths = _create_test_files(test_files)
    temp_path2, fpaths2 = _create_test_files((('', 'egg1.egg-link', temp_path),))

    output = get_dist_file_from_egg_link(fpaths2[0], '')
    expected_output = fpaths[0]
    _print_output(output, expected_output)
    assert output == expected_output

    # Test not existing path
    temp_path3, fpaths3 = _create_test_files((('', 'egg2.egg-link', '/not-a-path/'),))
    with pytest.raises(EnvironmentError) as exc:
        get_dist_file_from_egg_link(fpaths3[0], '')
    print(exc.value)

    # Test existing path but no valig egg-info files
    temp_path4 = tempfile.mkdtemp()
    temp_path4, fpaths4 = _create_test_files((('', 'egg2.egg-link', temp_path4),))
    with pytest.raises(EnvironmentError) as exc:
        get_dist_file_from_egg_link(fpaths4[0], '')
    print(exc.value)


@pytest.mark.skipif(True, reason="Ask @goanpeca about what this test is looking for.")
def test_get_python_distribution_info():
    temp_path_egg1, _ = _create_test_files((
        ('', 'bar.egg-info', 'Name: bar\n'),
    ))
    temp_path_egg2, _ = _create_test_files((
        ('lee.egg-info', 'PKG-INFO', 'Name: lee\n'),
    ))
    test_files = (
        # Egg link
        ('', 'boom.egg-link', '/not-a-path/'),
        ('', 'bar.egg-link', temp_path_egg1),
        ('', 'lee.egg-link', temp_path_egg2),
        # Dist info
        ('spam.dist-info', 'METADATA', 'Name: spam\n'),
        ('spam.dist-info', 'RECORD', ''),
        ('spam.dist-info', 'INSTALLER', ''),
        # Egg info
        ('foo.egg-info', 'METADATA', 'Name: foo\n'),
        # Direct file
        ('', 'cheese.egg-info', 'Name: cheese\n'),
    )
    temp_path2, fpaths = _create_test_files(test_files)
    output_names = ['boom', 'bar', 'lee', 'spam', 'spam', 'spam', 'foo', 'cheese']
    for i, fpath in enumerate(fpaths):
        output = PythonDistribution.init(temp_path2, basename(fpath), "1.1")
        output = output.prefix_record
        pprint(output.dump())
        if output:
            assert output.name == output_names[i]
            assert output.name == output_names[i]
        else:
            assert output is None


# Metadata
# -----------------------------------------------------------------------------
def test_metadata_keys():
    cls = PythonDistributionMetadata
    for keymap in cls.SINGLE_USE_KEYS, cls.MULTIPLE_USE_KEYS:
        for key, value in keymap.items():
            assert key.lower().replace('-', '_') == value


def test_metadata_process_path():
    name = 'META'
    test_files = (
        ('', name, 'Name: eggs\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)
    func = PythonDistributionMetadata._process_path

    # Test valid directory
    output = func(temp_path, [name])
    expected_output = fpaths[0]
    _print_output(output, expected_output)
    assert output == expected_output

    # Test valid directory (empty files)
    output = func(temp_path, [])
    expected_output = None
    _print_output(output, expected_output)
    assert output == expected_output

    # Test valid directory (file order)
    output = func(temp_path, ['something', name, 'something-else'])
    expected_output = fpaths[0]
    _print_output(output, expected_output)
    assert output == expected_output

    # Test valid file
    output = func(fpaths[0], [name])
    expected_output = fpaths[0]
    _print_output(output, expected_output)
    assert output == expected_output


def test_metadata_read_metadata():
    func = PythonDistributionMetadata._read_metadata

    # Test existing file unknown key
    temp_path, fpaths = _create_test_files((
        ('', 'PKG-INFO', 'Unknown-Key: unknown\n'),
    ))
    output = func(fpaths[0])
    expected_output = odict()
    _print_output(output, expected_output)
    assert output == expected_output

    # Test existing file known key
    temp_path, fpaths = _create_test_files((
        ('', 'PKG-INFO', 'Name: spam\n'),
    ))
    output = func(fpaths[0])
    expected_output = odict(name='spam')
    _print_output(output, expected_output)
    assert output == expected_output

    # Test non existing file
    test_fpath = '/foo/bar/METADATA'
    output = func(test_fpath)
    expected_output = odict()
    _print_output(output, expected_output)
    assert output == expected_output


def test_metadata():
    # Check warnings are raised for None path
    with pytest.warns(MetadataWarning):
        path = PythonDistributionMetadata._process_path(None, [])
    assert path is None

    # Check versions
    for fpath in METADATA_VERSION_PATHS:
        if not lexists(fpath):
            pytest.skip("test files not found: %s" % fpath)
        meta = PythonDistributionMetadata(fpath)
        a = meta.get_dist_requirements()
        b = meta.get_python_requirements()
        z = meta.get_external_requirements()
        c = meta.get_extra_provides()
        d = meta.get_dist_provides()
        e = meta.get_dist_obsolete()
        f = meta.get_classifiers()
        name = meta.name
        version = meta.version
        _print_output(fpath, meta._data, a, b, c, d, e, f, name, version)
        assert len(meta._data)
        assert name == 'BeagleVote'
        assert version == '1.0a2'


# Python Distributions
# -----------------------------------------------------------------------------
def test_basepydist_parse_requires_file_data():
    key = 'g'
    test_cases = (
        # (data, requirements, extras)
        ('', ([], [])),
        ('foo\n', (['foo'], [])),
        ('foo\n\n[:a == "a"]\nbar\n', (['foo', 'bar; a == "a"'], ['a'])),
        ('foo\n\n[a]\nbar\n', (['foo', 'bar; extra == "a"'], ['a'])),
    )
    func = PythonDistribution._parse_requires_file_data

    for data, (expected_reqs, expected_extras) in test_cases:
        output_reqs, output_extras = func(data, key)
        _print_output(repr(data), output_reqs, frozenset(expected_reqs))
        assert sorted(list(output_reqs)) == sorted(list(expected_reqs))


def test_basepydist_parse_entries_file_data():
    func = PythonDistribution._parse_entries_file_data
    data = '''
[a]
a = cli:main_1

[b.c]
b = cli:MAIN_2

[b.d]
C = cli:MAIN_3
'''
    expected_output = odict()
    expected_output['a'] = odict([('a', 'cli:main_1')])
    expected_output['b.c'] = odict([('b', 'cli:MAIN_2')])
    expected_output['b.d'] = odict([('C', 'cli:MAIN_3')])
    output = func(data)

    _print_output(output, expected_output)
    assert output == expected_output


def test_basepydist_load_requires_provides_file():
    temp_path, fpaths = _create_test_files((('', 'depends.txt', 'foo\n\n[a]\nbar\n'), ))

    dist = PythonEggInfoDistribution(temp_path, "1.8", None)
    exp_req, exp_extra = (['foo', 'bar; extra == "a"'], ['a'])
    req, extra = dist._load_requires_provides_file()
    _print_output((list(sorted(req)), extra), (list(sorted(exp_req)), exp_extra))
    assert (list(sorted(req)), extra) == (list(sorted(exp_req)), exp_extra)


def test_dist_get_paths():
    content = 'foo/bar,sha256=1,"45"\nfoo/spam,,\n'
    temp_path, fpaths = _create_test_files((('', 'SOURCES.txt', content), ))

    sp_dir = get_python_site_packages_short_path("2.7")

    dist = PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist.get_paths()
    expected_output = [(join_url(sp_dir, "foo", "bar"), '1', 45),
                       (join_url(sp_dir, "foo", "spam"), None, None)]
    _print_output(output, expected_output)
    assert output == expected_output


def test_dist_get_paths_no_paths():
    temp_path = tempfile.mkdtemp()
    dist = PythonEggInfoDistribution(temp_path, "2.7", None)
    with pytest.raises(EnvironmentError):
        paths = dist.get_paths()


def test_get_dist_requirements():
    test_files = (
        ('', 'METADATA', 'Name: spam\n'),
        ('', 'requires.txt', 'foo >1.0'),
    )
    temp_path, fpaths = _create_test_files(test_files)

    dist = PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist.get_dist_requirements()
    expected_output = frozenset({'foo >1.0'})
    _print_output(output, expected_output)
    assert output == expected_output


def test_get_extra_provides():
    test_files = (
        ('', 'METADATA', 'Name: spam\n'),
        ('', 'requires.txt', 'foo >1.0\n[a]\nbar\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)

    dist = PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist.get_extra_provides()
    expected_output = ['a']
    _print_output(output, expected_output)
    assert output == expected_output


def test_get_entry_points():
    test_files = (
        ('', 'METADATA', 'Name: spam\n'),
        ('', 'entry_points.txt', '[console_scripts]\ncheese = cli:main\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)

    dist = PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist.get_entry_points()
    expected_output = odict(console_scripts=odict(cheese='cli:main'))
    _print_output(output, expected_output)
    assert output == expected_output


def test_pydist_check_files():
    test_files = (
        ('', 'METADATA', '1'),
        ('', 'RECORD', '2'),
        ('', 'INSTALLER', '3'),
    )

    # Test mandatory files found
    temp_path, fpaths = _create_test_files(test_files)
    PythonInstalledDistribution(temp_path, "2.7", None)

    # Test mandatory file not found
    os.remove(fpaths[0])
    with pytest.raises(EnvironmentError) as exc:
        PythonInstalledDistribution(temp_path, "2.7", None)
    assert exc.value.errno == ENOENT


def test_python_dist_info():
    test_files = (
        ('', 'METADATA', ('Name: zoom\n'
                          'Requires-Python: ==2.7\n'
                          'Requires-External: C\n'
                          )
         ),
        ('', 'RECORD', 'foo/bar,sha256=1,"45"\nfoo/spam,,\n'),
        ('', 'INSTALLER', ''),
    )
    # Test mandatory files found
    temp_path, fpaths = _create_test_files(test_files)

    dist = PythonInstalledDistribution(temp_path, "RECORD", "2.7")
    paths = dist.get_paths()
    _print_output(paths)
    assert len(paths) == 2
    assert dist.get_python_requirements() == frozenset(['==2.7'])
    assert dist.get_external_requirements() == frozenset(['C'])


def test_python_dist_info_conda_dependencies():
    test_files = (
        ('', 'METADATA', ('Name: foo\n'
                          'Requires-Python: >2.7,<5.0\n'
                          'Requires-Dist: bar ; python_version == "2.7"\n'
                          'Requires-Dist: spam ; python_version == "4.9"\n'
                          'Provides-Extra: docs\n'
                          'Requires-Dist: cheese >=1.0; extra == "docs"\n'
                          )
         ),
    )
    temp_path, fpaths = _create_test_files(test_files)
    path = os.path.dirname(fpaths[0])

    dist = PythonEggInfoDistribution(path, "4.9", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 4.9.*' in depends
    assert 'bar' not in depends
    assert 'spam' in depends
    assert 'cheese >=1.0' in constrains

    dist = PythonEggInfoDistribution(path, "2.7", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 2.7.*' in depends
    assert 'bar' in depends
    assert 'spam' not in depends
    assert 'cheese >=1.0' in constrains

    dist = PythonEggInfoDistribution(path, "3.4", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 3.4.*' in depends
    assert 'bar' not in depends
    assert 'spam' not in depends
    assert 'cheese >=1.0' in constrains


def test_python_dist_info_conda_dependencies_2():
    test_files = (
        ('', 'METADATA', ('Name: foo\n')),
    )
    temp_path, fpaths = _create_test_files(test_files)
    path = os.path.dirname(fpaths[0])

    dist = PythonEggInfoDistribution(path, "4.9", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 4.9.*' in depends


def test_python_dist_info_conda_dependencies_3():
    test_files = (
        ('', 'METADATA', ('Name: foo\n')),
    )
    temp_path, fpaths = _create_test_files(test_files)
    path = os.path.dirname(fpaths[0])

    dist = PythonEggInfoDistribution(path, "3.6", None)
    depends, constrains = dist.get_conda_dependencies()
    assert "python 3.6.*" in depends


def test_python_dist_egg_path():
    test_files = (
        ('', 'installed-files.txt', 'foo/bar\nfoo/spam\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)
    path = os.path.dirname(fpaths[0])

    dist = PythonEggInfoDistribution(path, "2.7", None)
    paths = dist.get_paths()
    _print_output(paths)
    assert len(paths) == 2


def test_python_dist_egg_fpath():
    test_files = (
        ('', 'zoom.egg-info', 'Name: Zoom\nVersion: 1.0\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)

    dist = PythonEggInfoDistribution(fpaths[0], "2.2", None)
    assert dist.name == 'Zoom'
    assert dist.norm_name == 'zoom'
    assert dist.version == '1.0'


# Markers
# -----------------------------------------------------------------------------
def test_evaluate_marker():
    # See: https://www.python.org/dev/peps/pep-0508/#complete-grammar
    # ((marker_expr, context, extras, expected_output), ...)
    test_cases = (
        # Valid context
        ('spam == "1.0"', {'spam': '1.0'}, True),
        # Should parse as (a and b) or c
        ("a=='a' and b=='b' or c=='c'", {'a': 'a', 'b': 'b', 'c': ''}, True),
        # Overriding precedence -> a and (b or c)
        ("a=='a' and (b=='b' or c=='c')", {'a': 'a', 'b': '', 'c': ''}, None),
        # Overriding precedence -> (a or b) and c
        ("(a=='a' or b=='b') and c=='c'", {'a': 'a', 'b': '', 'c': ''}, None),
    )
    for marker_expr, context, expected_output in test_cases:
        output = None
        if expected_output:
            output = interpret(marker_expr, context)
            assert output is expected_output
        else:
            output = interpret(marker_expr, context)
        _print_output(marker_expr, context, output, expected_output)

    # Test cases syntax error
    test_cases = (
        ('spam == "1.0"', {}, None),
        ('spam2 == "1.0"', {'spam': '1.0'}, None),
        # Malformed
        ('spam2 = "1.0"', {'spam': '1.0'}, None),
    )
    for marker_expr, context, expected_output in test_cases:
        output = None
        with pytest.raises(SyntaxError):
            output = interpret(marker_expr, context)


def test_get_default_marker_context():
    context = get_default_marker_context()
    for key, val in context.items():
        # Check deprecated keys have same value as new keys (. -> _)
        if '.' in key:
            other_val = context.get(key.replace('.', '_'))
            _print_output(val, other_val)
            assert val == other_val
