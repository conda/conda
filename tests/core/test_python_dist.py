# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test for python distribution information and metadata handling."""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import tempfile

from conda.common.compat import odict
from conda.core.prefix_data import PrefixData
from conda.core.python_dist import (get_conda_anchor_files_and_records,
                                    get_site_packages_anchor_files,
                                    norm_package_name, norm_package_version,
                                    parse_specification, PySpec,
                                    get_dist_file_from_egg_link,
                                    PythonDistributionMetadata,
                                    pypi_name_to_conda_name,
                                    MetadataWarning)

import pytest

from .data import (PATH_TEST_ENV_1, PATH_TEST_ENV_2, SITE_PACKAGES_PATH_1,
                   SITE_PACKAGES_PATH_2, PATH_EGG_1, PATH_EGG_2,
                   METADATA_VERSION_PATHS)


class DummyPythonRecord:
    files = []


EGG_DATA = {
    'egg1': PATH_EGG_1,
    'egg2': PATH_EGG_2,
}
TEST_BASE_METADATA = {
    'Metadata-Version': '5.0',
    'Name': 'name',
    'Version': '1.2',
}


# Helper functions
# -----------------------------------------------------------------------------
def create_metadata(data, name="METADATA"):
    temp_path = tempfile.mkdtemp()
    temp_fpath = os.path.join(temp_path, name)
    lines = []
    for key, value in data.items():
        lines.append("{0}: {1}".format(key, value))

    new_data = '\n'.join(lines) if lines else ''
    with open(temp_fpath, 'w') as fh:
        fh.write(new_data)

    return temp_fpath


def create_egg_links():
    for sp_path in [SITE_PACKAGES_PATH_1, SITE_PACKAGES_PATH_2]:
        for name, test_egg_path in EGG_DATA.items():
            temp_fpath = os.path.join(sp_path, name + ".egg-link")

            with open(temp_fpath, 'w') as fh:
                fh.write(test_egg_path + '\n')


def delete_egg_links():
    for sp_path in [SITE_PACKAGES_PATH_1, SITE_PACKAGES_PATH_2]:
        for name, test_egg_path in EGG_DATA.items():
            temp_fpath = os.path.join(sp_path, name + ".egg-link")
            os.remove(temp_fpath)


def _print_output(*args):
    """Helper function to print output in case of failed tests."""
    for arg in args:
        print(arg)
    print('\n')


# Test module helper functions
# -----------------------------------------------------------------------------
def test_norm_package_name():
    test_names = {
        '': '',
        'pyOpenssl': 'pyopenssl',
        'py.Openssl': 'py-openssl',
        'py-Openssl': 'py-openssl',
        'py_Openssl': 'py-openssl',
        'zope.interface': 'zope-interface',
    }
    for name, expected_name in test_names.items():
        parsed_name = norm_package_name(name)
        _print_output(name, parsed_name, expected_name)
        assert parsed_name == expected_name


def test_pypi_name_to_conda_name():
    test_names = {
        'graphviz': 'python-graphviz',
    }
    for name, expected_name in test_names.items():
        parsed_name = pypi_name_to_conda_name(name)
        _print_output(name, parsed_name, expected_name)
        assert parsed_name == expected_name


def test_norm_package_version():
    test_versions = {
        '': '',
        '>=2': '>=2',
        '(>=2)': '>=2',
        ' (>=2) ': '>=2',
        '>=2,<3': '>=2,<3',
        '>=2, <3': '>=2,<3',
        ' (>=2, <3) ': '>=2,<3',
    }
    for version, expected_version in test_versions.items():
        parsed_version = norm_package_version(version)
        _print_output(version, parsed_version, expected_version)
        assert parsed_version == expected_version


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
    }
    for req, expected_req in test_reqs.items():
        parsed_req = parse_specification(req)
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

    output = get_conda_anchor_files_and_records(records)
    expected_output = odict()
    for i in range(len(valid_tests)):
        expected_output[valid_tests[i]] = records[i]

    _print_output(output, expected_output)
    assert output, expected_output


def test_get_site_packages_anchor_files():
    for path in [SITE_PACKAGES_PATH_1, SITE_PACKAGES_PATH_1]:
        result = get_site_packages_anchor_files(path, 'some-reference-dir')
        print(result)


def test_get_dist_file_from_egg_link():
    _, temp_dir = tempfile.mkstemp()
    test_cases = {
        # Valid cases
        PATH_EGG_1: '/egg1.egg-info/PKG-INFO',
        PATH_EGG_2: '/egg2.egg-info',
        # Invalid cases
        '/random/not-a-path/': None,  # Not an actual path
        temp_dir: None,               # An actual path but is no egg-info files
    }

    for test_egg_path, expected_output in test_cases.items():
        _, temp_fpath = tempfile.mkstemp(suffix=".egg-link")
        with open(temp_fpath, 'w') as fh:
            fh.write(test_egg_path + '\n')

        result = get_dist_file_from_egg_link(temp_fpath, '')
        _print_output(temp_fpath, test_egg_path, result)

        # Using str() to handle the None test case with the same logic
        assert str(result).endswith(str(expected_output))


@pytest.mark.xfail
def test_get_python_record():
    assert False


@pytest.mark.xfail
def test_get_python_records():
    assert False


# Markers
# -----------------------------------------------------------------------------
@pytest.mark.xfail
def test_evaluate_marker():
    assert False


@pytest.mark.xfail
def test_update_marker_context():
    assert False


@pytest.mark.xfail
def test_get_default_marker_context():
    assert False


# Metadata
# -----------------------------------------------------------------------------
def test_metadata_keys():
    cls = PythonDistributionMetadata
    for keymap in cls.SINGLE_USE_KEYS, cls.MULTIPLE_USE_KEYS:
        for key, value in keymap.items():
            assert key.lower().replace('-', '_') == value


def test_metadata_process_path():
    name = 'METADATA'
    test_fpath = create_metadata({}, name=name)
    test_path = os.path.dirname(test_fpath)
    func = PythonDistributionMetadata._process_path

    # Test valid directory
    output_fpath = func(test_path, [name])
    _print_output(test_fpath, output_fpath)
    assert output_fpath == test_fpath

    # Test valid directory (empty files)
    output_fpath = func(test_path, [])
    _print_output(test_fpath, output_fpath)
    assert output_fpath is None

    # Test valid directory (file order)
    output_fpath = func(test_path, ['something', name, 'something-else'])
    _print_output(test_fpath, output_fpath)
    assert output_fpath is output_fpath

    # Test file
    output_fpath = func(test_fpath, [name])
    _print_output(test_fpath, output_fpath)
    assert output_fpath == test_fpath


def test_metadata_read_metadata():
    func = PythonDistributionMetadata._read_metadata

    # Test existing file unknown key
    data = odict()
    data['Unknown-Key'] = 'unknown'
    data['Unknown-Key-2'] = 'unknown-2'
    test_fpath = create_metadata(data)
    expected_data = odict()
    expected_data['unknown_key'] = 'unknown'
    expected_data['unknown_key_2'] = 'unknown-2'

    with pytest.warns(MetadataWarning):
        output_data = func(test_fpath)

    _print_output(output_data, expected_data)
    assert output_data == expected_data

    # Test existing file known key
    data = odict()
    data['Name'] = 'name'
    expected_data = odict()
    expected_data['name'] = 'name'
    test_fpath = create_metadata(data)
    output_data = func(test_fpath)

    _print_output(output_data, expected_data)
    assert output_data == expected_data

    # Test non existing file
    test_fpath = '/foo/bar/'
    expected_data = odict()
    output_data = func(test_fpath)

    _print_output(output_data, expected_data)
    assert output_data == expected_data


def test_metadata():
    # Check warnings are raised for None path
    with pytest.warns(MetadataWarning):
        path = PythonDistributionMetadata._process_path(None, [])
    assert path is None

    # Check versions
    for fpath in METADATA_VERSION_PATHS:
        meta = PythonDistributionMetadata(fpath)
        a = meta.get_dist_requirements(True)
        a = meta.get_dist_requirements()
        b = meta.get_python_requirements(True)
        b = meta.get_python_requirements()
        c = meta.get_extra_provides()
        d = meta.get_dist_provides(True)
        d = meta.get_dist_provides()
        e = meta.get_dist_obsolete(True)
        e = meta.get_dist_obsolete()
        f = meta.get_classifiers(True)
        f = meta.get_classifiers()
        name = meta.name
        version = meta.version
        _print_output(fpath, meta._data, a, b, c, d, e, f, name, version)
        assert len(meta._data)
        assert name == 'BeagleVote'
        assert version == '1.0a2'


# Python Distributions
# -----------------------------------------------------------------------------
@pytest.mark.xfail
def test_ptyhon_distribution_dist_info():
    assert False


@pytest.mark.xfail
def test_ptyhon_distribution_dist_egg():
    assert False


# Prefix Data
# -----------------------------------------------------------------------------
def _pip_interop():
    create_egg_links()

    test_cases = {
        PATH_TEST_ENV_1: ['anaconda-client', 'conda', 'loghub', 'libsass'],
        PATH_TEST_ENV_2: [
            'anaconda-client', 'conda',
            'asn1crypto', 'babel', 'cffi', 'chardet', 'cryptography', 'dask',
            'django', 'django-phonenumber-field', 'django-twilio', 'enum34',
            'h5py', 'hdf5storage', 'idna', 'ipaddress', 'numpy', 'packaging',
            'phonenumberslite', 'pluggy', 'py', 'pycparser', 'pyjwt',
            'pyopenssl', 'pyparsing', 'pytz', 'requests', 'six', 'tox',
            'twilio', 'urllib3', 'virtualenv'
        ]
    }

    for path, expected_output in test_cases.items():
        pd = PrefixData(path, pip_interop_enabled=True)
        pd.load()
        records = pd._load_site_packages()
        record_names = tuple(sorted(records.keys()))
        for record_name in record_names:
            _print_output(expected_output, record_names)
            assert record_name in expected_output

    delete_egg_links()
