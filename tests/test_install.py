import shutil
import tempfile
import unittest
from os.path import join

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
            self.assertEqual(data,
                      b'\x7fELF.../usr/local/lib/libfoo.so\0\0\0\0\0\0\0\0')


if __name__ == '__main__':
    unittest.main()
