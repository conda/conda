# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test for python distribution information and metadata handling."""
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager
from datetime import datetime
import os
from os.path import dirname, isdir, basename
from pprint import pprint
import tempfile

from conda.common.compat import odict, on_win
from conda.common.serialize import json_dump, json_load
from conda.common.url import join
from conda.core.prefix_data import PrefixData
from conda.core import python_dist as pd
from conda.core.python_dist import get_python_records

import pytest

from test_data.env_metadata import (
    METADATA_VERSION_PATHS, PATH_TEST_ENV_1, PATH_TEST_ENV_2, PATH_TEST_ENV_3, PATH_TEST_ENV_4,
    __file__ as env_metadata_file,
)

ENV_METADATA_DIR = dirname(env_metadata_file)

# Helpers
# -----------------------------------------------------------------------------
class DummyPythonRecord:
    files = []


@contextmanager
def set_on_win(val):
    import conda.common.path
    import conda.core.prefix_data
    import conda.core.python_dist
    on_win_saved = conda.common.path.on_win
    win_path_ok_saved_1 = conda.core.prefix_data.win_path_ok
    win_path_ok_saved_2 = conda.core.python_dist.win_path_ok
    rm_rf_saved = conda.core.prefix_data.rm_rf
    try:
        conda.common.path.on_win = val
        conda.core.prefix_data.rm_rf = lambda x: None
        if val and not on_win:
            conda.core.prefix_data.win_path_ok = lambda x: x
            conda.core.python_dist.win_path_ok = lambda x: x
        yield
    finally:
        conda.common.path.on_win = on_win_saved
        conda.core.prefix_data.win_path_ok = win_path_ok_saved_1
        conda.core.python_dist.win_path_ok = win_path_ok_saved_2
        conda.core.prefix_data.rm_rf = rm_rf_saved


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
        parsed_name = pd.norm_package_name(name)
        _print_output(name, parsed_name, expected_name)
        assert parsed_name == expected_name


def test_pypi_name_to_conda_name():
    test_cases = (
        (None, ''),
        ('', ''),
        ('graphviz', 'python-graphviz'),
    )
    for (name, expected_name) in test_cases:
        parsed_name = pd.pypi_name_to_conda_name(name)
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
        parsed_version = pd.norm_package_version(version)
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
        output = pd.split_spec(spec, sep)
        _print_output(spec, output, expected_output)
        assert output == expected_output


def test_parse_specification():
    test_reqs = {
        '':
            pd.PySpec('', [], '', '', ''),
        'requests':
            pd.PySpec('requests', [], '', '', ''),
        'requests >1.1':
            pd.PySpec('requests', [], '>1.1', '', ''),
        'requests[security]':
            pd.PySpec('requests', ['security'], '', '', ''),
        'requests[security] (>=1.1.0)':
            pd.PySpec('requests', ['security'], '>=1.1.0', '', ''),
        'requests[security]>=1.5.0':
            pd.PySpec('requests', ['security'], '>=1.5.0', '', ''),
        'requests[security] (>=4.5.0) ; something >= 27':
            pd.PySpec('requests', ['security'], '>=4.5.0', 'something >= 27', ''),
        'requests[security]>=3.3.0;something >= 2.7 ':
            pd.PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7', ''),
        'requests[security]>=3.3.0;something >= 2.7 or something_else == 1':
            pd.PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7 or something_else == 1', ''),
        'requests[security] >=3.3.0 ; something >= 2.7 or something_else == 1':
            pd.PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7 or something_else == 1', ''),
        'requests[security] (>=3.3.0) ; something >= 2.7 or something_else == 1':
            pd.PySpec('requests', ['security'], '>=3.3.0', 'something >= 2.7 or something_else == 1', ''),
        'requests[security] (>=3.3.0<4.4) ; something >= 2.7 or something_else == 1':
            pd.PySpec('requests', ['security'], '>=3.3.0<4.4', 'something >= 2.7 or something_else == 1', ''),
        'pyOpenSSL>=0.14':
            pd.PySpec('pyopenssl', [], '>=0.14', '', ''),
        'py.OpenSSL>=0.14':
            pd.PySpec('py-openssl', [], '>=0.14', '', ''),
        'py-OpenSSL>=0.14':
            pd.PySpec('py-openssl', [], '>=0.14', '', ''),
        'py_OpenSSL>=0.14':
            pd.PySpec('py-openssl', [], '>=0.14', '', ''),
        'zope.interface (>3.5.0)':
            pd.PySpec('zope-interface', [], '>3.5.0', '', ''),
        "A":
            pd.PySpec('a', [], '', '', ''),
        "A.B-C_D":
            pd.PySpec('a-b-c-d', [], '', '', ''),
        "aa":
            pd.PySpec('aa', [], '', '', ''),
        "name":
            pd.PySpec('name', [], '', '', ''),
        "name<=1":
            pd.PySpec('name', [], '<=1', '', ''),
        "name>=3":
            pd.PySpec('name', [], '>=3', '', ''),
        "name>=3,<2":
            pd.PySpec('name', [], '>=3,<2', '', ''),
        " name ( >= 3,  < 2 ) ":
            pd.PySpec('name', [], '>=3,<2', '', ''),
        "name@http://foo.com":
            pd.PySpec('name', [], '', '', 'http://foo.com'),
        " name [ fred , bar ] ( >= 3 , < 2 ) ":
            pd.PySpec('name', ['fred', 'bar'], '>=3,<2', '', ''),
        " name [fred,bar] ( >= 3 , < 2 )  @  http://foo.com ; python_version=='2.7' ":
            pd.PySpec('name', ['fred', 'bar'], '>=3,<2', "python_version=='2.7'", 'http://foo.com'),
        " name [fred,bar] @ http://foo.com ; python_version=='2.7' ":
            pd.PySpec('name', ['fred', 'bar'], '', "python_version=='2.7'", 'http://foo.com'),
        "name[quux, strange];python_version<'2.7' and platform_version=='2'":
            pd.PySpec('name', ['quux', 'strange'], '', "python_version<'2.7' and platform_version=='2'", ''),
        "name; os_name=='a' or os_name=='b'":
            pd.PySpec('name', [], '', "os_name=='a' or os_name=='b'", ''),
        "name; os_name=='a' and os_name=='b' or os_name=='c'":
            pd.PySpec('name', [], '', "os_name=='a' and os_name=='b' or os_name=='c'", ''),
        "name; os_name=='a' and (os_name=='b' or os_name=='c')":
            pd.PySpec('name', [], '', "os_name=='a' and (os_name=='b' or os_name=='c')", ''),
        " name; os_name=='a' or os_name=='b' and os_name=='c' ":
            pd.PySpec('name', [], '', "os_name=='a' or os_name=='b' and os_name=='c'", ''),
        " name ; (os_name=='a' or os_name=='b') and os_name=='c' ":
            pd.PySpec('name', [], '', "(os_name=='a' or os_name=='b') and os_name=='c'", ''),
        '>=3,<2':
            pd.PySpec('', [], '>=3,<2', '', ''),
        ' ( >=3 , <2 ) ':
            pd.PySpec('', [], '>=3,<2', '', ''),
        '>=2.7,!=3.0.*,!=3.1.*,!=3.2.*':
            pd.PySpec('', [], '>=2.7,!=3.0.*,!=3.1.*,!=3.2.*', '', ''),
    }
    for req, expected_req in test_reqs.items():
        parsed_req = pd.parse_specification(req)
        _print_output(req, parsed_req, expected_req)
        assert parsed_req == expected_req


def test_get_conda_anchor_files_and_records():
    valid_tests = [
        os.sep.join(('v', 'site-packages', 'spam', '.egg-info', 'PKG-INFO')),
        os.sep.join(('v', 'site-packages', 'foo', '.dist-info', 'RECORD')),
        os.sep.join(('v', 'site-packages', 'bar', '.egg-info')),
    ]
    invalid_tests = [
        os.sep.join(('i', 'site-packages', '.egg-link')),
        os.sep.join(('i', 'spam', '.egg-info', 'PKG-INFO')),
        os.sep.join(('i', 'foo', '.dist-info', 'RECORD')),
        os.sep.join(('i', 'bar', '.egg-info')),
        os.sep.join(('i', 'site-packages', 'spam')),
        os.sep.join(('i', 'site-packages', 'foo')),
        os.sep.join(('i', 'site-packages', 'bar')),
    ]
    tests = valid_tests + invalid_tests
    records = []
    for path in tests:
        record = DummyPythonRecord()
        record.files = [path]
        records.append(record)

    output = pd.get_conda_anchor_files_and_records(records)
    expected_output = odict()
    for i in range(len(valid_tests)):
        expected_output[valid_tests[i]] = records[i]

    _print_output(output, expected_output)
    assert output, expected_output


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

    outputs = pd.get_site_packages_anchor_files(temp_path, ref_dir)

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

    output = pd.get_dist_file_from_egg_link(fpaths2[0], '')
    expected_output = fpaths[0]
    _print_output(output, expected_output)
    assert output == expected_output

    # Test not existing path
    temp_path3, fpaths3 = _create_test_files((('', 'egg2.egg-link', '/not-a-path/'),))
    output = pd.get_dist_file_from_egg_link(fpaths3[0], '')
    expected_output = None
    _print_output(output, expected_output)
    assert output == expected_output

    # Test existing path but no valig egg-info files
    temp_path4 = tempfile.mkdtemp()
    temp_path4, fpaths4 = _create_test_files((('', 'egg2.egg-link', temp_path4),))
    output = pd.get_dist_file_from_egg_link(fpaths4[0], '')
    expected_output = None
    _print_output(output, expected_output)
    assert output == expected_output


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
        output = pd.get_python_distribution_info(temp_path2, basename(fpath), "1.1")
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
    cls = pd.PythonDistributionMetadata
    for keymap in cls.SINGLE_USE_KEYS, cls.MULTIPLE_USE_KEYS:
        for key, value in keymap.items():
            assert key.lower().replace('-', '_') == value


def test_metadata_process_path():
    name = 'META'
    test_files = (
        ('', name, 'Name: eggs\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)
    func = pd.PythonDistributionMetadata._process_path

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
    func = pd.PythonDistributionMetadata._read_metadata

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
    with pytest.warns(pd.MetadataWarning):
        path = pd.PythonDistributionMetadata._process_path(None, [])
    assert path is None

    # Check versions
    for fpath in METADATA_VERSION_PATHS:
        meta = pd.PythonDistributionMetadata(fpath)
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
@pytest.mark.xfail(datetime.now() < datetime(2018, 10, 1),
                   reason="This test needs to be refactored for the case of raising a hard "
                                "error when the anchor_file doesn't exist.",
                   strict=True)
def test_basepydist_check_path_data():
    test_cases = (
        (('path', 'sha256=1', '45'), ('path', '1', 45), None),
        (('path', 'sha256=1', 45), ('path', '1', 45), None),
        (('path', '', 45), ('path', None, 45), None),
        (('path', None, 45), ('path', None, 45), None),
        (('path', 'md5=', 45), (), AssertionError),
    )

    with pytest.warns(pd.MetadataWarning):
        dist = pd.BasePythonDistribution('/path-not-found/', "1.8")

    for args, expected_output, raises_ in test_cases:
        if raises_:
            with pytest.raises(raises_):
                output = dist._check_path_data(*args)
        else:
            output = dist._check_path_data(*args)
            _print_output(output, expected_output)
            assert output == expected_output


def test_basepydist_parse_requires_file_data():
    key = 'g'
    test_cases = (
        # (data, requirements, extras)
        ('', ([], [])),
        ('foo\n', (['foo'], [])),
        ('foo\n\n[:a == "a"]\nbar\n', (['foo', 'bar; a == "a"'], ['a'])),
        ('foo\n\n[a]\nbar\n', (['foo', 'bar; extra == "a"'], ['a'])),
    )
    func = pd.BasePythonDistribution._parse_requires_file_data

    for data, (expected_reqs, expected_extras) in test_cases:
        output_reqs, output_extras = func(data, key)
        _print_output(repr(data), output_reqs, frozenset(expected_reqs))
        assert sorted(list(output_reqs)) == sorted(list(expected_reqs))


def test_basepydist_parse_entries_file_data():
    func = pd.BasePythonDistribution._parse_entries_file_data
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

    dist = pd.PythonEggInfoDistribution(temp_path, "1.8", None)
    exp_req, exp_extra = (['foo', 'bar; extra == "a"'], ['a'])
    req, extra = dist._load_requires_provides_file()
    _print_output((list(sorted(req)), extra), (list(sorted(exp_req)), exp_extra))
    assert (list(sorted(req)), extra) == (list(sorted(exp_req)), exp_extra)


def test_dist_get_paths():
    content = 'foo/bar,sha256=1,"45"\nfoo/spam,,\n'
    temp_path, fpaths = _create_test_files((('', 'SOURCES.txt', content), ))

    dist = pd.PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist._get_paths()
    expected_output = [('lib/python2.7/site-packages/foo/bar', '1', 45),
                       ('lib/python2.7/site-packages/foo/spam', None, None)]
    _print_output(output, expected_output)
    assert output == expected_output


def test_dist_get_paths_no_paths():
    temp_path = tempfile.mkdtemp()
    dist = pd.PythonEggInfoDistribution(temp_path, "2.7", None)
    paths_data, files = dist.get_paths_data()
    expected_output = ()
    _print_output(files, expected_output)
    assert files == expected_output


def test_get_dist_requirements():
    test_files = (
        ('', 'METADATA', 'Name: spam\n'),
        ('', 'requires.txt', 'foo >1.0'),
    )
    temp_path, fpaths = _create_test_files(test_files)

    dist = pd.PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist.get_dist_requirements()
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

    dist = pd.PythonEggInfoDistribution(temp_path, "2.7", None)
    output = dist.get_extra_provides()
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

    dist = pd.PythonEggInfoDistribution(temp_path, "2.7", None)
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
    pd.PythonInstalledDistribution(temp_path, "2.7", None)

    # Test mandatory file not found
    os.remove(fpaths[0])
    with pytest.raises(AssertionError):
        pd.PythonInstalledDistribution(temp_path, "2.7", None)


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

    dist = pd.PythonInstalledDistribution(temp_path, "RECORD", "2.7")
    paths_data, files = dist.get_paths_data()
    _print_output(paths_data)
    assert len(paths_data.paths) == 2
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

    dist = pd.PythonEggInfoDistribution(path, "4.9", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 4.9.*' in depends
    assert 'bar' not in depends
    assert 'spam' in depends
    assert 'cheese >=1.0' in constrains

    dist = pd.PythonEggInfoDistribution(path, "2.7", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 2.7.*' in depends
    assert 'bar' in depends
    assert 'spam' not in depends
    assert 'cheese >=1.0' in constrains

    dist = pd.PythonEggInfoDistribution(path, "3.4", None)
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

    dist = pd.PythonEggInfoDistribution(path, "4.9", None)
    depends, constrains = dist.get_conda_dependencies()
    assert 'python 4.9.*' in depends


def test_python_dist_info_conda_dependencies_3():
    test_files = (
        ('', 'METADATA', ('Name: foo\n')),
    )
    temp_path, fpaths = _create_test_files(test_files)
    path = os.path.dirname(fpaths[0])

    dist = pd.PythonEggInfoDistribution(path, "3.6", None)
    depends, constrains = dist.get_conda_dependencies()
    assert "python 3.6.*" in depends


def test_python_dist_egg_path():
    test_files = (
        ('', 'installed-files.txt', 'foo/bar\nfoo/spam\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)
    path = os.path.dirname(fpaths[0])

    dist = pd.PythonEggInfoDistribution(path, "2.7", None)
    paths_data, files = dist.get_paths_data()
    _print_output(paths_data)
    assert len(paths_data.paths) == 2


def test_python_dist_egg_fpath():
    test_files = (
        ('', 'zoom.egg-info', 'Name: Zoom\nVersion: 1.0\n'),
    )
    temp_path, fpaths = _create_test_files(test_files)

    dist = pd.PythonEggInfoDistribution(fpaths[0], "2.2", None)
    assert dist.name == 'Zoom'
    assert dist.norm_name == 'zoom'
    assert dist.version == '1.0'


# Prefix Data
# -----------------------------------------------------------------------------
def test_pip_interop_windows():
    test_cases = (
        (PATH_TEST_ENV_3,
         ('babel', 'backports-functools-lru-cache', 'chardet', 'cheroot', 'cherrypy',
         'cssselect', 'dask', 'django', 'django-phonenumber-field', 'django-twilio',
         'entrypoints', 'h5py', 'idna', 'jaraco-functools', 'lxml', 'more-itertools',
         'numpy', 'parsel', 'phonenumberslite', 'pluggy', 'portend', 'py', 'pyjwt',
         'pyopenssl', 'pytz', 'pywin32', 'pywin32-ctypes', 'queuelib', 'requests',
         'scrapy', 'service-identity', 'six', 'tempora', 'tox', 'urllib3', 'virtualenv',
         'w3lib')
        ),
        (PATH_TEST_ENV_4,
         ('asn1crypto', 'attrs', 'automat', 'babel', 'backports-functools-lru-cache',
         'cffi', 'chardet', 'cheroot', 'cherrypy', 'configparser', 'constantly',
         'cryptography', 'cssselect', 'dask', 'django', 'django-phonenumber-field',
         'django-twilio', 'entrypoints', 'enum34', 'functools32', 'h5py', 'hdf5storage',
         'hyperlink', 'idna', 'incremental', 'ipaddress', 'jaraco-functools', 'keyring',
         'lxml', 'more-itertools', 'numpy', 'parsel', 'phonenumberslite', 'pluggy',
        'portend', 'py', 'pyasn1', 'pyasn1-modules', 'pycparser', 'pydispatcher',
        'pyhamcrest', 'pyjwt', 'pyopenssl', 'pytz', 'pywin32', 'pywin32-ctypes',
        'queuelib', 'requests', 'scrapy', 'service-identity', 'six', 'tempora', 'tox',
        'twilio', 'twisted', 'urllib3', 'virtualenv', 'w3lib', 'zope-interface')
        ),
    )

    for path, expected_output in test_cases:
        with set_on_win(True):
            if os.path.isdir(path):
                prefixdata = PrefixData(path, pip_interop_enabled=True)
                prefixdata.load()
                records = prefixdata._load_site_packages()
                record_names = tuple(sorted(records.keys()))
                print('RECORDS', record_names)
                assert len(record_names), len(expected_output)
                _print_output(expected_output, record_names)
                for record_name in record_names:
                    _print_output(record_name)
                    assert record_name in expected_output
                for record_name in expected_output:
                    _print_output(record_name)
                    assert record_name in record_names


def test_pip_interop_osx():
    test_cases = (
        (PATH_TEST_ENV_1,
         ('asn1crypto', 'babel', 'backports-functools-lru-cache', 'cffi', 'chardet',
          'cheroot', 'cherrypy', 'configparser', 'cryptography', 'cssselect', 'dask',
          'django', 'django-phonenumber-field', 'django-twilio', 'entrypoints',
          'enum34', 'h5py', 'idna', 'ipaddress', 'jaraco-functools', 'lxml',
          'more-itertools', 'numpy', 'parsel', 'phonenumberslite', 'pip', 'pluggy',
          'portend', 'py', 'pycparser', 'pyjwt', 'pyopenssl', 'pytz', 'queuelib',
          'requests', 'scrapy', 'service-identity', 'six', 'tempora', 'tox', 'twisted',
          'urllib3', 'virtualenv', 'w3lib')
        ),
        (PATH_TEST_ENV_2,
         ('asn1crypto', 'attrs', 'automat', 'babel', 'backports-functools-lru-cache',
          'cffi', 'chardet', 'cheroot', 'cherrypy', 'constantly', 'cryptography',
          'cssselect', 'dask', 'django', 'django-phonenumber-field', 'django-twilio',
          'entrypoints', 'h5py', 'hdf5storage', 'hyperlink', 'idna', 'incremental',
          'jaraco-functools', 'keyring', 'lxml', 'more-itertools', 'numpy', 'parsel',
          'phonenumberslite', 'pip', 'pluggy', 'portend', 'py', 'pyasn1', 'pyasn1-modules',
          'pycparser', 'pydispatcher', 'pyhamcrest', 'pyjwt', 'pyopenssl', 'pysocks', 'pytz',
          'queuelib', 'requests', 'scrapy', 'service-identity', 'six', 'tempora', 'tox',
          'twilio', 'twisted', 'urllib3', 'virtualenv', 'w3lib', 'zope-interface')
        ),
    )

    for path, expected_output in test_cases:
        if os.path.isdir(path):
            with set_on_win(False):
                prefixdata = PrefixData(path, pip_interop_enabled=True)
                prefixdata.load()
                records = prefixdata._load_site_packages()
                record_names = tuple(sorted(records.keys()))
                print('RECORDS', record_names)
                assert len(record_names), len(expected_output)
                _print_output(expected_output, record_names)
                for record_name in record_names:
                    _print_output(record_name)
                    assert record_name in expected_output
                for record_name in expected_output:
                    _print_output(record_name)
                    assert record_name in record_names


def test_scrapy_py36_osx_whl():
    anchor_files = (
        "lib/python3.6/site-packages/Scrapy-1.5.1.dist-info/RECORD",
    )
    prefix_path = join(ENV_METADATA_DIR, "py36-osx-whl")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "3.6")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "cssselect >=0.9",
            "lxml",
            "parsel >=1.1",
            "pydispatcher >=2.0.5",
            "pyopenssl",
            "python 3.6.*",
            "queuelib",
            "service-identity",
            "six >=1.5.2",
            "twisted >=13.1.0",
            "w3lib >=1.17.0"
        ],
        "fn": "Scrapy-1.5.1.dist-info",
        "name": "scrapy",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "1.5.1"
    }
    print(json_dump(files))
    print(json_dump(paths_data["paths"]))
    assert "lib/python3.6/site-packages/scrapy/core/scraper.py" in files
    assert "lib/python3.6/site-packages/scrapy/core/__pycache__/scraper.cpython-36.pyc" in files
    pd1 = {
        "_path": "lib/python3.6/site-packages/scrapy/core/scraper.py",
        "path_type": "hardlink",
        "sha256": "2559X9n2z1YKdFV9ElMRD6_88LIdqH1a2UwQimStt2k",
        "size_in_bytes": 9960
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": "lib/python3.6/site-packages/scrapy/core/__pycache__/scraper.cpython-36.pyc",
        "path_type": "hardlink",
        "sha256": None,
        "size_in_bytes": None
    }
    assert pd2 in paths_data["paths"]
    pd3 = {
        "_path": "bin/scrapy",
        "path_type": "hardlink",
        "sha256": "RncAAoxSEnSi_0VIopaRxsq6kryQGL61YbEweN2TW3g",
        "size_in_bytes": 268
    }
    assert pd3 in paths_data["paths"]


def test_twilio_py36_osx_whl():
    anchor_files = (
        "lib/python3.6/site-packages/twilio-6.16.1.dist-info/RECORD",
    )
    prefix_path = join(ENV_METADATA_DIR, "py36-osx-whl")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "3.6")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]
    pprint(prefix_rec.depends)
    pprint(prefix_rec.constrains)

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "pyjwt >=1.4.2",
            "pysocks",
            "python 3.6.*",
            "pytz",
            "requests >=2.0.0",
            "six"
        ],
        "fn": "twilio-6.16.1.dist-info",
        "name": "twilio",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "6.16.1"
    }
    print(json_dump(files))
    print(json_dump(paths_data["paths"]))
    assert "lib/python3.6/site-packages/twilio/compat.py" in files
    assert "lib/python3.6/site-packages/twilio/__pycache__/compat.cpython-36.pyc" in files
    pd1 = {
        "_path": "lib/python3.6/site-packages/twilio/compat.py",
        "path_type": "hardlink",
        "sha256": "sJ1t7CKvxpipiX5cyH1YwXTf3n_FsLf_taUhuCVsCwE",
        "size_in_bytes": 517
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": "lib/python3.6/site-packages/twilio/jwt/__pycache__/compat.cpython-36.pyc",
        "path_type": "hardlink",
        "sha256": None,
        "size_in_bytes": None
    }
    assert pd2 in paths_data["paths"]


def test_pyjwt_py36_osx_whl():
    anchor_files = (
        "lib/python3.6/site-packages/PyJWT-1.6.4.dist-info/RECORD",
    )
    prefix_path = join(ENV_METADATA_DIR, "py36-osx-whl")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "3.6")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [
            "cryptography >=1.4",
            "pytest <4,>3"
        ],
        "depends": [
            "python 3.6.*"
        ],
        "fn": "PyJWT-1.6.4.dist-info",
        "name": "pyjwt",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "1.6.4"
    }
    print(json_dump(files))
    print(json_dump(paths_data["paths"]))
    assert 'bin/pyjwt' in files
    assert 'lib/python3.6/site-packages/jwt/__pycache__/__init__.cpython-36.pyc' in files
    pd1 = {
        "_path": "bin/pyjwt",
        "path_type": "hardlink",
        "sha256": "wZET_24uZDEpsMdhAQ78Ass2k-76aQ59yPSE4DTE2To",
        "size_in_bytes": 260
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": "lib/python3.6/site-packages/jwt/contrib/__pycache__/__init__.cpython-36.pyc",
        "path_type": "hardlink",
        "sha256": None,
        "size_in_bytes": None
    }
    assert pd2 in paths_data["paths"]


def test_cherrypy_py36_osx_whl():
    anchor_files = (
        "lib/python3.6/site-packages/CherryPy-17.2.0.dist-info/RECORD",
    )
    prefix_path = join(ENV_METADATA_DIR, "py36-osx-whl")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "3.6")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [
            "jaraco-packaging >=3.2",
            # "pypiwin32 ==219",
            "pytest >=2.8",
            "python-memcached >=1.58",
            "routes >=2.3.1",
            "rst-linker >=1.9"
        ],
        "depends": [
            "cheroot >=6.2.4",
            "more-itertools",
            "portend >=2.1.1",
            "python 3.6.*",
            "six >=1.11.0"
        ],
        "fn": "CherryPy-17.2.0.dist-info",
        "name": "cherrypy",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "17.2.0"
    }


def test_scrapy_py27_osx_no_binary():
    anchor_files = (
        "lib/python2.7/site-packages/Scrapy-1.5.1-py2.7.egg-info/PKG-INFO",
    )
    prefix_path = join(ENV_METADATA_DIR, "py27-osx-no-binary")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "2.7")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "cssselect >=0.9",
            "lxml",
            "parsel >=1.1",
            "pydispatcher >=2.0.5",
            "pyopenssl",
            "python 2.7.*",
            "queuelib",
            "service-identity",
            "six >=1.5.2",
            "twisted >=13.1.0",
            "w3lib >=1.17.0"
        ],
        "fn": "Scrapy-1.5.1-py2.7.egg-info",
        "name": "scrapy",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "1.5.1"
    }
    print(json_dump(files))
    print(json_dump(paths_data["paths"]))
    assert "lib/python2.7/site-packages/scrapy/contrib/downloadermiddleware/decompression.py" in files
    assert "lib/python2.7/site-packages/scrapy/downloadermiddlewares/decompression.pyc" in files
    assert "bin/scrapy" in files
    pd1 = {
        "_path": "lib/python2.7/site-packages/scrapy/contrib/downloadermiddleware/decompression.py",
        "path_type": "hardlink"
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": "lib/python2.7/site-packages/scrapy/contrib/downloadermiddleware/decompression.pyc",
        "path_type": "hardlink"
    }
    assert pd2 in paths_data["paths"]
    pd3 = {
        "_path": "bin/scrapy",
        "path_type": "hardlink"
    }
    assert pd3 in paths_data["paths"]


def test_twilio_py27_osx_no_binary():
    anchor_files = (
        "lib/python2.7/site-packages/twilio-6.16.1-py2.7.egg-info/PKG-INFO",
    )
    prefix_path = join(ENV_METADATA_DIR, "py27-osx-no-binary")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "2.7")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]
    pprint(prefix_rec.depends)
    pprint(prefix_rec.constrains)

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "pyjwt >=1.4.2",
            "python 2.7.*",
            "pytz",
            "requests >=2.0.0",
            "six"
        ],
        "fn": "twilio-6.16.1-py2.7.egg-info",
        "name": "twilio",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "6.16.1"
    }
    print(json_dump(files))
    print(json_dump(paths_data["paths"]))
    assert "lib/python2.7/site-packages/twilio/compat.py" in files
    assert "lib/python2.7/site-packages/twilio/compat.pyc" in files
    pd1 = {
        "_path": "lib/python2.7/site-packages/twilio/compat.py",
        "path_type": "hardlink"
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": "lib/python2.7/site-packages/twilio/jwt/compat.pyc",
        "path_type": "hardlink"
    }
    assert pd2 in paths_data["paths"]


def test_pyjwt_py27_osx_no_binary():
    anchor_files = (
        "lib/python2.7/site-packages/PyJWT-1.6.4-py2.7.egg-info/PKG-INFO",
    )
    prefix_path = join(ENV_METADATA_DIR, "py27-osx-no-binary")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "2.7")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [
            "cryptography >=1.4",
            "pytest <4,>3"
        ],
        "depends": [
            "python 2.7.*"
        ],
        "fn": "PyJWT-1.6.4-py2.7.egg-info",
        "name": "pyjwt",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "1.6.4"
    }
    print(json_dump(files))
    print(json_dump(paths_data["paths"]))
    assert 'bin/pyjwt' in files
    assert 'lib/python2.7/site-packages/jwt/__init__.pyc' in files
    pd1 = {
        "_path": "bin/pyjwt",
        "path_type": "hardlink"
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": "lib/python2.7/site-packages/jwt/contrib/__init__.pyc",
        "path_type": "hardlink"
    }
    assert pd2 in paths_data["paths"]


def test_cherrypy_py27_osx_no_binary():
    anchor_files = (
        "lib/python2.7/site-packages/CherryPy-17.2.0-py2.7.egg-info/PKG-INFO",
    )
    prefix_path = join(ENV_METADATA_DIR, "py27-osx-no-binary")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "2.7")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [
            "jaraco-packaging >=3.2",
            "pytest >=2.8",
            "python-memcached >=1.58",
            "routes >=2.3.1",
            "rst-linker >=1.9"
        ],
        "depends": [
            "cheroot >=6.2.4",
            "more-itertools",
            "portend >=2.1.1",
            "python 2.7.*",
            "six >=1.11.0"
        ],
        "fn": "CherryPy-17.2.0-py2.7.egg-info",
        "name": "cherrypy",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "17.2.0"
    }


def test_six_py27_osx_no_binary_unmanageable():
    anchor_files = (
        "lib/python2.7/site-packages/six-1.11.0-py2.7.egg-info/PKG-INFO",
    )
    prefix_path = join(ENV_METADATA_DIR, "py27-osx-no-binary")
    if not isdir(prefix_path):
        pytest.skip("test files not found: %s" % prefix_path)
    prefix_recs = get_python_records(prefix_path, anchor_files, "2.7")
    assert len(prefix_recs) == 1
    prefix_rec = prefix_recs[0]

    dumped_rec = json_load(json_dump(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json_dump(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "python 2.7.*"
        ],
        "fn": "six-1.11.0-py2.7.egg-info",
        "name": "six",
        "package_type": "virtual_python_egg_unmanageable",
        "subdir": "pypi",
        "version": "1.11.0"
    }
    assert not files
    assert not prefix_rec.paths_data.paths
