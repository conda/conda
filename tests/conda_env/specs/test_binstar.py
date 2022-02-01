# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import types
import unittest
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
from mock import patch, MagicMock
from binstar_client import errors

from conda_env.specs import binstar
from conda_env.specs.binstar import BinstarSpec
from conda_env.env import Environment


class TestBinstarSpec(unittest.TestCase):
    def test_has_can_handle_method(self):
        spec = BinstarSpec()
        self.assertTrue(hasattr(spec, 'can_handle'))
        self.assertIsInstance(spec.can_handle, types.MethodType)

    def test_name_not_present(self):
        spec = BinstarSpec(filename='filename')
        self.assertEqual(spec.can_handle(), False)
        self.assertEqual(spec.msg, "Can't process without a name")

    def test_invalid_name(self):
        spec = BinstarSpec(name='invalid-name')
        self.assertEqual(spec.can_handle(), False)
        self.assertEqual(spec.msg, "Invalid name, try the format: user/package")

    def test_package_not_exist(self):
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(side_effect=errors.NotFound('msg'))
            binstar = MagicMock(package=package)
            get_binstar_mock.return_value = binstar
            spec = BinstarSpec(name='darth/no-exist')
            self.assertEqual(spec.package, None)
            self.assertEqual(spec.can_handle(), False)

    def test_package_without_environment_file(self):
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(return_value={'files': []})
            binstar = MagicMock(package=package)
            get_binstar_mock.return_value = binstar
            spec = BinstarSpec('darth/no-env-file')

            self.assertEqual(spec.can_handle(), False)

    def test_download_environment(self):
        fake_package = {
            'files': [{'type': 'env', 'version': '1', 'basename': 'environment.yml'}]
        }
        fake_req = MagicMock(text=u"name: env")
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(return_value=fake_package)
            downloader = MagicMock(return_value=fake_req)
            binstar = MagicMock(package=package, download=downloader)
            get_binstar_mock.return_value = binstar

            spec = BinstarSpec(name='darth/env-file')
            self.assertIsInstance(spec.environment, Environment)

    def test_environment_version_sorting(self):
        fake_package = {
            'files': [
                {'type': 'env', 'version': '0.1.1', 'basename': 'environment.yml'},
                {'type': 'env', 'version': '0.1a.2', 'basename': 'environment.yml'},
                {'type': 'env', 'version': '0.2.0', 'basename': 'environment.yml'},
            ]
        }
        fake_req = MagicMock(text=u"name: env")
        with patch('conda_env.specs.binstar.get_binstar') as get_binstar_mock:
            package = MagicMock(return_value=fake_package)
            downloader = MagicMock(return_value=fake_req)
            binstar = MagicMock(package=package, download=downloader)
            get_binstar_mock.return_value = binstar

            spec = BinstarSpec(name='darth/env-file')
            spec.environment
            downloader.assert_called_with('darth', 'env-file', '0.2.0', 'environment.yml')

    def test_binstar_not_installed(self):
        spec = BinstarSpec(name='user/package')
        spec.binstar = None
        self.assertFalse(spec.can_handle())
        self.assertEqual(spec.msg, 'Please install binstar')


if __name__ == '__main__':
    unittest.main()
