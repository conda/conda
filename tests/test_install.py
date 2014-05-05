import unittest

from conda.install import binary_replace


class TestBinaryReplace(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(binary_replace('xxxaaaaaxyz\x00zz', 'aaaaa', 'bbbbb'),
                                        'xxxbbbbbxyz\x00zz')

    def test_shorter(self):
        self.assertEqual(binary_replace('xxxaaaaaxyz\x00zz', 'aaaaa', 'bbbb'),
                                        'xxxbbbbxyz\x00\x00zz')

    def test_too_long(self):
        self.assertEqual(binary_replace('xxxaaaaaxyz\x00zz', 'aaaaa', 'bbbbbbbb'),
                                        'xxxaaaaaxyz\x00zz')

    def test_no_extra(self):
        self.assertEqual(binary_replace('aaaaa\x00', 'aaaaa', 'bbbbb'),
                                        'bbbbb\x00')

    def test_two(self):
        self.assertEqual(binary_replace('aaaaa\x001234aaaaacc\x00\x00',
                                                                 'aaaaa', 'bbbbb'),
                                        'bbbbb\x001234bbbbbcc\x00\x00')


if __name__ == '__main__':
    unittest.main()
