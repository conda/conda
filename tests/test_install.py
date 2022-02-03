# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from conda.base.context import context
from conda.common.compat import text_type
from conda.core.package_cache_data import download
from conda.core.portability import _PaddingError, binary_replace, update_prefix
from conda.gateways.disk.delete import move_path_to_trash
from conda.gateways.disk.read import read_no_link, yield_lines
from conda.models.enums import FileMode
from conda.utils import on_win
from os import chdir, getcwd, makedirs
from os.path import exists, join, relpath
import pytest
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

from conda.testing.helpers import mock

patch = mock.patch if mock else None


def generate_random_path():
    return '/some/path/to/file%s' % random.randint(100, 200)


class TestBinaryReplace(unittest.TestCase):

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_simple(self):
        self.assertEqual(
            binary_replace(b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbbb'),
            b'xxxbbbbbxyz\x00zz')

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_shorter(self):
        self.assertEqual(
            binary_replace(b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbb'),
            b'xxxbbbbxyz\x00\x00zz')

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_too_long(self):
        self.assertRaises(_PaddingError, binary_replace,
                          b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbbbbbb')

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_no_extra(self):
        self.assertEqual(binary_replace(b'aaaaa\x00', b'aaaaa', b'bbbbb'),
                         b'bbbbb\x00')

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_two(self):
        self.assertEqual(
            binary_replace(b'aaaaa\x001234aaaaacc\x00\x00', b'aaaaa',
                           b'bbbbb'),
            b'bbbbb\x001234bbbbbcc\x00\x00')

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_spaces(self):
        self.assertEqual(
            binary_replace(b' aaaa \x00', b'aaaa', b'bbbb'),
            b' bbbb \x00')

    @pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
    def test_multiple(self):
        self.assertEqual(
            binary_replace(b'aaaacaaaa\x00', b'aaaa', b'bbbb'),
            b'bbbbcbbbb\x00')
        self.assertEqual(
            binary_replace(b'aaaacaaaa\x00', b'aaaa', b'bbb'),
            b'bbbcbbb\x00\x00\x00')
        self.assertRaises(_PaddingError, binary_replace,
                          b'aaaacaaaa\x00', b'aaaa', b'bbbbb')

    @pytest.mark.integration
    @pytest.mark.skipif(not on_win, reason="exe entry points only necessary on win")
    def test_windows_entry_point(self):
        """
        This emulates pip-created entry point executables on windows.  For more info,
        refer to conda/install.py::replace_entry_point_shebang
        """
        tmp_dir = tempfile.mkdtemp()
        cwd = getcwd()
        chdir(tmp_dir)
        original_prefix = "C:\\BogusPrefix\\python.exe"
        try:
            url = 'https://s3.amazonaws.com/conda-dev/pyzzerw.pyz'
            download(url, 'pyzzerw.pyz')
            url = 'https://files.pythonhosted.org/packages/source/c/conda/conda-4.1.6.tar.gz'
            download(url, 'conda-4.1.6.tar.gz')
            subprocess.check_call([sys.executable, 'pyzzerw.pyz',
                                   # output file
                                   '-o', 'conda.exe',
                                   # entry point
                                   '-m', 'conda.cli.main:main',
                                   # initial shebang
                                   '-s', '#! ' + original_prefix,
                                   # launcher executable to use (32-bit text should be compatible)
                                   '-l', 't32',
                                   # source archive to turn into executable
                                   'conda-4.1.6.tar.gz',
                                   ],
                                  cwd=tmp_dir)
            # this is the actual test: change the embedded prefix and make sure that the exe runs.
            data = open('conda.exe', 'rb').read()
            fixed_data = binary_replace(data, original_prefix, sys.executable)
            with open("conda.fixed.exe", 'wb') as f:
                f.write(fixed_data)
            # without a valid shebang in the exe, this should fail
            with pytest.raises(subprocess.CalledProcessError):
                subprocess.check_call(['conda.exe', '-h'])

            process = subprocess.Popen(['conda.fixed.exe', '-h'],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            output, error = process.communicate()
            output = output.decode('utf-8')
            error = error.decode('utf-8')
            assert ("conda is a tool for managing and deploying applications, "
                    "environments and packages.") in output
        except:
            raise
        finally:
            chdir(cwd)


class FileTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfname = join(self.tmpdir, 'testfile')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_default_text(self):
        with open(self.tmpfname, 'w') as fo:
            fo.write('#!/opt/anaconda1anaconda2anaconda3/bin/python\n'
                     'echo "Hello"\n')
        update_prefix(self.tmpfname, '/usr/local')
        with open(self.tmpfname, 'r') as fi:
            data = fi.read()
            self.assertEqual(data, '#!/usr/local/bin/python\n'
                                   'echo "Hello"\n')

    @pytest.mark.skipif(on_win, reason="test is invalid on windows")
    def test_long_default_text(self):
        with open(self.tmpfname, 'w') as fo:
            fo.write('#!/opt/anaconda1anaconda2anaconda3/bin/python -O\n'
                     'echo "Hello"\n')
        new_prefix = '/usr/local/{0}'.format('1234567890'*12)
        update_prefix(self.tmpfname, new_prefix)
        with open(self.tmpfname, 'r') as fi:
            data = fi.read()
            self.assertEqual(data, '#!/usr/bin/env python -O\n'
                                   'echo "Hello"\n')

    @pytest.mark.skipif(on_win, reason="no binary replacement done on win")
    def test_binary(self):
        with open(self.tmpfname, 'wb') as fo:
            fo.write(b'\x7fELF.../some-placeholder/lib/libfoo.so\0')
        update_prefix(self.tmpfname, '/usr/local',
                      placeholder='/some-placeholder', mode=FileMode.binary)
        with open(self.tmpfname, 'rb') as fi:
            data = fi.read()
            self.assertEqual(
                data,
                b'\x7fELF.../usr/local/lib/libfoo.so\0\0\0\0\0\0\0\0'
            )

    def test_trash_outside_prefix(self):
        tmp_dir = tempfile.mkdtemp()
        rel = relpath(tmp_dir, context.root_dir)
        self.assertTrue(rel.startswith(u'..'))
        move_path_to_trash(tmp_dir)
        self.assertFalse(exists(tmp_dir))
        makedirs(tmp_dir)
        move_path_to_trash(tmp_dir)
        self.assertFalse(exists(tmp_dir))


# class remove_readonly_TestCase(unittest.TestCase):
#     def test_takes_three_args(self):
#         with self.assertRaises(TypeError):
#             install.\
#                 _remove_readonly()
#
#         with self.assertRaises(TypeError):
#             install._remove_readonly(True)
#
#         with self.assertRaises(TypeError):
#             install._remove_readonly(True, True)
#
#         with self.assertRaises(TypeError):
#             install._remove_readonly(True, True, True, True)
#
#     @skip_if_no_mock
#     def test_calls_os_chmod(self):
#         some_path = generate_random_path()
#         with patch.object(install.os, 'chmod') as chmod:
#             install._remove_readonly(mock.Mock(), some_path, {})
#         chmod.assert_called_with(some_path, stat.S_IWRITE)
#
#     @skip_if_no_mock
#     def test_calls_func(self):
#         some_path = generate_random_path()
#         func = mock.Mock()
#         with patch.object(install.os, 'chmod'):
#             install._remove_readonly(func, some_path, {})
#         func.assert_called_with(some_path)


# class rm_rf_file_and_link_TestCase(unittest.TestCase):
#     @contextmanager
#     def generate_mock_islink(self, value):
#         with patch.object(install, 'islink', return_value=value) as islink:
#             yield islink
#
#     @contextmanager
#     def generate_mock_isdir(self, value):
#         with patch.object(install, 'isdir', return_value=value) as isdir:
#             yield isdir
#
#     @contextmanager
#     def generate_mock_isfile(self, value):
#         with patch.object(install, 'isfile', return_value=value) as isfile:
#             yield isfile
#
#     @contextmanager
#     def generate_mock_os_access(self, value):
#         with patch.object(install.os, 'access', return_value=value) as os_access:
#             yield os_access
#
#     @contextmanager
#     def generate_mock_unlink(self):
#         with patch.object(install, 'backoff_unlink') as unlink:
#             yield unlink
#
#     @contextmanager
#     def generate_mock_rename(self):
#         with patch.object(install.os, 'rename') as rename:
#             yield rename
#
#     @contextmanager
#     def generate_mock_rmtree(self):
#         with patch.object(install.shutil, 'rmtree') as rmtree:
#             yield rmtree
#
#     @contextmanager
#     def generate_mock_log(self):
#         with patch.object(install, 'log') as log:
#             yield log
#
#     @contextmanager
#     def generate_mock_on_win(self, value):
#         original = install.on_win
#         install.on_win = value
#         yield
#         install.on_win = original
#
#     @contextmanager
#     def generate_mock_check_call(self):
#         with patch.object(install.subprocess, 'check_call') as check_call:
#             yield check_call
#
#     @contextmanager
#     def generate_mocks(self, islink=True, isfile=True, isdir=True, on_win=False, os_access=True):
#         with self.generate_mock_islink(islink) as mock_islink:
#             with self.generate_mock_isfile(isfile) as mock_isfile:
#                 with self.generate_mock_os_access(os_access) as mock_os_access:
#                     with self.generate_mock_isdir(isdir) as mock_isdir:
#                         with self.generate_mock_rename() as mock_rename:
#                             with self.generate_mock_unlink() as mock_unlink:
#                                 with self.generate_mock_rmtree() as mock_rmtree:
#                                     with self.generate_mock_log() as mock_log:
#                                         with self.generate_mock_on_win(on_win):
#                                             with self.generate_mock_check_call() as check_call:
#                                                 yield {
#                                                     'islink': mock_islink,
#                                                     'isfile': mock_isfile,
#                                                     'isdir': mock_isdir,
#                                                     'os_access': mock_os_access,
#                                                     'unlink': mock_unlink,
#                                                     'rename': mock_rename,
#                                                     'rmtree': mock_rmtree,
#                                                     'log': mock_log,
#                                                     'check_call': check_call,
#                                             }
#
#     def generate_directory_mocks(self, on_win=False):
#         return self.generate_mocks(islink=False, isfile=False, isdir=True,
#                                    on_win=on_win)
#
#     def generate_all_false_mocks(self):
#         return self.generate_mocks(False, False, False)
#
#     @property
#     def generate_random_path(self):
#         return generate_random_path()
#
#     @skip_if_no_mock
#     def test_calls_islink(self):
#         with self.generate_mocks() as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         mocks['islink'].assert_called_with(some_path)
#
#     @skip_if_no_mock
#     def test_calls_unlink_on_true_islink(self):
#         with self.generate_mocks() as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         mocks['unlink'].assert_called_with(some_path)
#
#     @skip_if_no_mock
#     def test_calls_rename_if_unlink_fails(self):
#         with self.generate_mocks() as mocks:
#             mocks['unlink'].side_effect = OSError(errno.ENOEXEC, "blah")
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         assert mocks['unlink'].call_count > 1
#         assert mocks['rename'].call_count == 1
#         rename_args = mocks['rename'].call_args[0]
#         assert rename_args[0] == mocks['unlink'].call_args_list[0][0][0]
#         assert dirname(rename_args[1]) in (ca[0][0] for ca in mocks['unlink'].call_args_list)
#
#     @skip_if_no_mock
#     def test_calls_unlink_on_os_access_false(self):
#         with self.generate_mocks(os_access=False) as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         mocks['unlink'].assert_called_with(some_path)
#
#     @skip_if_no_mock
#     def test_does_not_call_isfile_if_islink_is_true(self):
#         with self.generate_mocks() as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         self.assertFalse(mocks['isfile'].called)
#
#     @skip_if_no_mock
#     def test_calls_isfile_with_path(self):
#         with self.generate_mocks(islink=False, isfile=True) as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         mocks['isfile'].assert_called_with(some_path)
#
#     @skip_if_no_mock
#     def test_calls_unlink_on_false_islink_and_true_isfile(self):
#         with self.generate_mocks(islink=False, isfile=True) as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         mocks['unlink'].assert_called_with(some_path)
#
#     @skip_if_no_mock
#     def test_does_not_call_unlink_on_false_values(self):
#         with self.generate_mocks(islink=False, isfile=False) as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         self.assertFalse(mocks['unlink'].called)
#
#     @skip_if_no_mock
#     def test_does_not_call_shutil_on_false_isdir(self):
#         with self.generate_all_false_mocks() as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         self.assertFalse(mocks['rmtree'].called)
#
#     @skip_if_no_mock
#     def test_calls_rmtree_at_least_once_on_isdir_true(self):
#         with self.generate_directory_mocks() as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         mocks['rmtree'].assert_called_with(
#             some_path, onerror=warn_failed_remove, ignore_errors=False)
#
#     @skip_if_no_mock
#     def test_calls_rmtree_and_rename_on_win(self):
#         with self.generate_directory_mocks(on_win=True) as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         assert mocks['rename'].call_count == 1
#         assert mocks['rmtree'].call_count == 1
#         assert mocks['rename'].call_args[0][1] == mocks['rmtree'].call_args[0][0]
#
#     @skip_if_no_mock
#     def test_calls_rmtree_and_rename_on_unix(self):
#         with self.generate_directory_mocks() as mocks:
#             mocks['rmtree'].side_effect = OSError
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         assert mocks['rename'].call_count == 1
#         assert mocks['rmtree'].call_count > 1
#         assert dirname(mocks['rename'].call_args[0][1]) == mocks['rmtree'].call_args[0][0]
#
#     @skip_if_no_mock
#     def test_calls_rmtree_only_once_on_success(self):
#         with self.generate_directory_mocks() as mocks:
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path)
#         self.assertEqual(1, mocks['rmtree'].call_count)
#
#     @skip_if_no_mock
#     def test_raises_final_exception_if_it_cant_remove(self):
#         with self.generate_directory_mocks(on_win=True) as mocks:
#             mocks['rmtree'].side_effect = OSError
#             mocks['rename'].side_effect = OSError
#             some_path = self.generate_random_path
#             with self.assertRaises(OSError):
#                 conda.common.disk.rm_rf(some_path, trash=False)
#
#     @skip_if_no_mock
#     def test_retries_six_times_to_ensure_it_cant_really_remove(self):
#         with self.generate_directory_mocks() as mocks:
#             mocks['rmtree'].side_effect = OSError
#             some_path = self.generate_random_path
#             with self.assertRaises(OSError):
#                 conda.common.disk.rm_rf(some_path, trash=False)
#         self.assertEqual(6, mocks['rmtree'].call_count)
#
#     @skip_if_no_mock
#     def test_retries_as_many_as_max_retries_plus_one(self):
#         max_retries = random.randint(7, 10)
#         with self.generate_directory_mocks() as mocks:
#             mocks['rmtree'].side_effect = OSError
#             some_path = self.generate_random_path
#             with self.assertRaises(OSError):
#                 conda.common.disk.rm_rf(some_path, max_retries=max_retries, trash=False)
#         self.assertEqual(max_retries + 1, mocks['rmtree'].call_count)
#
#     @skip_if_no_mock
#     def test_stops_retrying_after_success(self):
#         with self.generate_directory_mocks() as mocks:
#             mocks['rmtree'].side_effect = [OSError, OSError, None]
#             some_path = self.generate_random_path
#             conda.common.disk.rm_rf(some_path, trash=False)
#         self.assertEqual(3, mocks['rmtree'].call_count)
#
#     @skip_if_no_mock
#     def test_pauses_for_same_number_of_seconds_as_max_retries(self):
#         with self.generate_directory_mocks() as mocks:
#             mocks['rmtree'].side_effect = OSError
#             max_retries = random.randint(1, 10)
#             with self.assertRaises(OSError):
#                 conda.common.disk.rm_rf(self.generate_random_path,
#                                         max_retries=max_retries, trash=False)
#
#         expected = [mock.call(i) for i in range(max_retries)]
#         mocks['sleep'].assert_has_calls(expected)
#
#     @skip_if_no_mock
#     def test_logs_messages_generated_for_each_retry(self):
#         with self.generate_directory_mocks() as mocks:
#             random_path = self.generate_random_path
#             mocks['rmtree'].side_effect = OSError(random_path)
#             max_retries = random.randint(1, 10)
#             with self.assertRaises(OSError):
#                 conda.common.disk.rm_rf(random_path, max_retries=max_retries, trash=False)
#
#         log_template = "\n".join([
#             "Unable to delete %s" % random_path,
#             "%s" % OSError(random_path),
#             "Retrying after %d seconds...",
#         ])
#
#         expected_call_list = [mock.call(log_template % i)
#                               for i in range(max_retries)]
#         mocks['log'].debug.assert_has_calls(expected_call_list)
#
#     @skip_if_no_mock
#     def test_tries_extra_kwarg_on_windows(self):
#         with self.generate_directory_mocks(on_win=True) as mocks:
#             random_path = self.generate_random_path
#             mocks['rmtree'].side_effect = [OSError, None]
#             conda.common.disk.rm_rf(random_path, trash=False)
#
#         expected_call_list = [
#             mock.call(random_path, ignore_errors=False, onerror=warn_failed_remove),
#             mock.call(random_path, onerror=install._remove_readonly)
#         ]
#         mocks['rmtree'].assert_has_calls(expected_call_list)
#         self.assertEqual(2, mocks['rmtree'].call_count)


# def test_dist2():
#     for name in ('python', 'python-hyphen', ''):
#         for version in ('2.7.0', '2.7.0rc1', ''):
#             for build in ('0', 'py27_0', 'py35_0+g34fe21', ''):
#                 for channel in ('defaults', 'test', 'test-hyphen', 'http://bremen',
#                                 'https://anaconda.org/mcg', '<unknown>'):
#                     dist_noprefix = name + '-' + version + '-' + build
#                     quad = (name, version, build, channel)
#                     dist = dist_noprefix if channel == 'defaults' else channel + '::' + dist_noprefix
#                     for suffix in ('', '.tar.bz2', '[debug]', '.tar.bz2[debug]'):
#                         test = dist + suffix
#                         assert dist2quad(test) == quad
#                         assert dist2pair(test) == (channel, dist_noprefix)
#                         assert dist2name(test) == name
#                         assert name_dist(test) == name
#                         assert dist2dirname(test) == dist_noprefix
#                         assert dist2filename(test) == dist_noprefix + '.tar.bz2'
#                         assert dist2filename(test, '') == dist_noprefix


def _make_lines_file(path):
    with open(path, 'w') as fh:
        fh.write("line 1\n")
        fh.write("line 2\n")
        fh.write("# line 3\n")
        fh.write("line 4\n")

def test_yield_lines(tmpdir):
    tempfile = join(text_type(tmpdir), "testfile")
    _make_lines_file(tempfile)
    lines = list(yield_lines(tempfile))
    assert lines == ['line 1', 'line 2', 'line 4']


def test_read_no_link(tmpdir):
    tempdir = text_type(tmpdir)
    no_link = join(tempdir, 'no_link')
    no_softlink = join(tempdir, 'no_softlink')
    _make_lines_file(no_link)
    s1 = read_no_link(tempdir)
    assert s1 == {'line 1', 'line 2', 'line 4'}

    _make_lines_file(no_softlink)
    s2 = read_no_link(tempdir)
    assert s2 == {'line 1', 'line 2', 'line 4'}
