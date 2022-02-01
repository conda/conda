# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import os
from conda_env.installers import pip
from conda.exceptions import CondaValueError


class PipInstallerTest(unittest.TestCase):
    def test_straight_install(self):

        # To check that the correct file would be written
        written_deps = []

        def log_write(text):
            written_deps.append(text)
            return mock.DEFAULT

        with mock.patch.object(pip.subprocess, 'Popen') as mock_popen, \
                mock.patch.object(pip, 'pip_args') as mock_pip_args, \
                mock.patch('tempfile.NamedTemporaryFile', mock.mock_open()) as mock_namedtemp:
            # Mock
            mock_popen.return_value.returncode = 0
            mock_pip_args.return_value = (['pip'], '9.0.1')
            mock_namedtemp.return_value.write.side_effect = log_write
            mock_namedtemp.return_value.name = 'tmp-file'
            args = mock.Mock()
            root_dir = '/whatever' if os.name != 'nt' else 'C:\\whatever'
            args.file = os.path.join(root_dir, 'environment.yml')
            # Run
            pip.install('/some/prefix', ['foo', '-e ./bar'], args)
            # Check expectations
            mock_popen.assert_called_with(['pip', 'install', '-r', 'tmp-file'],
                                          cwd=root_dir,
                                          universal_newlines=True)
            self.assertEqual(1, mock_popen.return_value.communicate.call_count)
            self.assertEqual(written_deps, ['foo\n-e ./bar'])

    def test_stops_on_exception(self):
        with mock.patch.object(pip.subprocess, 'Popen') as popen:
            popen.return_value.returncode = 22
            with mock.patch.object(pip, 'pip_args') as pip_args:
                # make sure that installed doesn't bail early
                pip_args.return_value = (['pip'], '9.0.1')

                self.assertRaises(CondaValueError, pip.install,
                                  '/some/prefix', ['foo'], None)
