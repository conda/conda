import unittest

from conda.fetch import cache_fn_url
from conda.verify_sig import ascii2sig, sig2ascii


class TestMisc(unittest.TestCase):

    def test_cache_fn_url(self):
        url = "http://repo.continuum.io/pkgs/pro/osx-64/"
        self.assertEqual(cache_fn_url(url), '7618c8b6.json')

    def test_ascii2sig(self):
        self.assertEqual(sig2ascii(1234), 'BNI=')

    def test_sig2ascii(self):
        self.assertEqual(ascii2sig('BNI='), 1234)

    def test_sig2ascii2sig(self):
        for i in range(10000):
            self.assertEqual(ascii2sig(sig2ascii(i)), i)


if __name__ == '__main__':
    unittest.main()
