# -*- coding: utf-8 -*-


"""
Example packages:

- https://github.com/frejanordsiek/hdf5storage/blob/0.1.15/setup.py
- https://github.com/dask/dask/blob/master/setup.py
- https://github.com/rdegges/django-twilio/blob/master/setup.py
- https://github.com/twilio/twilio-python/blob/master/setup.py
- https://github.com/tox-dev/tox/blob/master/setup.py

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os

from conda.common.compat import odict
from conda.core.prefix_data import PrefixData
from conda.core.python_dist import (get_conda_anchor_files_and_records,
                                    norm_package_name, norm_package_version,
                                    parse_requirement, PySpec)


class DummyPythonRecord:
    files = []


def test_norm_package_name():
    test_names = {
        '': '',
        'pyOpenssl': 'pyopenssl',
        'py.Openssl': 'py-openssl',
        'py-Openssl': 'py-openssl',
        'py_Openssl': 'py-openssl',
        'PasteDeploy': 'pastedeploy',
        'zope.interface': 'zope-interface',
    }
    for name, expected_name in test_names.items():
        parsed_name = norm_package_name(name)
        print(name)
        print(parsed_name)
        print(expected_name)
        print('\n')
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
        print(version)
        print(parsed_version)
        print(parsed_version)
        print('\n')
        assert parsed_version == expected_version


def test_parse_requirement():
    test_reqs = {
        'requests':
            PySpec('requests', None, None, None),
        'requests >1.1':
            PySpec('requests', None, '>1.1', None),
        'requests[security]':
            PySpec('requests', 'security', None, None),
        'requests[security] (>=1.1.0)':
            PySpec('requests', 'security', '>=1.1.0', None),
        'requests[security]>=1.5.0':
            PySpec('requests', 'security', '>=1.5.0', None),
        'requests[security] (>=4.5.0) ; something >= 27':
            PySpec('requests', 'security', '>=4.5.0', 'something >= 27'),
        'requests[security]>=3.3.0;something >= 2.7 ':
            PySpec('requests', 'security', '>=3.3.0', 'something >= 2.7'),
        'requests[security]>=3.3.0;something >= 2.7 or something_else == 1':
            PySpec('requests', 'security', '>=3.3.0', 'something >= 2.7 or something_else == 1'),
        'requests[security] >=3.3.0 ; something >= 2.7 or something_else == 1':
            PySpec('requests', 'security', '>=3.3.0', 'something >= 2.7 or something_else == 1'),
        'requests[security] (>=3.3.0) ; something >= 2.7 or something_else == 1':
            PySpec('requests', 'security', '>=3.3.0', 'something >= 2.7 or something_else == 1'),
        'requests[security] (>=3.3.0<4.4) ; something >= 2.7 or something_else == 1':
            PySpec('requests', 'security', '>=3.3.0<4.4', 'something >= 2.7 or something_else == 1'),
        'pyOpenSSL>=0.14':
            PySpec('pyopenssl', None, '>=0.14', None),
        'py.OpenSSL>=0.14':
            PySpec('py-openssl', None, '>=0.14', None),
        'py-OpenSSL>=0.14':
            PySpec('py-openssl', None, '>=0.14', None),
        'py_OpenSSL>=0.14':
            PySpec('py-openssl', None, '>=0.14', None),
        'zope.interface (>3.5.0)':
            PySpec('zope-interface', None, '>3.5.0', None),
    }
    for req, expected_req in test_reqs.items():
        parsed_req = parse_requirement(req)
        print(req)
        print(parsed_req)
        print(expected_req)
        print('\n')
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

    print(output)
    print(expected_output)
    assert output, expected_output


def test_pip_interop():
    pass
    # path = '/Users/gpena-castellanos/Desktop/tests-pydist-env'
    # pd = PrefixData(path, True)
    # pd.load()
    # pd._load_site_packages()
    # print(pd.__prefix_records)


def test_ptyhon_distribution_metadata():
    pass


def test_ptyhon_distribution_dist_info():
    pass


def test_ptyhon_distribution_dist_egg():
    pass


def test_get_python_distribution_info():
    pass
    # Test dist

    # Test egg-link


def test_get_dist_file_from_egg_link():
    pass


def test_get_python_record():
    pass


def test_get_site_packages_anchor_files():
    pass
