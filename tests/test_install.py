try:
    from unittest import mock
except ImportError:
    import mock
    from mock import patch

from contextlib import contextmanager
import random
import shutil
import tempfile
import unittest
from os.path import join

from conda import install
from conda.install import PaddingError, binary_replace, update_prefix


class TestBinaryReplace(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(
            binary_replace(b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbbb'),
            b'xxxbbbbbxyz\x00zz')

    def test_shorter(self):
        self.assertEqual(
            binary_replace(b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbb'),
            b'xxxbbbbxyz\x00\x00zz')

    def test_too_long(self):
        self.assertRaises(PaddingError, binary_replace,
                          b'xxxaaaaaxyz\x00zz', b'aaaaa', b'bbbbbbbb')

    def test_no_extra(self):
        self.assertEqual(binary_replace(b'aaaaa\x00', b'aaaaa', b'bbbbb'),
                         b'bbbbb\x00')

    def test_two(self):
        self.assertEqual(
            binary_replace(b'aaaaa\x001234aaaaacc\x00\x00', b'aaaaa', b'bbbbb'),
            b'bbbbb\x001234bbbbbcc\x00\x00')

    def test_spaces(self):
        self.assertEqual(
            binary_replace(b' aaaa \x00', b'aaaa', b'bbbb'),
            b' bbbb \x00')

    def test_multiple(self):
        self.assertEqual(
            binary_replace(b'aaaacaaaa\x00', b'aaaa', b'bbbb'),
            b'bbbbcbbbb\x00')
        self.assertEqual(
            binary_replace(b'aaaacaaaa\x00', b'aaaa', b'bbb'),
            b'bbbcbbb\x00\x00\x00')
        self.assertRaises(PaddingError, binary_replace,
                          b'aaaacaaaa\x00', b'aaaa', b'bbbbb')


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

    def test_binary(self):
        with open(self.tmpfname, 'wb') as fo:
            fo.write(b'\x7fELF.../some-placeholder/lib/libfoo.so\0')
        update_prefix(self.tmpfname, '/usr/local',
                      placeholder='/some-placeholder', mode='binary')
        with open(self.tmpfname, 'rb') as fi:
            data = fi.read()
            self.assertEqual(
                data,
                b'\x7fELF.../usr/local/lib/libfoo.so\0\0\0\0\0\0\0\0'
            )


class rm_rf_file_and_link_TestCase(unittest.TestCase):
    @contextmanager
    def generate_mock_islink(self, value):
        with patch.object(install, 'islink', return_value=value) as islink:
            yield islink

    @contextmanager
    def generate_mock_isfile(self, value):
        with patch.object(install, 'isfile', return_value=value) as isfile:
            yield isfile

    @contextmanager
    def generate_mock_unlink(self):
        with patch.object(install.os, 'unlink') as unlink:
            yield unlink

    @contextmanager
    def generate_mocks(self, islink=True, isfile=True):
        with self.generate_mock_islink(islink) as mock_islink:
            with self.generate_mock_isfile(isfile) as mock_isfile:
                with self.generate_mock_unlink() as mock_unlink:
                    yield {
                        'islink': mock_islink,
                        'isfile': mock_isfile,
                        'unlink': mock_unlink,
                    }

    def test_calls_islink(self):
        with self.generate_mocks() as mocks:
            some_path = '/some/path/to/file%s' % random.randint(100, 200)
            install.rm_rf(some_path)
        mocks['islink'].assert_called_with(some_path)

    def test_calls_unlink_on_true_islink(self):
        with self.generate_mocks() as mocks:
            some_path = '/some/path/to/file%s' % random.randint(100, 200)
            install.rm_rf(some_path)
        mocks['unlink'].assert_called_with(some_path)

    def test_does_not_call_isfile_if_islink_is_true(self):
        with self.generate_mocks() as mocks:
            some_path = '/some/path/to/file%s' % random.randint(100, 200)
            install.rm_rf(some_path)
        self.assertFalse(mocks['isfile'].called)

    def test_calls_isfile_with_path(self):
        with self.generate_mocks(islink=False, isfile=True) as mocks:
            some_path = '/some/path/to/file%s' % random.randint(100, 200)
            install.rm_rf(some_path)
        mocks['isfile'].assert_called_with(some_path)

    def test_calls_unlink_on_false_islink_and_true_isfile(self):
        with self.generate_mocks(islink=False, isfile=True) as mocks:
            some_path = '/some/path/to/file%s' % random.randint(100, 200)
            install.rm_rf(some_path)
        mocks['unlink'].assert_called_with(some_path)

    def test_does_not_call_unlink_on_false_values(self):
        with self.generate_mocks(islink=False, isfile=False) as mocks:
            some_path = '/some/path/to/file%s' % random.randint(100, 200)
            install.rm_rf(some_path)
        self.assertFalse(mocks['unlink'].called)


if __name__ == '__main__':
    unittest.main()
